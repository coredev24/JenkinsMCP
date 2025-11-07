"""
Jenkins MCP Server

A comprehensive Model Context Protocol (MCP) server for Jenkins automation.
Provides programmatic access to Jenkins UI functionality through MCP tools,
resources, and prompts.
"""

__version__ = "1.0.0"
__author__ = "Jenkins MCP Team"
__email__ = "team@jenkins-mcp.com"

from .server import mcp
from .config import JenkinsConfig
from .client import JenkinsClient

__all__ = ["mcp", "JenkinsConfig", "JenkinsClient"]