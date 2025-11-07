"""
Authentication handlers for Jenkins MCP server.

Supports multiple authentication methods including API tokens, basic auth,
and OAuth. Provides secure credential management and token refresh.
"""

import base64
import time
import json
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, Tuple
import aiohttp
import structlog

from .config import JenkinsConfig, AuthMethod

logger = structlog.get_logger()


class AuthError(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthError):
    """Raised when authentication credentials are invalid."""
    pass


class TokenExpiredError(AuthError):
    """Raised when authentication token has expired."""
    pass


class OAuthError(AuthError):
    """Raised when OAuth authentication fails."""
    pass


class AuthProvider(ABC):
    """Abstract base class for authentication providers."""

    @abstractmethod
    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for HTTP requests."""
        pass

    @abstractmethod
    async def validate_credentials(self) -> bool:
        """Validate that credentials are working."""
        pass

    @abstractmethod
    async def refresh_if_needed(self) -> None:
        """Refresh authentication credentials if needed."""
        pass


class APITokenAuthProvider(AuthProvider):
    """Authentication provider using Jenkins API tokens."""

    def __init__(self, config: JenkinsConfig):
        self.config = config
        self.username = config.username
        self.token = config.token

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for API token authentication."""
        if not self.username or not self.token:
            raise InvalidCredentialsError(
                "Username and token are required for API token authentication"
            )

        credentials = f"{self.username}:{self.token}"
        encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

    async def validate_credentials(self) -> bool:
        """Validate API token credentials."""
        try:
            headers = await self.get_auth_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.url}/api/json",
                    headers=headers,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        logger.info(
                            "api_token_credentials_validated",
                            username=self.username
                        )
                        return True
                    elif response.status == 401:
                        logger.warning(
                            "api_token_credentials_invalid",
                            username=self.username,
                            status=response.status
                        )
                        return False
                    else:
                        logger.error(
                            "credential_validation_error",
                            status=response.status,
                            username=self.username
                        )
                        return False

        except Exception as e:
            logger.error(
                "credential_validation_failed",
                username=self.username,
                error=str(e)
            )
            return False

    async def refresh_if_needed(self) -> None:
        """API tokens don't need refresh, but validate if still valid."""
        # API tokens in Jenkins don't typically expire, but we can validate
        # they're still working by making a test request
        is_valid = await self.validate_credentials()
        if not is_valid:
            raise InvalidCredentialsError(
                "API token credentials are no longer valid"
            )


class BasicAuthProvider(AuthProvider):
    """Authentication provider using username/password (basic auth)."""

    def __init__(self, config: JenkinsConfig):
        self.config = config
        self.username = config.username
        self.password = config.token  # Token field stores password for basic auth

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for basic authentication."""
        if not self.username or not self.password:
            raise InvalidCredentialsError(
                "Username and password are required for basic authentication"
            )

        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(
            credentials.encode("utf-8")
        ).decode("utf-8")

        return {
            "Authorization": f"Basic {encoded_credentials}",
            "Content-Type": "application/json"
        }

    async def validate_credentials(self) -> bool:
        """Validate basic auth credentials."""
        try:
            headers = await self.get_auth_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.url}/api/json",
                    headers=headers,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        logger.info(
                            "basic_auth_credentials_validated",
                            username=self.username
                        )
                        return True
                    elif response.status == 401:
                        logger.warning(
                            "basic_auth_credentials_invalid",
                            username=self.username,
                            status=response.status
                        )
                        return False
                    else:
                        logger.error(
                            "credential_validation_error",
                            status=response.status,
                            username=self.username
                        )
                        return False

        except Exception as e:
            logger.error(
                "credential_validation_failed",
                username=self.username,
                error=str(e)
            )
            return False

    async def refresh_if_needed(self) -> None:
        """Basic auth doesn't support token refresh."""
        # Basic auth doesn't have refresh capability
        # Just validate credentials are still working
        is_valid = await self.validate_credentials()
        if not is_valid:
            raise InvalidCredentialsError(
                "Basic authentication credentials are no longer valid"
            )


class OAuthAuthProvider(AuthProvider):
    """Authentication provider using OAuth 2.0."""

    def __init__(self, config: JenkinsConfig):
        self.config = config
        self.access_token = config.token
        self.refresh_token = None
        self.token_expires_at = 0
        self.client_id = None
        self.client_secret = None

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get headers for OAuth authentication."""
        if not self.access_token:
            raise InvalidCredentialsError(
                "Access token is required for OAuth authentication"
            )

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def validate_credentials(self) -> bool:
        """Validate OAuth access token."""
        try:
            headers = await self.get_auth_headers()
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.url}/api/json",
                    headers=headers,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        logger.info("oauth_token_validated")
                        return True
                    elif response.status == 401:
                        logger.warning(
                            "oauth_token_invalid",
                            status=response.status
                        )
                        return False
                    else:
                        logger.error(
                            "token_validation_error",
                            status=response.status
                        )
                        return False

        except Exception as e:
            logger.error(
                "oauth_validation_failed",
                error=str(e)
            )
            return False

    async def refresh_if_needed(self) -> None:
        """Refresh OAuth access token if needed."""
        if not self.refresh_token or not self.client_id or not self.client_secret:
            # No refresh capability available
            is_valid = await self.validate_credentials()
            if not is_valid:
                raise TokenExpiredError(
                    "OAuth token has expired and no refresh mechanism available"
                )
            return

        # Check if token needs refresh (expires within 5 minutes)
        if self.token_expires_at > time.time() + 300:
            return  # Token is still valid

        try:
            logger.info("refreshing_oauth_token")

            async with aiohttp.ClientSession() as session:
                token_data = {
                    "grant_type": "refresh_token",
                    "refresh_token": self.refresh_token,
                    "client_id": self.client_id,
                    "client_secret": self.client_secret
                }

                async with session.post(
                    f"{self.config.url}/securityRealm/finishLogin",
                    data=token_data,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        token_response = await response.json()
                        self.access_token = token_response["access_token"]
                        self.refresh_token = token_response.get("refresh_token")
                        self.token_expires_at = time.time() + token_response.get(
                            "expires_in", 3600
                        )

                        logger.info("oauth_token_refreshed_successfully")

                    else:
                        raise OAuthError(
                            f"Token refresh failed: {response.status}"
                        )

        except Exception as e:
            logger.error(
                "oauth_token_refresh_failed",
                error=str(e)
            )
            raise OAuthError(f"Failed to refresh OAuth token: {e}")

    def set_oauth_config(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: Optional[str] = None,
        expires_in: int = 3600
    ) -> None:
        """Set OAuth configuration parameters."""
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.token_expires_at = time.time() + expires_in


class AuthManager:
    """Manages authentication for Jenkins connections."""

    def __init__(self, config: JenkinsConfig):
        self.config = config
        self.auth_provider = self._create_auth_provider()

    def _create_auth_provider(self) -> AuthProvider:
        """Create appropriate authentication provider based on config."""
        if self.config.auth_method == AuthMethod.API_TOKEN:
            return APITokenAuthProvider(self.config)
        elif self.config.auth_method == AuthMethod.BASIC:
            return BasicAuthProvider(self.config)
        elif self.config.auth_method == AuthMethod.OAUTH:
            return OAuthAuthProvider(self.config)
        else:
            raise ValueError(f"Unsupported authentication method: {self.config.auth_method}")

    async def get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers for current provider."""
        await self.auth_provider.refresh_if_needed()
        return await self.auth_provider.get_auth_headers()

    async def validate_credentials(self) -> bool:
        """Validate current authentication credentials."""
        return await self.auth_provider.validate_credentials()

    async def test_connection(self) -> Dict[str, Any]:
        """Test Jenkins connection with current authentication."""
        start_time = time.time()

        try:
            headers = await self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.url}/api/json",
                    headers=headers,
                    timeout=self.config.timeout
                ) as response:

                    duration = time.time() - start_time

                    if response.status == 200:
                        system_info = await response.json()

                        logger.info(
                            "jenkins_connection_test_successful",
                            url=self.config.url,
                            auth_method=self.config.auth_method.value,
                            duration_ms=duration * 1000
                        )

                        return {
                            "success": True,
                            "url": self.config.url,
                            "auth_method": self.config.auth_method.value,
                            "duration_ms": duration * 1000,
                            "jenkins_version": system_info.get("description", "Unknown"),
                            "system_message": system_info.get("systemMessage", ""),
                            "mode": system_info.get("mode", "UNKNOWN"),
                            "num_executors": system_info.get("numExecutors", 0)
                        }
                    else:
                        error_text = await response.text()

                        logger.error(
                            "jenkins_connection_test_failed",
                            url=self.config.url,
                            auth_method=self.config.auth_method.value,
                            status=response.status,
                            error_text=error_text[:200]
                        )

                        return {
                            "success": False,
                            "url": self.config.url,
                            "auth_method": self.config.auth_method.value,
                            "status": response.status,
                            "error": error_text,
                            "duration_ms": duration * 1000
                        }

        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "jenkins_connection_test_exception",
                url=self.config.url,
                auth_method=self.config.auth_method.value,
                error=str(e),
                duration_ms=duration * 1000
            )

            return {
                "success": False,
                "url": self.config.url,
                "auth_method": self.config.auth_method.value,
                "error": str(e),
                "duration_ms": duration * 1000
            }

    async def get_crumb(self) -> Optional[Dict[str, str]]:
        """Get CSRF crumb token if required by Jenkins."""
        if not self.config.crumb_required:
            return None

        try:
            headers = await self.get_auth_headers()

            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.config.url}/crumbIssuer/api/json",
                    headers=headers,
                    timeout=self.config.timeout
                ) as response:
                    if response.status == 200:
                        crumb_data = await response.json()
                        crumb_header = crumb_data.get("crumbRequestField", "Jenkins-Crumb")
                        crumb_value = crumb_data.get("crumb")

                        logger.debug("crumb_obtained_successfully")

                        return {crumb_header: crumb_value}
                    else:
                        logger.warning(
                            "crumb_request_failed",
                            status=response.status
                        )
                        return None

        except Exception as e:
            logger.warning(
                "crumb_fetch_failed",
                error=str(e)
            )
            return None