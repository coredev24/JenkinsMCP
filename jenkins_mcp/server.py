"""
Main FastMCP server for Jenkins automation.

This is the entry point for the Jenkins MCP server that provides
comprehensive access to Jenkins functionality through MCP tools,
resources, and prompts.
"""

import asyncio
import sys
import signal
from typing import Optional
from contextlib import asynccontextmanager

import fastmcp
import structlog

from .config import JenkinsConfig, configure_logging
from .client import JenkinsClient

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan_manager(app: fastmcp.FastMCP):
    """Manage the lifecycle of the Jenkins MCP server."""
    # Load configuration
    try:
        config = JenkinsConfig.from_env()
        configure_logging(config)

        logger.info(
            "jenkins_mcp_server_starting",
            version="1.0.0",
            jenkins_url=config.url,
            auth_method=config.auth_method.value
        )

        # Create Jenkins client
        client = JenkinsClient(config)

        # Test connection
        connection_test = await client.test_connection()
        if not connection_test.get("success"):
            logger.error(
                "jenkins_connection_failed",
                error=connection_test.get("error", "Unknown error")
            )
            raise RuntimeError(f"Failed to connect to Jenkins: {connection_test.get('error')}")

        logger.info(
            "jenkins_connection_successful",
            jenkins_version=connection_test.get("jenkins_version", "Unknown")
        )

        # Store client in app state
        app.state.jenkins_client = client
        app.state.jenkins_config = config

        yield

    except Exception as e:
        logger.error(
            "server_startup_failed",
            error=str(e),
            error_type=type(e).__name__
        )
        raise
    finally:
        # Cleanup
        if hasattr(app.state, 'jenkins_client'):
            await app.state.jenkins_client.close()

        logger.info("jenkins_mcp_server_stopped")


# Create FastMCP server
mcp = fastmcp.FastMCP(
    "jenkins-mcp-server",
    lifespan=lifespan_manager
)


def get_jenkins_client() -> JenkinsClient:
    """Get the Jenkins client from app state."""
    client = getattr(mcp.state, 'jenkins_client', None)
    if client is None:
        raise RuntimeError("Jenkins client not initialized")
    return client


def get_jenkins_config() -> JenkinsConfig:
    """Get the Jenkins config from app state."""
    config = getattr(mcp.state, 'jenkins_config', None)
    if config is None:
        raise RuntimeError("Jenkins config not initialized")
    return config


def format_error_response(tool_name: str, error: Exception) -> dict:
    """Format standardized error responses for MCP tools."""
    error_types = {
        "JenkinsConnectionError": "connection_error",
        "JenkinsAuthenticationError": "authentication_error",
        "JenkinsNotFoundError": "not_found",
        "JenkinsPermissionError": "permission_error",
        "JenkinsTimeoutError": "timeout_error",
        "JenkinsServerError": "server_error"
    }

    error_type = error_types.get(type(error).__name__, "unknown_error")

    response = {
        "success": False,
        "error": {
            "type": error_type,
            "message": str(error),
            "tool": tool_name
        }
    }

    # Add context for specific error types
    if "Authentication" in type(error).__name__:
        response["error"]["suggestion"] = "Check Jenkins credentials and permissions"
    elif "NotFound" in type(error).__name__:
        response["error"]["suggestion"] = "Verify the resource exists and is accessible"
    elif "Timeout" in type(error).__name__:
        response["error"]["suggestion"] = "Try again or increase timeout settings"

    return response


def mcp_tool_handler(tool_name: str):
    """Decorator for MCP tool handlers with error handling."""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = asyncio.get_event_loop().time()

            try:
                logger.info(
                    "tool_execution_started",
                    tool_name=tool_name,
                    args=list(args),
                    kwargs=kwargs
                )

                # Execute the tool
                result = await func(*args, **kwargs)

                # Log successful completion
                duration = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.info(
                    "tool_execution_completed",
                    tool_name=tool_name,
                    duration_ms=duration
                )

                return result

            except Exception as e:
                # Log error
                duration = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.error(
                    "tool_execution_failed",
                    tool_name=tool_name,
                    duration_ms=duration,
                    error_type=type(e).__name__,
                    error_message=str(e)
                )

                # Return formatted error response
                return format_error_response(tool_name, e)

        return wrapper
    return decorator


# Import and register all tools
async def register_all_tools():
    """Register all MCP tools."""
    from .tools import jobs, builds, system, views, credentials, users

    # Register job management tools
    mcp.tool()(mcp_tool_handler("list_jobs")(jobs.list_jobs))
    mcp.tool()(mcp_tool_handler("get_job_details")(jobs.get_job_details))
    mcp.tool()(mcp_tool_handler("create_job")(jobs.create_job))
    mcp.tool()(mcp_tool_handler("update_job_config")(jobs.update_job_config))
    mcp.tool()(mcp_tool_handler("delete_job")(jobs.delete_job))
    mcp.tool()(mcp_tool_handler("enable_job")(jobs.enable_job))
    mcp.tool()(mcp_tool_handler("disable_job")(jobs.disable_job))
    mcp.tool()(mcp_tool_handler("copy_job")(jobs.copy_job))
    mcp.tool()(mcp_tool_handler("get_job_config")(jobs.get_job_config))

    # Register build management tools
    mcp.tool()(mcp_tool_handler("trigger_build")(builds.trigger_build))
    mcp.tool()(mcp_tool_handler("get_build_details")(builds.get_build_details))
    mcp.tool()(mcp_tool_handler("get_build_log")(builds.get_build_log))
    mcp.tool()(mcp_tool_handler("get_build_artifacts")(builds.get_build_artifacts))
    mcp.tool()(mcp_tool_handler("abort_build")(builds.abort_build))
    mcp.tool()(mcp_tool_handler("get_build_queue")(builds.get_build_queue))
    mcp.tool()(mcp_tool_handler("get_build_history")(builds.get_build_history))

    # Register system monitoring tools
    mcp.tool()(mcp_tool_handler("get_system_info")(system.get_system_info))
    mcp.tool()(mcp_tool_handler("get_version")(system.get_version))
    mcp.tool()(mcp_tool_handler("list_nodes")(system.list_nodes))
    mcp.tool()(mcp_tool_handler("get_node_details")(system.get_node_details))
    mcp.tool()(mcp_tool_handler("get_plugin_list")(system.get_plugin_list))
    mcp.tool()(mcp_tool_handler("install_plugin")(system.install_plugin))
    mcp.tool()(mcp_tool_handler("get_load_statistics")(system.get_load_statistics))

    # Register view management tools
    mcp.tool()(mcp_tool_handler("list_views")(views.list_views))
    mcp.tool()(mcp_tool_handler("get_view_details")(views.get_view_details))
    mcp.tool()(mcp_tool_handler("create_view")(views.create_view))
    mcp.tool()(mcp_tool_handler("update_view")(views.update_view))

    # Register credential management tools
    mcp.tool()(mcp_tool_handler("list_credentials")(credentials.list_credentials))
    mcp.tool()(mcp_tool_handler("create_credential")(credentials.create_credential))
    mcp.tool()(mcp_tool_handler("update_credential")(credentials.update_credential))
    mcp.tool()(mcp_tool_handler("delete_credential")(credentials.delete_credential))

    # Register user management tools
    mcp.tool()(mcp_tool_handler("get_user_info")(users.get_user_info))
    mcp.tool()(mcp_tool_handler("list_users")(users.list_users))
    mcp.tool()(mcp_tool_handler("create_user")(users.create_user))

    logger.info("all_tools_registered")


async def register_all_resources():
    """Register all MCP resources."""
    from .resources import config, status, logs, data

    # Register configuration resources
    mcp.resource("jenkins://config/system")(config.get_system_config)
    mcp.resource("jenkins://config/jobs/{job_name}")(config.get_job_config)
    mcp.resource("jenkins://config/views/{view_name}")(config.get_view_config)
    mcp.resource("jenkins://config/nodes/{node_name}")(config.get_node_config)

    # Register status resources
    mcp.resource("jenkins://status/system")(status.get_system_status)
    mcp.resource("jenkins://status/jobs/{job_name}")(status.get_job_status)
    mcp.resource("jenkins://status/builds/{job_name}/{build_number}")(status.get_build_status)
    mcp.resource("jenkins://status/queue")(status.get_queue_status)
    mcp.resource("jenkins://status/nodes")(status.get_nodes_status)

    # Register log resources
    mcp.resource("jenkins://logs/builds/{job_name}/{build_number}")(logs.get_build_logs)
    mcp.resource("jenkins://logs/system")(logs.get_system_logs)
    mcp.resource("jenkins://logs/nodes/{node_name}")(logs.get_node_logs)

    # Register data resources
    mcp.resource("jenkins://data/artifacts/{job_name}/{build_number}")(data.get_build_artifacts)
    mcp.resource("jenkins://data/plugins")(data.get_plugin_data)
    mcp.resource("jenkins://data/users")(data.get_user_data)

    logger.info("all_resources_registered")


async def register_all_prompts():
    """Register all MCP prompts."""
    from .prompts import automation, troubleshooting, integration, reporting

    # Register automation prompts
    mcp.prompt("jenkins_automation_setup")(automation.automation_setup)
    mcp.prompt("build_pipeline_design")(automation.pipeline_design)
    mcp.prompt("job_template_creation")(automation.job_template_creation)
    mcp.prompt("monitoring_setup")(automation.monitoring_setup)

    # Register troubleshooting prompts
    mcp.prompt("build_failure_analysis")(troubleshooting.build_failure_analysis)
    mcp.prompt("performance_diagnostics")(troubleshooting.performance_diagnostics)
    mcp.prompt("configuration_review")(troubleshooting.configuration_review)
    mcp.prompt("security_audit")(troubleshooting.security_audit)

    # Register integration prompts
    mcp.prompt("git_integration_setup")(integration.git_integration_setup)
    mcp.prompt("notification_setup")(integration.notification_setup)
    mcp.prompt("credential_management_setup")(integration.credential_management_setup)
    mcp.prompt("multi_environment_deployment")(integration.multi_environment_deployment)

    # Register reporting prompts
    mcp.prompt("build_summary_report")(reporting.build_summary_report)
    mcp.prompt("system_health_report")(reporting.system_health_report)
    mcp.prompt("usage_statistics")(reporting.usage_statistics)
    mcp.prompt("compliance_report")(reporting.compliance_report)

    logger.info("all_prompts_registered")


async def setup_server():
    """Set up the MCP server with all tools, resources, and prompts."""
    await register_all_tools()
    await register_all_resources()
    await register_all_prompts()


# Health check endpoint
@mcp.tool()
async def health_check() -> dict:
    """Check the health of the Jenkins MCP server."""
    try:
        client = get_jenkins_client()
        config = get_jenkins_config()

        # Test Jenkins connection
        connection_test = await client.test_connection()

        return {
            "status": "healthy" if connection_test.get("success") else "unhealthy",
            "jenkins_connected": connection_test.get("success", False),
            "jenkins_url": config.url,
            "auth_method": config.auth_method.value,
            "server_version": "1.0.0",
            "timestamp": str(asyncio.get_event_loop().time())
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": str(asyncio.get_event_loop().time())
        }


# Server information endpoint
@mcp.tool()
async def server_info() -> dict:
    """Get information about the Jenkins MCP server."""
    try:
        config = get_jenkins_config()
        client = get_jenkins_client()

        # Get Jenkins system info
        system_info = await client.get_system_info(include_stats=False)

        return {
            "server_name": "jenkins-mcp-server",
            "version": "1.0.0",
            "description": "Comprehensive MCP server for Jenkins automation",
            "jenkins_url": config.url,
            "jenkins_version": system_info.get("description", "Unknown"),
            "auth_method": config.auth_method.value,
            "supported_features": [
                "job_management",
                "build_management",
                "system_monitoring",
                "view_management",
                "credential_management",
                "user_management",
                "real_time_logging",
                "artifact_management"
            ],
            "tools_count": 35,
            "resources_count": 12,
            "prompts_count": 16
        }

    except Exception as e:
        logger.error("server_info_failed", error=str(e))
        return {
            "server_name": "jenkins-mcp-server",
            "version": "1.0.0",
            "error": str(e)
        }


async def main():
    """Main entry point for the Jenkins MCP server."""
    # Set up signal handlers for graceful shutdown
    shutdown_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info("shutdown_signal_received", signal=signum)
        shutdown_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    try:
        # Set up server
        await setup_server()

        logger.info("jenkins_mcp_server_ready")

        # Run server until shutdown
        await shutdown_event.wait()

        logger.info("jenkins_mcp_server_shutting_down")

    except Exception as e:
        logger.error(
            "server_runtime_error",
            error=str(e),
            error_type=type(e).__name__
        )
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())