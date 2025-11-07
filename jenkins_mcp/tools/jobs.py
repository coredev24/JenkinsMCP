"""
Jenkins job management MCP tools.

Provides comprehensive job management functionality including listing,
creating, updating, configuring, and managing Jenkins jobs.
"""

import structlog

logger = structlog.get_logger()


async def list_jobs(
    view_name: str = None,
    job_filter: str = None,
    include_details: bool = False,
    limit: int = 100
) -> dict:
    """List all Jenkins jobs with optional filtering capabilities.

    Args:
        view_name: Filter jobs by specific view
        job_filter: Filter jobs by name pattern (supports wildcards)
        include_details: Include detailed job information
        limit: Maximum number of jobs to return

    Returns:
        Dictionary containing job list and metadata
    """
    from ..server import get_jenkins_client
    import fnmatch

    client = get_jenkins_client()

    result = await client.list_jobs(
        view_name=view_name,
        include_details=include_details,
        limit=limit
    )

    jobs = result.get("jobs", [])

    # Apply job name filter if specified
    if job_filter:
        jobs = [
            job for job in jobs
            if fnmatch.fnmatch(job.get("name", ""), job_filter)
        ]

    return {
        "jobs": jobs,
        "total_count": len(jobs),
        "has_more": len(jobs) == limit,
        "view_name": view_name,
        "job_filter": job_filter,
        "include_details": include_details
    }


async def get_job_details(
    job_name: str,
    include_config: bool = False,
    include_recent_builds: int = 5
) -> dict:
    """Get comprehensive details for a specific job.

    Args:
        job_name: Name of the Jenkins job
        include_config: Include job configuration XML
        include_recent_builds: Number of recent builds to include

    Returns:
        Dictionary containing detailed job information
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    try:
        result = await client.get_job_details(
            job_name=job_name,
            include_config=include_config
        )

        # Add recent builds if requested
        if include_recent_builds > 0:
            build_history = await client.get_build_history(
                job_name=job_name,
                max_builds=include_recent_builds
            )
            result["recent_builds"] = build_history.get("builds", [])

        return result

    except Exception as e:
        logger.error(
            "get_job_details_failed",
            job_name=job_name,
            error=str(e)
        )
        raise


async def create_job(
    job_name: str,
    config_xml: str,
    from_template: str = None,
    view_name: str = None
) -> dict:
    """Create a new Jenkins job from configuration.

    Args:
        job_name: Name for the new job
        config_xml: Complete job configuration XML
        from_template: Create from existing job template
        view_name: Add job to specific view after creation

    Returns:
        Dictionary containing job creation result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    # Validate job name
    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if not config_xml or not config_xml.strip():
        raise ValueError("Configuration XML cannot be empty")

    logger.info(
        "creating_job",
        job_name=job_name,
        from_template=from_template,
        view_name=view_name
    )

    result = await client.create_job(
        job_name=job_name,
        config_xml=config_xml,
        from_template=from_template,
        view_name=view_name
    )

    logger.info(
        "job_created_successfully",
        job_name=job_name,
        url=result.get("url")
    )

    return result


async def update_job_config(
    job_name: str,
    config_xml: str,
    backup_old_config: bool = True
) -> dict:
    """Update existing job configuration.

    Args:
        job_name: Name of the job to update
        config_xml: New job configuration XML
        backup_old_config: Backup current config

    Returns:
        Dictionary containing update result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    # Validate inputs
    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if not config_xml or not config_xml.strip():
        raise ValueError("Configuration XML cannot be empty")

    logger.info(
        "updating_job_config",
        job_name=job_name,
        backup_old_config=backup_old_config
    )

    result = await client.update_job_config(
        job_name=job_name,
        config_xml=config_xml,
        backup_old_config=backup_old_config
    )

    logger.info(
        "job_config_updated_successfully",
        job_name=job_name,
        backup_created=result.get("config_backup_url") is not None
    )

    return result


async def delete_job(
    job_name: str,
    confirm: bool = False,
    backup_config: bool = True
) -> dict:
    """Delete a Jenkins job.

    Args:
        job_name: Name of the job to delete
        confirm: Confirmation to prevent accidental deletion
        backup_config: Backup config before deletion

    Returns:
        Dictionary containing deletion result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not confirm:
        raise ValueError("Confirmation required for job deletion. Set confirm=True to proceed.")

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    logger.warning(
        "deleting_job",
        job_name=job_name,
        backup_config=backup_config
    )

    result = await client.delete_job(
        job_name=job_name,
        confirm=confirm,
        backup_config=backup_config
    )

    logger.warning(
        "job_deleted_successfully",
        job_name=job_name,
        backup_created=result.get("backup_url") is not None
    )

    return result


async def enable_job(job_name: str, reason: str = None) -> dict:
    """Enable a Jenkins job.

    Args:
        job_name: Name of the job
        reason: Reason for enabling (logged)

    Returns:
        Dictionary containing enable result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    logger.info(
        "enabling_job",
        job_name=job_name,
        reason=reason
    )

    result = await client.enable_job(job_name=job_name, reason=reason)

    logger.info(
        "job_enabled_successfully",
        job_name=job_name,
        reason=reason
    )

    return result


async def disable_job(job_name: str, reason: str = None) -> dict:
    """Disable a Jenkins job.

    Args:
        job_name: Name of the job
        reason: Reason for disabling (logged)

    Returns:
        Dictionary containing disable result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    logger.info(
        "disabling_job",
        job_name=job_name,
        reason=reason
    )

    result = await client.disable_job(job_name=job_name, reason=reason)

    logger.info(
        "job_disabled_successfully",
        job_name=job_name,
        reason=reason
    )

    return result


async def copy_job(
    source_job: str,
    new_job_name: str,
    update_config: str = None,
    target_view: str = None
) -> dict:
    """Create a copy of an existing job.

    Args:
        source_job: Name of source job to copy
        new_job_name: Name for the new job copy
        update_config: New config XML to apply after copy
        target_view: Add new job to specific view

    Returns:
        Dictionary containing copy result
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    # Validate inputs
    if not source_job or not source_job.strip():
        raise ValueError("Source job name cannot be empty")

    if not new_job_name or not new_job_name.strip():
        raise ValueError("New job name cannot be empty")

    logger.info(
        "copying_job",
        source_job=source_job,
        new_job_name=new_job_name,
        target_view=target_view
    )

    result = await client.copy_job(
        source_job=source_job,
        new_job_name=new_job_name,
        update_config=update_config,
        target_view=target_view
    )

    logger.info(
        "job_copied_successfully",
        source_job=source_job,
        new_job_name=new_job_name,
        url=result.get("new_job_url")
    )

    return result


async def get_job_config(job_name: str, format: str = "xml") -> dict:
    """Retrieve job configuration.

    Args:
        job_name: Name of the job
        format: Output format ("xml" or "json")

    Returns:
        Dictionary containing job configuration
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not job_name or not job_name.strip():
        raise ValueError("Job name cannot be empty")

    if format not in ["xml", "json"]:
        raise ValueError("Format must be 'xml' or 'json'")

    logger.info(
        "retrieving_job_config",
        job_name=job_name,
        format=format
    )

    result = await client.get_job_config(job_name=job_name, format=format)

    logger.info(
        "job_config_retrieved_successfully",
        job_name=job_name,
        format=format
    )

    return result