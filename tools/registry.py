"""Tool Registry - Central registry for all agent tools.

Provides tool discovery, schema validation, execution tracking,
and OpenAI-compatible function calling schema generation.
"""

import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolDefinition:
    """Definition of a tool that the agent can use."""

    name: str
    description: str
    func: Callable
    parameters: Dict[str, Any] = field(default_factory=dict)  # JSON Schema
    category: str = "general"
    requires_confirmation: bool = False
    timeout_seconds: int = 30
    version: str = "1.0.0"
    tags: List[str] = field(default_factory=list)

    def to_openai_function(self) -> Dict[str, Any]:
        """Generate OpenAI-compatible function definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.parameters,
                    "required": [
                        k for k, v in self.parameters.items()
                        if v.get("required", False)
                    ],
                },
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        """Full definition as dict."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "category": self.category,
            "requires_confirmation": self.requires_confirmation,
            "timeout_seconds": self.timeout_seconds,
            "version": self.version,
            "tags": self.tags,
        }


@dataclass
class ToolExecution:
    """Record of a single tool execution."""

    execution_id: str
    tool_name: str
    arguments: Dict[str, Any]
    result: Optional[Any]
    error: Optional[str]
    execution_time: float
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True


class ToolRegistry:
    """Registry for all agent tools with execution tracking.

    Usage:
        registry = ToolRegistry()
        registry.register(ToolDefinition(
            name="file_read",
            description="Read a file from the filesystem",
            func=lambda path: open(path).read(),
            parameters={"path": {"type": "string", "description": "File path"}},
            category="file",
        ))
        result = registry.execute("file_read", path="/tmp/data.txt")
    """

    def __init__(self):
        self._tools: Dict[str, ToolDefinition] = {}
        self._executions: List[ToolExecution] = []
        self._category_index: Dict[str, List[str]] = defaultdict(list)
        self._tag_index: Dict[str, List[str]] = defaultdict(list)
        self._execution_counters: Dict[str, int] = defaultdict(int)
        self._max_execution_history = 1000

    def register(self, tool: ToolDefinition):
        """Register a tool."""
        self._tools[tool.name] = tool
        self._category_index[tool.category].append(tool.name)
        for tag in tool.tags:
            self._tag_index[tag].append(tool.name)

    def register_many(self, tools: List[ToolDefinition]):
        """Register multiple tools at once."""
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> List[str]:
        """List all tool names."""
        return list(self._tools.keys())

    def list_by_category(self, category: str) -> List[str]:
        """List tools in a category."""
        return self._category_index.get(category, [])

    def list_by_tag(self, tag: str) -> List[str]:
        """List tools by tag."""
        return self._tag_index.get(tag, [])

    def search(self, query: str) -> List[ToolDefinition]:
        """Search for tools by name or description."""
        query_lower = query.lower()
        results = []
        for tool in self._tools.values():
            if query_lower in tool.name.lower() or query_lower in tool.description.lower():
                results.append(tool)
        return results

    def execute(
        self,
        tool_name: str,
        confirm_callback: Optional[Callable[[str], bool]] = None,
        **kwargs,
    ) -> Any:
        """Execute a tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute
            confirm_callback: Optional callback for tools requiring confirmation
            **kwargs: Tool arguments

        Returns:
            Tool execution result

        Raises:
            ValueError: If tool not found
        """
        import uuid

        tool = self._tools.get(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found. Available: {list(self._tools.keys())}")

        # Confirmation check
        if tool.requires_confirmation:
            if confirm_callback:
                if not confirm_callback(f"Confirm execution of '{tool_name}' with {kwargs}?"):
                    return {"status": "cancelled", "reason": "User declined confirmation"}
            else:
                return {
                    "status": "requires_confirmation",
                    "tool": tool_name,
                    "arguments": kwargs,
                }

        execution_id = f"exec-{uuid.uuid4().hex[:8]}"
        start = time.perf_counter()
        error = None
        result = None
        success = True

        try:
            result = tool.func(**kwargs)
        except Exception as e:
            error = str(e)
            success = False

        execution_time = time.perf_counter() - start

        # Record execution
        execution = ToolExecution(
            execution_id=execution_id,
            tool_name=tool_name,
            arguments=kwargs,
            result=result,
            error=error,
            execution_time=execution_time,
            success=success,
        )
        self._executions.append(execution)
        self._execution_counters[tool_name] += 1

        # Trim history
        if len(self._executions) > self._max_execution_history:
            self._executions = self._executions[-self._max_execution_history:]

        if error:
            return {"success": False, "error": error, "execution_time": execution_time}

        return {"success": True, "result": result, "execution_time": execution_time}

    def get_openai_functions(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get all tools as OpenAI-compatible function definitions.

        Args:
            categories: Optional filter by categories

        Returns:
            List of function schema dicts
        """
        functions = []
        for tool in self._tools.values():
            if categories and tool.category not in categories:
                continue
            functions.append(tool.to_openai_function())
        return functions

    def get_anthropic_tools(self, categories: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """Get all tools as Anthropic-compatible tool definitions."""
        tools = []
        for tool in self._tools.values():
            if categories and tool.category not in categories:
                continue
            tools.append({
                "name": tool.name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": tool.parameters,
                    "required": [
                        k for k, v in tool.parameters.items()
                        if v.get("required", False)
                    ],
                },
            })
        return tools

    def get_recent_executions(self, count: int = 20) -> List[ToolExecution]:
        """Get most recent tool executions."""
        return self._executions[-count:]

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        total = len(self._executions)
        if total == 0:
            return {"total_executions": 0}

        successful = sum(1 for e in self._executions if e.success)
        avg_time = sum(e.execution_time for e in self._executions) / total

        return {
            "total_executions": total,
            "successful": successful,
            "failed": total - successful,
            "success_rate": successful / total if total else 0,
            "average_execution_time": avg_time,
            "executions_by_tool": dict(self._execution_counters),
            "total_tools": len(self._tools),
            "categories": list(self._category_index.keys()),
        }

    def register_all(self):
        """Register all built-in tools from all categories."""
        from tools.file_tools import register_file_tools
        from tools.web_tools import register_web_tools
        from tools.code_tools import register_code_tools
        from tools.data_tools import register_data_tools
        from tools.system_tools import register_system_tools

        register_file_tools(self)
        register_web_tools(self)
        register_code_tools(self)
        register_data_tools(self)
        register_system_tools(self)

    def __len__(self):
        return len(self._tools)

    def __contains__(self, name: str):
        return name in self._tools
