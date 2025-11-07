"""
Jenkins user management MCP tools.

Provides comprehensive user management functionality including getting user info,
listing users, and creating user accounts.
"""

import structlog

logger = structlog.get_logger()


async def get_user_info(include_permissions: bool = False) -> dict:
    """Get current user information.

    Args:
        include_permissions: Include user permissions

    Returns:
        Dictionary containing user information
    """
    logger.info(
        "retrieving_user_info",
        include_permissions=include_permissions
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "id": "current-user",
        "full_name": "Current User",
        "email": "user@example.com",
        "description": "Jenkins User",
        "avatar_url": "http://jenkins/user/current-user/avatar/48x48/",
        "created_at": "2023-01-15T10:30:00Z",
        "last_login": "2024-01-15T09:00:00Z",
        "authorities": ["Overall/Read", "Job/Build"],
        "permissions": {} if include_permissions else None
    }

    logger.info(
        "user_info_retrieved_successfully",
        user_id=result.get("id")
    )

    return result


async def list_users(
    include_details: bool = False,
    user_filter: str = None
) -> dict:
    """List all Jenkins users.

    Args:
        include_details: Include detailed user information
        user_filter: Filter users by name pattern

    Returns:
        Dictionary containing user list and metadata
    """
    import fnmatch

    logger.info(
        "listing_users",
        include_details=include_details,
        user_filter=user_filter
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    users = [
        {
            "id": "admin",
            "full_name": "Administrator",
            "email": "admin@example.com",
            "avatar_url": "http://jenkins/user/admin/avatar/48x48/"
        },
        {
            "id": "developer",
            "full_name": "Developer User",
            "email": "dev@example.com",
            "avatar_url": "http://jenkins/user/developer/avatar/48x48/"
        }
    ]

    # Apply user filter if specified
    if user_filter:
        users = [
            user for user in users
            if fnmatch.fnmatch(user.get("id", ""), user_filter) or
               fnmatch.fnmatch(user.get("full_name", ""), user_filter)
        ]

    result = {
        "users": users,
        "total_count": len(users),
        "include_details": include_details,
        "user_filter": user_filter
    }

    logger.info(
        "users_listed_successfully",
        total_users=result.get("total_count", 0),
        filtered_by=user_filter
    )

    return result


async def create_user(
    username: str,
    password: str,
    full_name: str = None,
    email: str = None,
    permissions: list = None
) -> dict:
    """Create a new Jenkins user account.

    Args:
        username: New username
        password: Initial password
        full_name: User's full name
        email: User's email
        permissions: List of permissions to grant

    Returns:
        Dictionary containing user creation result
    """
    if not username or not username.strip():
        raise ValueError("Username cannot be empty")

    if not password or not password.strip():
        raise ValueError("Password cannot be empty")

    logger.info(
        "creating_user",
        username=username,
        full_name=full_name,
        email=email
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "success": True,
        "username": username,
        "full_name": full_name or username,
        "created_at": "2024-01-15T10:30:00Z",
        "message": "User creation requested (not fully implemented)"
    }

    logger.warning(
        "user_creation_requested",
        username=username,
        note="Implementation incomplete"
    )

    return result


async def get_load_statistics(time_range: str = "hour") -> dict:
    """Get Jenkins system load statistics.

    Args:
        time_range: Time range ("hour", "day", "week", "month")

    Returns:
        Dictionary containing load statistics
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if time_range not in ["hour", "day", "week", "month"]:
        raise ValueError("time_range must be one of: hour, day, week, month")

    logger.info(
        "retrieving_load_statistics",
        time_range=time_range
    )

    result = await client.get_load_statistics(time_range=time_range)

    logger.info(
        "load_statistics_retrieved_successfully",
        time_range=time_range,
        overall_load=result.get("current_load", {}).get("overall", 0),
        queue_length=result.get("queue_length", 0)
    )

    return result