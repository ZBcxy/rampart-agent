"""Polaris Agent Tools - 20+ Executable Tools

Tools are organized into categories:
- file: File system operations
- web: Web search and HTTP requests
- code: Code execution and analysis
- data: Data processing and transformation
- system: System utilities and monitoring
- ai: AI/LLM-powered tools

Usage:
    from tools import ToolRegistry
    registry = ToolRegistry()
    registry.register_all()
    result = registry.execute("file_read", path="/tmp/data.txt")
"""

from tools.registry import ToolRegistry
from tools.file_tools import register_file_tools
from tools.web_tools import register_web_tools
from tools.code_tools import register_code_tools
from tools.data_tools import register_data_tools
from tools.system_tools import register_system_tools

__all__ = [
    "ToolRegistry",
    "register_file_tools",
    "register_web_tools",
    "register_code_tools",
    "register_data_tools",
    "register_system_tools",
]
