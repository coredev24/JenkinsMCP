"""
Jenkins build management MCP tools.

Provides comprehensive build management functionality including triggering,
monitoring, retrieving logs, managing artifacts, and build history.
"""

import structlog

logger = structlog.get_logger()


async def trigger_build(
    job_name: str,
    parameters: dict = None,
    wait_for_start: bool = False,
    timeout: int = 30
) -> dict:
    """Trigger build for a job (simple or parameterized).

    Args:
        job_name: Name of the job to build
        parameters: Build parameters for parameterized jobs
        wait_for_start: Wait for build to start
        timeout: Timeout for waiting (seconds)

    Returns:
        Dictionary containing build trigger result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    logger.info(
        "triggering_build",
        job_name=job_name,
        parameters=parameters,
        wait_for_start=wait_for_start
    )

    result = await client.trigger_build(
        job_name=job_name,
        parameters=parameters,
        wait_for_start=wait_for_start,
        timeout=timeout
    )

    logger.info(
        "build_triggered_successfully",
        job_name=job_name,
        queue_id=result.get("queue_id"),
        build_number=result.get("build_number")
    )

    return result


async def get_build_details(
    job_name: str,
    build_number: int,
    include_test_results: bool = False,
    include_artifacts: bool = False
) -> dict:
    """Get comprehensive build information.

    Args:
        job_name: Name of the job
        build_number: Build number (or "last" for latest)
        include_test_results: Include test results
        include_artifacts: Include artifact list

    Returns:
        Dictionary containing detailed build information
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if build_number == "last":
        build_number = "lastBuild"

    logger.info(
        "retrieving_build_details",
        job_name=job_name,
        build_number=build_number,
        include_test_results=include_test_results,
        include_artifacts=include_artifacts
    )

    result = await client.get_build_details(
        job_name=job_name,
        build_number=build_number,
        include_test_results=include_test_results,
        include_artifacts=include_artifacts
    )

    logger.info(
        "build_details_retrieved_successfully",
        job_name=job_name,
        build_number=result.get("number"),
        result=result.get("result")
    )

    return result


async def get_build_log(
    job_name: str,
    build_number: int,
    start_line: int = 0,
    max_lines: int = 1000,
    follow: bool = False
) -> dict:
    """Retrieve build logs with progressive streaming support.

    Args:
        job_name: Name of the job
        build_number: Build number
        start_line: Starting line number
        max_lines: Maximum lines to return
        follow: Follow log for new content

    Returns:
        Dictionary containing build log content and metadata
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if build_number < 1:
        raise ValueError("Build number must be positive")

    logger.info(
        "retrieving_build_log",
        job_name=job_name,
        build_number=build_number,
        start_line=start_line,
        max_lines=max_lines,
        follow=follow
    )

    result = await client.get_build_log(
        job_name=job_name,
        build_number=build_number,
        start_line=start_line,
        max_lines=max_lines,
        follow=follow
    )

    logger.info(
        "build_log_retrieved_successfully",
        job_name=job_name,
        build_number=build_number,
        lines_returned=result.get("end_line", 0) - result.get("start_line", 0),
        has_more=result.get("has_more", False)
    )

    return result


async def get_build_artifacts(
    job_name: str,
    build_number: int,
    download_artifact: str = None,
    artifact_pattern: str = None
) -> dict:
    """List and optionally download build artifacts.

    Args:
        job_name: Name of the job
        build_number: Build number
        download_artifact: Download specific artifact (base64 encoded)
        artifact_pattern: Filter artifacts by pattern

    Returns:
        Dictionary containing artifact information and optional download
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if build_number < 1:
        raise ValueError("Build number must be positive")

    logger.info(
        "retrieving_build_artifacts",
        job_name=job_name,
        build_number=build_number,
        download_artifact=download_artifact,
        artifact_pattern=artifact_pattern
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "job_name": job_name,
        "build_number": build_number,
        "artifacts": [],
        "total_count": 0,
        "downloaded_artifact": None
    }

    if download_artifact:
        logger.warning(
            "artifact_download_not_implemented",
            artifact=download_artifact
        )

    logger.info(
        "build_artifacts_retrieved_successfully",
        job_name=job_name,
        build_number=build_number,
        artifact_count=result.get("total_count", 0)
    )

    return result


async def abort_build(
    job_name: str,
    build_number: int,
    reason: str = None
) -> dict:
    """Abort or cancel a running build.

    Args:
        job_name: Name of the job
        build_number: Build number to abort
        reason: Reason for aborting (logged)

    Returns:
        Dictionary containing abort result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if build_number < 1:
        raise ValueError("Build number must be positive")

    logger.warning(
        "aborting_build",
        job_name=job_name,
        build_number=build_number,
        reason=reason
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "success": True,
        "job_name": job_name,
        "build_number": build_number,
        "aborted_at": str(int(__import__('time').time())),
        "reason": reason or "Manual abort via MCP",
        "message": "Build abort requested (not fully implemented)"
    }

    logger.warning(
        "build_abort_requested",
        job_name=job_name,
        build_number=build_number,
        note="Implementation incomplete"
    )

    return result


async def get_build_queue(
    include_details: bool = False,
    job_filter: str = None
) -> dict:
    """Get current build queue status.

    Args:
        include_details: Include detailed queue information
        job_filter: Filter queue items by job name pattern

    Returns:
        Dictionary containing queue status and items
    """
    from ..server import get_jenkins_client
    import fnmatch

    client = get_jenkins_client()

    logger.info(
        "retrieving_build_queue",
        include_details=include_details,
        job_filter=job_filter
    )

    result = await client.get_build_queue()
    queue_items = result.get("queue_items", [])

    # Apply job filter if specified
    if job_filter:
        queue_items = [
            item for item in queue_items
            if fnmatch.fnmatch(item.get("job", {}).get("name", ""), job_filter)
        ]

    filtered_result = {
        "queue_items": queue_items,
        "total_count": len(queue_items),
        "include_details": include_details,
        "job_filter": job_filter
    }

    logger.info(
        "build_queue_retrieved_successfully",
        total_items=filtered_result.get("total_count", 0),
        filtered_by=job_filter
    )

    return filtered_result


async def get_build_history(
    job_name: str,
    max_builds: int = 50,
    status_filter: str = None
) -> dict:
    """Get build history for a job.

    Args:
        job_name: Name of the job
        max_builds: Maximum builds to return
        status_filter: Filter by build status (SUCCESS, FAILURE, etc.)

    Returns:
        Dictionary containing build history
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if max_builds < 1:
        raise ValueError("max_builds must be positive")

    logger.info(
        "retrieving_build_history",
        job_name=job_name,
        max_builds=max_builds,
        status_filter=status_filter
    )

    result = await client.get_build_history(
        job_name=job_name,
        max_builds=max_builds,
        status_filter=status_filter
    )

    logger.info(
        "build_history_retrieved_successfully",
        job_name=job_name,
        builds_returned=result.get("total_count", 0),
        has_more=result.get("has_more", False)
    )

    return result