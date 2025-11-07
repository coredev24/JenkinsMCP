"""
Configuration management for Jenkins MCP server.

Handles authentication methods, connection details, and server configuration.
Supports multiple authentication strategies and secure credential storage.
"""

import os
import json
import logging
from enum import Enum
from pathlib import Path
from typing import Optional, Dict, Any, Union
from dataclasses import dataclass, field
from dotenv import load_dotenv
import structlog

logger = structlog.get_logger()


class AuthMethod(Enum):
    """Supported authentication methods for Jenkins."""
    API_TOKEN = "api_token"
    BASIC = "basic"
    OAUTH = "oauth"


@dataclass
class RetryConfig:
    """Configuration for retry logic on Jenkins API requests."""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True

    # Retry on these HTTP status codes
    retry_status_codes = {429, 500, 502, 503, 504}

    # Don't retry on these status codes
    no_retry_status_codes = {400, 401, 403, 404, 422}


@dataclass
class JenkinsConfig:
    """Jenkins server configuration and connection settings."""

    # Connection settings
    url: str
    username: Optional[str] = None
    token: Optional[str] = None
    auth_method: AuthMethod = AuthMethod.API_TOKEN

    # Connection behavior
    timeout: int = 30
    retry_config: RetryConfig = field(default_factory=RetryConfig)
    verify_ssl: bool = True
    crumb_required: bool = True

    # Server settings
    log_level: str = "INFO"
    json_logs: bool = False
    log_file: Optional[str] = None

    # Performance settings
    max_concurrent_requests: int = 10
    request_timeout: int = 60

    # Development settings
    debug: bool = False
    mock_jenkins: bool = False

    @classmethod
    def from_env(cls) -> "JenkinsConfig":
        """Load configuration from environment variables."""
        # Load .env file if it exists
        load_dotenv()

        # Required environment variables
        url = os.getenv("JENKINS_URL")
        if not url:
            raise ValueError("JENKINS_URL environment variable is required")

        # Authentication settings
        username = os.getenv("JENKINS_USER")
        token = os.getenv("JENKINS_TOKEN")
        auth_method_str = os.getenv("JENKINS_AUTH_METHOD", "API_TOKEN").upper()

        try:
            auth_method = AuthMethod(auth_method_str.lower())
        except ValueError:
            logger.warning(
                "invalid_auth_method",
                method=auth_method_str,
                default="API_TOKEN"
            )
            auth_method = AuthMethod.API_TOKEN

        # Connection settings
        timeout = int(os.getenv("JENKINS_TIMEOUT", "30"))
        retry_count = int(os.getenv("JENKINS_RETRY_COUNT", "3"))
        retry_delay = float(os.getenv("JENKINS_RETRY_DELAY", "1.0"))
        verify_ssl = os.getenv("JENKINS_VERIFY_SSL", "true").lower() == "true"
        crumb_required = os.getenv("JENKINS_CRUMB_REQUIRED", "true").lower() == "true"

        # Server settings
        log_level = os.getenv("MCP_SERVER_LOG_LEVEL", "INFO")
        json_logs = os.getenv("MCP_SERVER_JSON_LOGS", "false").lower() == "true"
        log_file = os.getenv("MCP_SERVER_LOG_FILE")

        # Performance settings
        max_concurrent_requests = int(os.getenv("JENKINS_MAX_CONCURRENT_REQUESTS", "10"))
        request_timeout = int(os.getenv("JENKINS_REQUEST_TIMEOUT", "60"))

        # Development settings
        debug = os.getenv("JENKINS_MCP_DEBUG", "false").lower() == "true"
        mock_jenkins = os.getenv("JENKINS_MCP_MOCK_JENKINS", "false").lower() == "true"

        # Configure retry settings
        retry_config = RetryConfig(
            max_retries=retry_count,
            base_delay=retry_delay
        )

        config = cls(
            url=url.rstrip("/"),  # Remove trailing slash
            username=username,
            token=token,
            auth_method=auth_method,
            timeout=timeout,
            retry_config=retry_config,
            verify_ssl=verify_ssl,
            crumb_required=crumb_required,
            log_level=log_level,
            json_logs=json_logs,
            log_file=log_file,
            max_concurrent_requests=max_concurrent_requests,
            request_timeout=request_timeout,
            debug=debug,
            mock_jenkins=mock_jenkins
        )

        # Validate configuration
        config.validate()

        logger.info(
            "configuration_loaded",
            url=url,
            auth_method=auth_method.value,
            timeout=timeout,
            debug=debug
        )

        return config

    @classmethod
    def from_file(cls, config_path: Union[str, Path]) -> "JenkinsConfig":
        """Load configuration from JSON file."""
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            # Convert auth_method string to enum
            if "auth_method" in config_data:
                config_data["auth_method"] = AuthMethod(
                    config_data["auth_method"].lower()
                )

            # Handle retry config
            if "retry_config" in config_data:
                retry_data = config_data.pop("retry_config")
                config_data["retry_config"] = RetryConfig(**retry_data)

            config = cls(**config_data)
            config.validate()

            logger.info(
                "configuration_loaded_from_file",
                config_path=str(config_path),
                url=config.url
            )

            return config

        except Exception as e:
            logger.error(
                "configuration_load_failed",
                config_path=str(config_path),
                error=str(e)
            )
            raise ValueError(f"Failed to load configuration from {config_path}: {e}")

    def validate(self) -> None:
        """Validate configuration values."""
        if not self.url:
            raise ValueError("Jenkins URL is required")

        if not self.url.startswith(("http://", "https://")):
            raise ValueError("Jenkins URL must start with http:// or https://")

        # Validate authentication settings
        if self.auth_method == AuthMethod.API_TOKEN:
            if not self.username or not self.token:
                raise ValueError(
                    "API token authentication requires both username and token"
                )
        elif self.auth_method == AuthMethod.BASIC:
            if not self.username or not self.token:
                raise ValueError(
                    "Basic authentication requires both username and password"
                )
        elif self.auth_method == AuthMethod.OAUTH:
            if not self.token:
                raise ValueError("OAuth authentication requires access token")

        # Validate timeout values
        if self.timeout <= 0:
            raise ValueError("Timeout must be positive")

        if self.request_timeout <= 0:
            raise ValueError("Request timeout must be positive")

        # Validate retry configuration
        if self.retry_config.max_retries < 0:
            raise ValueError("Max retries must be non-negative")

        if self.retry_config.base_delay <= 0:
            raise ValueError("Retry delay must be positive")

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary for serialization."""
        return {
            "url": self.url,
            "username": self.username,
            "token": "***REDACTED***" if self.token else None,
            "auth_method": self.auth_method.value,
            "timeout": self.timeout,
            "retry_config": {
                "max_retries": self.retry_config.max_retries,
                "base_delay": self.retry_config.base_delay,
                "max_delay": self.retry_config.max_delay,
                "exponential_base": self.retry_config.exponential_base,
                "jitter": self.retry_config.jitter
            },
            "verify_ssl": self.verify_ssl,
            "crumb_required": self.crumb_required,
            "log_level": self.log_level,
            "json_logs": self.json_logs,
            "log_file": self.log_file,
            "max_concurrent_requests": self.max_concurrent_requests,
            "request_timeout": self.request_timeout,
            "debug": self.debug,
            "mock_jenkins": self.mock_jenkins
        }

    def save_to_file(self, config_path: Union[str, Path]) -> None:
        """Save configuration to JSON file."""
        config_path = Path(config_path)

        try:
            # Create directory if it doesn't exist
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

            logger.info(
                "configuration_saved",
                config_path=str(config_path)
            )

        except Exception as e:
            logger.error(
                "configuration_save_failed",
                config_path=str(config_path),
                error=str(e)
            )
            raise

    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get default configuration file path."""
        home = Path.home()
        return home / ".jenkins-mcp.json"

    @classmethod
    def load_default(cls) -> Optional["JenkinsConfig"]:
        """Load configuration from default locations."""
        # Try environment variables first
        try:
            return cls.from_env()
        except ValueError:
            pass

        # Try default config file
        default_path = cls.get_default_config_path()
        if default_path.exists():
            try:
                return cls.from_file(default_path)
            except Exception:
                logger.warning(
                    "default_config_load_failed",
                    config_path=str(default_path)
                )

        return None


def configure_logging(config: JenkinsConfig) -> None:
    """Configure structured logging based on configuration."""
    import structlog

    # Configure structlog processors
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if config.json_logs:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=config.log_file
    )

    logger.info(
        "logging_configured",
        level=config.log_level,
        json_logs=config.json_logs,
        log_file=config.log_file
    )