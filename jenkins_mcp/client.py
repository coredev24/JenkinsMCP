"""
Jenkins API client with comprehensive error handling and retry logic.

Provides async access to Jenkins REST API with proper authentication,
retry mechanisms, and structured error responses.
"""

import asyncio
import time
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List, Union
from urllib.parse import urljoin, quote

import aiohttp
import structlog

from .config import JenkinsConfig
from .auth import AuthManager, JenkinsConnectionError, JenkinsAuthenticationError

logger = structlog.get_logger()


class JenkinsClientError(Exception):
    """Base exception for Jenkins client errors."""
    pass


class JenkinsConnectionError(JenkinsClientError):
    """Connection-related errors."""
    pass


class JenkinsAuthenticationError(JenkinsClientError):
    """Authentication failures."""
    pass


class JenkinsNotFoundError(JenkinsClientError):
    """Resource not found errors."""
    pass


class JenkinsPermissionError(JenkinsClientError):
    """Permission/authorization errors."""
    pass


class JenkinsTimeoutError(JenkinsClientError):
    """Request timeout errors."""
    pass


class JenkinsServerError(JenkinsClientError):
    """Server-side errors."""
    pass


class JenkinsClient:
    """Async Jenkins API client with comprehensive error handling."""

    def __init__(self, config: JenkinsConfig):
        self.config = config
        self.auth_manager = AuthManager(config)
        self.session: Optional[aiohttp.ClientSession] = None
        self._crumb_cache: Optional[Dict[str, str]] = None
        self._crumb_cache_time: float = 0
        self._crumb_cache_ttl: float = 300  # 5 minutes

    async def __aenter__(self):
        """Async context manager entry."""
        await self.ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def ensure_session(self) -> None:
        """Ensure aiohttp session is created."""
        if self.session is None or self.session.closed:
            connector = aiohttp.TCPConnector(
                limit=self.config.max_concurrent_requests,
                limit_per_host=self.config.max_concurrent_requests,
                ssl=self.config.verify_ssl,
                ttl_dns_cache=300,
                use_dns_cache=True,
            )

            timeout = aiohttp.ClientTimeout(
                total=self.config.request_timeout,
                connect=self.config.timeout,
                sock_read=self.config.timeout
            )

            self.session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
                headers={"User-Agent": "jenkins-mcp-server/1.0.0"}
            )

    async def close(self) -> None:
        """Close the aiohttp session."""
        if self.session and not self.session.closed:
            await self.session.close()
            self.session = None

    async def _get_auth_headers(self) -> Dict[str, str]:
        """Get authentication headers."""
        return await self.auth_manager.get_auth_headers()

    async def _get_crumb_headers(self) -> Dict[str, str]:
        """Get CSRF crumb headers if required."""
        if not self.config.crumb_required:
            return {}

        # Check cache
        current_time = time.time()
        if (
            self._crumb_cache and
            current_time - self._crumb_cache_time < self._crumb_cache_ttl
        ):
            return self._crumb_cache.copy()

        # Fetch new crumb
        crumb = await self.auth_manager.get_crumb()
        if crumb:
            self._crumb_cache = crumb
            self._crumb_cache_time = current_time
            return crumb.copy()

        return {}

    async def _wait_for_retry(self, attempt: int) -> None:
        """Wait before retry with exponential backoff."""
        delay = min(
            self.config.retry_config.base_delay *
            (self.config.retry_config.exponential_base ** attempt),
            self.config.retry_config.max_delay
        )

        # Add jitter if enabled
        if self.config.retry_config.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)

        logger.debug(
            "retrying_request",
            attempt=attempt,
            delay_seconds=delay
        )

        await asyncio.sleep(delay)

    async def _handle_error_response(self, response: aiohttp.ClientResponse) -> None:
        """Handle HTTP error responses and raise appropriate exceptions."""
        status_code = response.status

        # Try to get error details from response
        error_text = ""
        try:
            error_text = await response.text()
        except Exception:
            pass

        if status_code == 400:
            raise JenkinsClientError(f"Bad request: {error_text}")
        elif status_code == 401:
            raise JenkinsAuthenticationError(f"Authentication failed: {error_text}")
        elif status_code == 403:
            raise JenkinsPermissionError(f"Access forbidden: {error_text}")
        elif status_code == 404:
            raise JenkinsNotFoundError(f"Resource not found: {error_text}")
        elif status_code >= 500:
            raise JenkinsServerError(f"Server error ({status_code}): {error_text}")
        else:
            raise JenkinsClientError(f"HTTP error ({status_code}): {error_text}")

    async def make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        headers: Optional[Dict[str, str]] = None,
        allow_redirects: bool = True
    ) -> Dict[str, Any]:
        """Make HTTP request with comprehensive error handling and retry logic."""
        await self.ensure_session()

        url = urljoin(self.config.url + "/", endpoint.lstrip("/"))
        attempt = 0

        while attempt <= self.config.retry_config.max_retries:
            try:
                # Prepare headers
                request_headers = {}
                request_headers.update(await self._get_auth_headers())

                # Add crumb for POST/PUT/DELETE requests
                if method.upper() in ["POST", "PUT", "DELETE"]:
                    crumb_headers = await self._get_crumb_headers()
                    request_headers.update(crumb_headers)

                if headers:
                    request_headers.update(headers)

                # Prepare data
                request_data = None
                if data is not None:
                    if isinstance(data, dict):
                        request_data = json.dumps(data)
                        request_headers["Content-Type"] = "application/json"
                    else:
                        request_data = data

                logger.debug(
                    "jenkins_api_request",
                    method=method,
                    url=url,
                    attempt=attempt + 1,
                    max_retries=self.config.retry_config.max_retries + 1
                )

                # Make request
                async with self.session.request(
                    method,
                    url,
                    params=params,
                    data=request_data,
                    headers=request_headers,
                    allow_redirects=allow_redirects
                ) as response:

                    # Handle successful responses
                    if response.status < 400:
                        content_type = response.headers.get("content-type", "")

                        if "application/json" in content_type:
                            result = await response.json()
                        else:
                            text_result = await response.text()
                            try:
                                result = json.loads(text_result)
                            except json.JSONDecodeError:
                                result = {"content": text_result}

                        logger.debug(
                            "jenkins_api_request_success",
                            method=method,
                            url=url,
                            status=response.status,
                            attempt=attempt + 1
                        )

                        return result

                    # Handle error responses
                    status_code = response.status

                    # Check if we should retry based on status code
                    if status_code in self.config.retry_config.retry_status_codes:
                        if attempt < self.config.retry_config.max_retries:
                            await self._wait_for_retry(attempt)
                            attempt += 1
                            continue

                    # Don't retry on certain status codes
                    if status_code in self.config.retry_config.no_retry_status_codes:
                        await self._handle_error_response(response)

                    # Default error handling
                    await self._handle_error_response(response)

            except asyncio.TimeoutError:
                if attempt < self.config.retry_config.max_retries:
                    await self._wait_for_retry(attempt)
                    attempt += 1
                    continue
                else:
                    raise JenkinsTimeoutError(
                        f"Request to {url} timed out after "
                        f"{self.config.timeout} seconds"
                    )

            except aiohttp.ClientError as e:
                if attempt < self.config.retry_config.max_retries:
                    await self._wait_for_retry(attempt)
                    attempt += 1
                    continue
                else:
                    raise JenkinsConnectionError(
                        f"Connection error to Jenkins: {str(e)}"
                    )

        # Should never reach here
        raise JenkinsClientError("Max retries exceeded")

    # System Information Methods

    async def get_system_info(self, include_stats: bool = True) -> Dict[str, Any]:
        """Get comprehensive Jenkins system information."""
        params = {"depth": 1} if include_stats else {}
        return await self.make_request("GET", "/api/json", params=params)

    async def get_version(self) -> Dict[str, Any]:
        """Get Jenkins version information."""
        return await self.make_request("GET", "/api/json")

    # Job Management Methods

    async def list_jobs(
        self,
        view_name: Optional[str] = None,
        job_filter: Optional[str] = None,
        include_details: bool = False,
        limit: int = 100
    ) -> Dict[str, Any]:
        """List Jenkins jobs with optional filtering."""
        if view_name:
            endpoint = f"/view/{quote(view_name)}/api/json"
        else:
            endpoint = "/api/json"

        params = {
            "depth": 2 if include_details else 1,
            "tree": f"jobs[name,url,color,buildable,inQueue,lastBuild[number,url,result,timestamp],nextBuildNumber,description][{max(0, limit-1)}:]"
        }

        return await self.make_request("GET", endpoint, params=params)

    async def get_job_details(
        self,
        job_name: str,
        include_config: bool = False,
        include_recent_builds: int = 5
    ) -> Dict[str, Any]:
        """Get comprehensive details for a specific job."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/api/json"

        params = {
            "depth": 2,
            "tree": f"name,displayName,url,description,buildable,concurrentBuild,scm,triggers,builders,publishers,properties,lastBuild[number,url,result,timestamp,duration,building],lastCompletedBuild,lastSuccessfulBuild,lastFailedBuild,lastUnsuccessfulBuild,nextBuildNumber,healthReport,actions[causes]"
        }

        result = await self.make_request("GET", endpoint, params=params)

        # Include configuration XML if requested
        if include_config:
            config_endpoint = f"/job/{encoded_job_name}/config.xml"
            config_xml = await self.make_request("GET", config_endpoint)
            result["config_xml"] = config_xml.get("content", "")

        return result

    async def get_job_config(self, job_name: str, format: str = "xml") -> Dict[str, Any]:
        """Retrieve job configuration."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/config.xml"

        if format.lower() == "json":
            params = {"format": "json"}
            return await self.make_request("GET", endpoint, params=params)
        else:
            result = await self.make_request("GET", endpoint)
            return {"config_xml": result.get("content", ""), "format": "xml"}

    async def create_job(
        self,
        job_name: str,
        config_xml: str,
        from_template: Optional[str] = None,
        view_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new Jenkins job."""
        encoded_job_name = quote(job_name)

        if from_template:
            # Copy from template
            template_endpoint = f"/job/{quote(from_template)}/config.xml"
            template_config = await self.make_request("GET", template_endpoint)
            config_xml = template_config.get("content", config_xml)

        # Create job
        create_endpoint = f"/createItem?name={encoded_job_name}"
        headers = {"Content-Type": "application/xml"}

        await self.make_request("POST", create_endpoint, data=config_xml, headers=headers)

        # Add to view if specified
        if view_name:
            await self.add_job_to_view(view_name, job_name)

        return {
            "success": True,
            "job_name": job_name,
            "url": f"{self.config.url}/job/{encoded_job_name}/",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": "Job created successfully"
        }

    async def update_job_config(
        self,
        job_name: str,
        config_xml: str,
        backup_old_config: bool = True
    ) -> Dict[str, Any]:
        """Update existing job configuration."""
        encoded_job_name = quote(job_name)

        # Backup old config if requested
        backup_url = None
        if backup_old_config:
            try:
                old_config = await self.get_job_config(job_name)
                backup_endpoint = f"/job/{encoded_job_name}/config.xml.backup"
                headers = {"Content-Type": "application/xml"}
                await self.make_request("POST", backup_endpoint,
                                       data=old_config["config_xml"], headers=headers)
                backup_url = f"{self.config.url}/job/{encoded_job_name}/config.xml.backup"
            except Exception as e:
                logger.warning(
                    "config_backup_failed",
                    job_name=job_name,
                    error=str(e)
                )

        # Update configuration
        endpoint = f"/job/{encoded_job_name}/config.xml"
        headers = {"Content-Type": "application/xml"}

        await self.make_request("POST", endpoint, data=config_xml, headers=headers)

        return {
            "success": True,
            "job_name": job_name,
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "config_backup_url": backup_url,
            "message": "Job configuration updated successfully"
        }

    async def delete_job(
        self,
        job_name: str,
        confirm: bool = False,
        backup_config: bool = True
    ) -> Dict[str, Any]:
        """Delete a Jenkins job."""
        if not confirm:
            raise JenkinsClientError("Confirmation required for job deletion")

        encoded_job_name = quote(job_name)

        # Backup config if requested
        backup_url = None
        if backup_config:
            try:
                old_config = await self.get_job_config(job_name)
                backup_endpoint = f"/job/{encoded_job_name}/config.xml.backup"
                headers = {"Content-Type": "application/xml"}
                await self.make_request("POST", backup_endpoint,
                                       data=old_config["config_xml"], headers=headers)
                backup_url = f"{self.config.url}/job/{encoded_job_name}/config.xml.backup"
            except Exception as e:
                logger.warning(
                    "config_backup_failed",
                    job_name=job_name,
                    error=str(e)
                )

        # Delete job
        endpoint = f"/job/{encoded_job_name}/doDelete"
        await self.make_request("POST", endpoint)

        return {
            "success": True,
            "job_name": job_name,
            "deleted_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "backup_url": backup_url,
            "message": "Job deleted successfully"
        }

    async def enable_job(self, job_name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Enable a Jenkins job."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/enable"

        await self.make_request("POST", endpoint)

        return {
            "success": True,
            "job_name": job_name,
            "enabled": True,
            "changed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason or "Manual enable via MCP",
            "message": "Job enabled successfully"
        }

    async def disable_job(self, job_name: str, reason: Optional[str] = None) -> Dict[str, Any]:
        """Disable a Jenkins job."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/disable"

        await self.make_request("POST", endpoint)

        return {
            "success": True,
            "job_name": job_name,
            "enabled": False,
            "changed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "reason": reason or "Manual disable via MCP",
            "message": "Job disabled successfully"
        }

    async def copy_job(
        self,
        source_job: str,
        new_job_name: str,
        update_config: Optional[str] = None,
        target_view: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a copy of an existing job."""
        encoded_source = quote(source_job)
        encoded_new = quote(new_job_name)

        # Copy job
        endpoint = f"/job/{encoded_source}/doCopy?name={encoded_new}"
        await self.make_request("POST", endpoint)

        # Update config if provided
        if update_config:
            await self.update_job_config(new_job_name, update_config, backup_old_config=False)

        # Add to view if specified
        if target_view:
            await self.add_job_to_view(target_view, new_job_name)

        return {
            "success": True,
            "source_job": source_job,
            "new_job_name": new_job_name,
            "new_job_url": f"{self.config.url}/job/{encoded_new}/",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "message": "Job copied successfully"
        }

    async def add_job_to_view(self, view_name: str, job_name: str) -> None:
        """Add a job to a specific view."""
        encoded_view = quote(view_name)
        encoded_job = quote(job_name)

        # Get current view configuration
        view_endpoint = f"/view/{encoded_view}/config.xml"
        view_config = await self.make_request("GET", view_endpoint)

        # Parse XML and add job
        root = ET.fromstring(view_config.get("content", ""))

        # Find jobNames section or create it
        job_names = root.find("jobNames")
        if job_names is None:
            job_names = ET.SubElement(root, "jobNames")
            comparator = ET.SubElement(job_names, "comparator")
            comparator.set("class", "hudson.util.ReverseViewComparator")

        # Add job name
        ET.SubElement(job_names, "string").text = job_name

        # Update view configuration
        updated_config = ET.tostring(root, encoding="unicode")
        headers = {"Content-Type": "application/xml"}
        await self.make_request("POST", view_endpoint, data=updated_config, headers=headers)

    # Build Management Methods

    async def trigger_build(
        self,
        job_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        wait_for_start: bool = False,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Trigger a build for a job (simple or parameterized)."""
        encoded_job_name = quote(job_name)

        if parameters:
            # Parameterized build
            endpoint = f"/job/{encoded_job_name}/buildWithParameters"
            params = parameters
        else:
            # Simple build
            endpoint = f"/job/{encoded_job_name}/build"
            params = None

        # Trigger build
        response = await self.make_request("POST", endpoint, params=params)

        # Extract queue ID from Location header if available
        queue_id = None
        build_number = None

        # Get queue information
        queue_info = await self.get_build_queue()
        for item in queue_info.get("queue_items", []):
            if item.get("job_name") == job_name:
                queue_id = item.get("id")
                break

        # Wait for build to start if requested
        if wait_for_start and queue_id:
            build_info = await self.wait_for_build_start(job_name, queue_id, timeout)
            build_number = build_info.get("build_number")

        return {
            "success": True,
            "job_name": job_name,
            "build_number": build_number,
            "queue_id": queue_id,
            "build_url": f"{self.config.url}/job/{encoded_job_name}/{build_number}/" if build_number else None,
            "status": "QUEUED" if not wait_for_start else "RUNNING",
            "timestamp": int(time.time()),
            "parameters": parameters or {}
        }

    async def get_build_details(
        self,
        job_name: str,
        build_number: Union[int, str],
        include_test_results: bool = False,
        include_artifacts: bool = False
    ) -> Dict[str, Any]:
        """Get comprehensive build information."""
        encoded_job_name = quote(job_name)

        if build_number == "last":
            build_number = "lastBuild"

        endpoint = f"/job/{encoded_job_name}/{build_number}/api/json"

        params = {
            "depth": 2,
            "tree": "number,url,jobName,result,timestamp,duration,estimatedDuration,building,displayName,fullDisplayName,description,actions[causes,parameters],changeSet[items[commitId,author,msg,timestamp]]"
        }

        if include_test_results:
            params["tree"] += ",testResults[totalCount,failCount,skipCount,suites[cases[className,name,status,errorDetails,errorStackTrace]]]"

        if include_artifacts:
            params["tree"] += ",artifacts[relativePath,fileName,size,displayPath]"

        result = await self.make_request("GET", endpoint, params=params)

        # Get console output preview
        log_endpoint = f"/job/{encoded_job_name}/{build_number}/logText/progressiveText"
        try:
            log_response = await self.make_request("GET", log_endpoint, params={"start": 0})
            result["console_output"] = log_response.get("content", "")[:1000]  # First 1000 chars
        except Exception:
            result["console_output"] = ""

        result["log_url"] = f"{self.config.url}/job/{encoded_job_name}/{build_number}/console"

        return result

    async def get_build_log(
        self,
        job_name: str,
        build_number: int,
        start_line: int = 0,
        max_lines: int = 1000,
        follow: bool = False
    ) -> Dict[str, Any]:
        """Retrieve build logs with progressive streaming support."""
        encoded_job_name = quote(job_name)

        if follow:
            # Progressive log endpoint
            endpoint = f"/job/{encoded_job_name}/{build_number}/logText/progressiveText"
            params = {"start": start_line}
            result = await self.make_request("GET", endpoint, params=params)

            return {
                "job_name": job_name,
                "build_number": build_number,
                "log_content": result.get("content", ""),
                "start_line": start_line,
                "end_line": start_line + result.get("size", 0),
                "total_lines": start_line + result.get("size", 0),
                "has_more": result.get("hasMore", False),
                "follow_url": f"jenkins://logs/builds/{job_name}/{build_number}?follow=true",
                "timestamp": int(time.time())
            }
        else:
            # Static log endpoint
            endpoint = f"/job/{encoded_job_name}/{build_number}/consoleText"
            result = await self.make_request("GET", endpoint)

            lines = result.get("content", "").split("\n")
            selected_lines = lines[start_line:start_line + max_lines]

            return {
                "job_name": job_name,
                "build_number": build_number,
                "log_content": "\n".join(selected_lines),
                "start_line": start_line,
                "end_line": start_line + len(selected_lines),
                "total_lines": len(lines),
                "has_more": start_line + len(selected_lines) < len(lines),
                "timestamp": int(time.time())
            }

    async def get_build_artifacts(
        self,
        job_name: str,
        build_number: int,
        download_artifact: Optional[str] = None,
        artifact_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """List and optionally download build artifacts."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/{build_number}/api/json"

        params = {"tree": "artifacts[relativePath,fileName,size,displayPath,downloadUrl]"}
        result = await self.make_request("GET", endpoint, params=params)

        artifacts = result.get("artifacts", [])

        # Filter by pattern if specified
        if artifact_pattern:
            import fnmatch
            artifacts = [
                artifact for artifact in artifacts
                if fnmatch.fnmatch(artifact.get("relativePath", ""), artifact_pattern)
            ]

        # Download specific artifact if requested
        downloaded_artifact = None
        if download_artifact:
            for artifact in artifacts:
                if artifact.get("relativePath") == download_artifact or artifact.get("fileName") == download_artifact:
                    download_url = f"{self.config.url}/job/{encoded_job_name}/{build_number}/artifact/{artifact.get('relativePath')}"
                    download_response = await self.make_request("GET", download_url)

                    downloaded_artifact = {
                        "name": artifact.get("fileName"),
                        "content": download_response.get("content", ""),
                        "size": artifact.get("size", 0)
                    }
                    break

        return {
            "job_name": job_name,
            "build_number": build_number,
            "artifacts": artifacts,
            "total_count": len(artifacts),
            "downloaded_artifact": downloaded_artifact
        }

    async def abort_build(
        self,
        job_name: str,
        build_number: int,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Abort or cancel a running build."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/{build_number}/stop"

        await self.make_request("POST", endpoint)

        return {
            "success": True,
            "job_name": job_name,
            "build_number": build_number,
            "aborted_at": str(int(time.time())),
            "reason": reason or "Manual abort via MCP",
            "message": "Build aborted successfully"
        }

    async def get_build_queue(
        self,
        include_details: bool = False,
        job_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get current build queue status."""
        endpoint = "/queue/api/json"

        if include_details:
            params = {"depth": 2}
        else:
            params = {"depth": 1}

        result = await self.make_request("GET", endpoint, params=params)
        queue_items = result.get("items", [])

        # Filter by job name pattern if specified
        if job_filter:
            import fnmatch
            queue_items = [
                item for item in queue_items
                if fnmatch.fnmatch(item.get("job", {}).get("name", ""), job_filter)
            ]

        return {
            "queue_items": queue_items,
            "total_count": len(queue_items)
        }

    async def get_build_history(
        self,
        job_name: str,
        max_builds: int = 50,
        status_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get build history for a job."""
        encoded_job_name = quote(job_name)
        endpoint = f"/job/{encoded_job_name}/api/json"

        params = {
            "tree": f"builds[number,url,result,timestamp,duration,description][{{0,{max_builds-1}}}]"
        }

        result = await self.make_request("GET", endpoint, params=params)
        builds = result.get("builds", [])

        # Filter by status if specified
        if status_filter:
            builds = [
                build for build in builds
                if build.get("result") == status_filter
            ]

        return {
            "job_name": job_name,
            "builds": builds,
            "total_count": len(builds),
            "has_more": len(builds) == max_builds
        }

    async def wait_for_build_start(
        self,
        job_name: str,
        queue_id: int,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """Wait for a queued build to start."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            queue_info = await self.get_build_queue()

            # Check if our queue item is still in queue
            found_in_queue = False
            for item in queue_info.get("queue_items", []):
                if item.get("id") == queue_id:
                    found_in_queue = True
                    # Check if executable (build started)
                    executable = item.get("executable")
                    if executable:
                        return {
                            "queue_id": queue_id,
                            "build_number": executable.get("number"),
                            "build_url": executable.get("url"),
                            "status": "RUNNING"
                        }
                    break

            if not found_in_queue:
                # Build may have started or failed
                # Check recent builds for this job
                builds_info = await self.get_build_history(job_name, max_builds=1)
                if builds_info.get("builds"):
                    latest_build = builds_info["builds"][0]
                    return {
                        "queue_id": queue_id,
                        "build_number": latest_build.get("number"),
                        "build_url": latest_build.get("url"),
                        "status": latest_build.get("result", "UNKNOWN")
                    }

            await asyncio.sleep(1)

        raise JenkinsTimeoutError(f"Build did not start within {timeout} seconds")

    # Node Management Methods

    async def list_nodes(
        self,
        include_offline: bool = True,
        include_details: bool = False
    ) -> Dict[str, Any]:
        """List all Jenkins nodes/agents."""
        endpoint = "/computer/api/json"

        params = {"depth": 2 if include_details else 1}
        result = await self.make_request("GET", endpoint, params=params)

        computers = result.get("computer", [])

        # Filter offline nodes if requested
        if not include_offline:
            computers = [comp for comp in computers if not comp.get("offline", True)]

        return {
            "nodes": computers,
            "total_count": len(computers),
            "online_count": len([c for c in computers if not c.get("offline", True)]),
            "offline_count": len([c for c in computers if c.get("offline", True)])
        }

    async def get_node_details(
        self,
        node_name: str,
        include_monitor_data: bool = True
    ) -> Dict[str, Any]:
        """Get detailed information for a specific node."""
        encoded_node = quote(node_name)
        endpoint = f"/computer/{encoded_node}/api/json"

        params = {"depth": 2} if include_monitor_data else {"depth": 1}
        return await self.make_request("GET", endpoint, params=params)

    # Plugin Management Methods

    async def get_plugin_list(
        self,
        include_updates: bool = False,
        filter_enabled: Optional[bool] = None
    ) -> Dict[str, Any]:
        """List installed Jenkins plugins."""
        endpoint = "/pluginManager/api/json"

        params = {"depth": 2} if include_updates else {"depth": 1}
        result = await self.make_request("GET", endpoint, params=params)

        plugins = result.get("plugins", [])

        # Filter by enabled status if specified
        if filter_enabled is not None:
            plugins = [p for p in plugins if p.get("enabled", False) == filter_enabled]

        # Count statistics
        enabled_count = len([p for p in plugins if p.get("enabled", False)])
        disabled_count = len([p for p in plugins if not p.get("enabled", False)])
        updates_count = len([p for p in plugins if p.get("hasUpdate", False)])

        return {
            "plugins": plugins,
            "total_count": len(plugins),
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
            "updates_available": updates_count if include_updates else None
        }

    # View Management Methods

    async def list_views(
        self,
        include_nested: bool = False,
        view_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """List all Jenkins views with optional filtering."""
        endpoint = "/api/json"

        params = {"depth": 2 if include_nested else 1}
        result = await self.make_request("GET", endpoint, params=params)

        views = result.get("views", [])

        # Filter by view type if specified
        if view_type:
            views = [v for v in views if view_type.lower() in v.get("_class", "").lower()]

        primary_view = result.get("primaryView", {})

        return {
            "views": views,
            "total_count": len(views),
            "primary_view": primary_view.get("name", "All")
        }

    async def get_view_details(
        self,
        view_name: str,
        include_job_details: bool = False
    ) -> Dict[str, Any]:
        """Get detailed information for a specific view."""
        encoded_view = quote(view_name)
        endpoint = f"/view/{encoded_view}/api/json"

        params = {"depth": 2 if include_job_details else 1}
        return await self.make_request("GET", endpoint, params=params)

    # Load Statistics

    async def get_load_statistics(self, time_range: str = "hour") -> Dict[str, Any]:
        """Get Jenkins system load statistics."""
        # Jenkins doesn't have a direct API for historical load statistics
        # We'll return current system information that can be used for monitoring

        system_info = await self.get_system_info(include_stats=True)
        queue_info = await self.get_build_queue()
        nodes_info = await self.list_nodes(include_details=True)

        # Extract relevant statistics
        stats = {
            "overall_load": system_info.get("unlabeledLoad", {}).get("overallLoad", 0),
            "computer_loads": {}
        }

        # Calculate per-node load
        for node in nodes_info.get("nodes", []):
            node_name = node.get("displayName", "unknown")
            if not node.get("offline", True):
                # Simple load calculation based on executors
                num_executors = node.get("numExecutors", 0)
                idle = node.get("idle", True)
                load = 0.0 if idle else 1.0  # Simplified load metric
                stats["computer_loads"][node_name] = load

        return {
            "time_range": time_range,
            "stats": stats,
            "current_load": {
                "overall": stats["overall_load"],
                **stats["computer_loads"]
            },
            "queue_length": len(queue_info.get("queue_items", [])),
            "total_executors": system_info.get("numExecutors", 0)
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test Jenkins connection and authentication."""
        return await self.auth_manager.test_connection()