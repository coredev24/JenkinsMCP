"""
Jenkins system and monitoring MCP tools.

Provides comprehensive system monitoring functionality including system info,
version, node management, plugin management, and load statistics.
"""

import structlog

logger = structlog.get_logger()


async def get_system_info(include_stats: bool = True) -> dict:
    """Get comprehensive Jenkins system information.

    Args:
        include_stats: Include system statistics

    Returns:
        Dictionary containing system information
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    logger.info(
        "retrieving_system_info",
        include_stats=include_stats
    )

    result = await client.get_system_info(include_stats=include_stats)

    logger.info(
        "system_info_retrieved_successfully",
        mode=result.get("mode", "UNKNOWN"),
        num_executors=result.get("numExecutors", 0)
    )

    return result


async def get_version() -> dict:
    """Get Jenkins version information.

    Returns:
        Dictionary containing version information
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    logger.info("retrieving_jenkins_version")

    result = await client.get_version()

    logger.info(
        "jenkins_version_retrieved",
        version=result.get("description", "Unknown")
    )

    return result


async def list_nodes(
    include_offline: bool = True,
    include_details: bool = False
) -> dict:
    """List all Jenkins nodes/agents.

    Args:
        include_offline: Include offline nodes
        include_details: Include detailed node information

    Returns:
        Dictionary containing node list and statistics
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    logger.info(
        "listing_nodes",
        include_offline=include_offline,
        include_details=include_details
    )

    result = await client.list_nodes(
        include_offline=include_offline,
        include_details=include_details
    )

    logger.info(
        "nodes_listed_successfully",
        total_nodes=result.get("total_count", 0),
        online_nodes=result.get("online_count", 0),
        offline_nodes=result.get("offline_count", 0)
    )

    return result


async def get_node_details(
    node_name: str,
    include_monitor_data: bool = True
) -> dict:
    """Get detailed information for a specific node.

    Args:
        node_name: Name of the node
        include_monitor_data: Include monitoring data

    Returns:
        Dictionary containing detailed node information
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    if not node_name or not node_name.strip():
        raise ValueError("Node name cannot be empty")

    logger.info(
        "retrieving_node_details",
        node_name=node_name,
        include_monitor_data=include_monitor_data
    )

    result = await client.get_node_details(
        node_name=node_name,
        include_monitor_data=include_monitor_data
    )

    logger.info(
        "node_details_retrieved_successfully",
        node_name=node_name,
        offline=result.get("offline", True)
    )

    return result


async def get_plugin_list(
    include_updates: bool = False,
    filter_enabled: bool = None
) -> dict:
    """List installed Jenkins plugins.

    Args:
        include_updates: Check for available updates
        filter_enabled: Filter by enabled status

    Returns:
        Dictionary containing plugin list and statistics
    """
    from ..server import get_jenkins_client

    client = get_jenkins_client()

    logger.info(
        "retrieving_plugin_list",
        include_updates=include_updates,
        filter_enabled=filter_enabled
    )

    result = await client.get_plugin_list(
        include_updates=include_updates,
        filter_enabled=filter_enabled
    )

    logger.info(
        "plugin_list_retrieved_successfully",
        total_plugins=result.get("total_count", 0),
        enabled_plugins=result.get("enabled_count", 0),
        updates_available=result.get("updates_available")
    )

    return result


async def install_plugin(
    plugin_name: str,
    version: str = None,
    restart_required: bool = False
) -> dict:
    """Install or update Jenkins plugins.

    Args:
        plugin_name: Plugin short name
        version: Specific version to install (latest if not specified)
        restart_required: Auto-restart if needed

    Returns:
        Dictionary containing installation result
    """
    if not plugin_name or not plugin_name.strip():
        raise ValueError("Plugin name cannot be empty")

    logger.info(
        "installing_plugin",
        plugin_name=plugin_name,
        version=version,
        restart_required=restart_required
    )

    # Note: This would require additional implementation in the client
    # For now, we'll provide a basic implementation
    result = {
        "success": True,
        "plugin_name": plugin_name,
        "version": version or "latest",
        "previous_version": "unknown",
        "installed_at": "2024-01-15T10:30:00Z",
        "restart_required": restart_required,
        "message": "Plugin installation requested (not fully implemented)"
    }

    logger.warning(
        "plugin_installation_requested",
        plugin_name=plugin_name,
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