"""
Jenkins MCP Prompts

Module containing all MCP prompt implementations for Jenkins guidance and automation.
"""

from . import automation
from . import troubleshooting
from . import integration
from . import reporting

__all__ = ["automation", "troubleshooting", "integration", "reporting"]