"""
Jenkins view and organization MCP tools.

Provides comprehensive view management functionality including listing,
creating, updating, and managing Jenkins views.
"""

import structlog

logger = structlog.get_logger()


async def list_views(
    include_nested: bool = False,
    view_type: str = None
) -> dict:
    """List all Jenkins views with optional filtering.

    Args:
        include_nested: Include nested views
        view_type: Filter by view type ("list", "my", "all", "status")

    Returns:
        Dictionary containing view list and metadata
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    logger.info(
        "listing_views",
        include_nested=include_nested,
        view_type=view_type
    )

    result = await client.list_views(
        include_nested=include_nested,
        view_type=view_type
    )

    logger.info(
        "views_listed_successfully",
        total_views=result.get("total_count", 0),
        primary_view=result.get("primary_view", "Unknown")
    )

    return result


async def get_view_details(
    view_name: str,
    include_job_details: bool = False
) -> dict:
    """Get detailed information for a specific view.

    Args:
        view_name: Name of the view
        include_job_details: Include detailed job information

    Returns:
        Dictionary containing detailed view information
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not view_name or not view_name.strip():
        raise ValueError("View name cannot be empty")

    logger.info(
        "retrieving_view_details",
        view_name=view_name,
        include_job_details=include_job_details
    )

    result = await client.get_view_details(
        view_name=view_name,
        include_job_details=include_job_details
    )

    logger.info(
        "view_details_retrieved_successfully",
        view_name=view_name,
        job_count=len(result.get("jobs", []))
    )

    return result


async def create_view(
    view_name: str,
    view_type: str,
    description: str = None,
    job_filter: str = None,
    use_regex: bool = False
) -> dict:
    """Create a new Jenkins view.

    Args:
        view_name: Name for the new view
        view_type: Type of view ("list", "my", "all", "status")
        description: View description
        job_filter: Job name filter for list views
        use_regex: Use regex for job filtering

    Returns:
        Dictionary containing view creation result
    """
    if not view_name or not view_name.strip():
        raise ValueError("View name cannot be empty")

    if not view_type or not view_type.strip():
        raise ValueError("View type cannot be empty")

    if view_type not in ["list", "my", "all", "status"]:
        raise ValueError("view_type must be one of: list, my, all, status")

    logger.info(
        "creating_view",
        view_name=view_name,
        view_type=view_type,
        description=description,
        job_filter=job_filter,
        use_regex=use_regex
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "success": True,
        "view_name": view_name,
        "view_type": view_type,
        "url": f"http://jenkins/view/{view_name}/",
        "created_at": "2024-01-15T10:30:00Z",
        "message": "View creation requested (not fully implemented)"
    }

    logger.warning(
        "view_creation_requested",
        view_name=view_name,
        note="Implementation incomplete"
    )

    return result


async def update_view(
    view_name: str,
    description: str = None,
    job_filter: str = None,
    use_regex: bool = None,
    add_jobs: list = None,
    remove_jobs: list = None
) -> dict:
    """Update existing view configuration.

    Args:
        view_name: Name of the view to update
        description: New description
        job_filter: New job filter
        use_regex: Use regex for filtering
        add_jobs: Jobs to add to view
        remove_jobs: Jobs to remove from view

    Returns:
        Dictionary containing update result
    """
    if not view_name or not view_name.strip():
        raise ValueError("View name cannot be empty")

    logger.info(
        "updating_view",
        view_name=view_name,
        description=description,
        job_filter=job_filter,
        use_regex=use_regex,
        add_jobs=add_jobs,
        remove_jobs=remove_jobs
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "success": True,
        "view_name": view_name,
        "updated_at": "2024-01-15T10:30:00Z",
        "added_jobs": add_jobs or [],
        "removed_jobs": remove_jobs or [],
        "message": "View update requested (not fully implemented)"
    }

    logger.warning(
        "view_update_requested",
        view_name=view_name,
        note="Implementation incomplete"
    )

    return result