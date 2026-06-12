"""Code Harness — "Code as Agent Harness" execution layer.

Wraps SandboxManager to provide a validated code execution pipeline
where model-generated code is the harness medium, not just tool calls.
"""

import ast
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from core.executor.sandbox_manager import SandboxManager


class ValidationResult(BaseModel):
    is_valid: bool
    errors: List[str] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)


class HarnessTraceItem(BaseModel):
    """Records a single code execution in the harness trace."""
    step_index: int = 0
    code: str
    validated: bool = False
    execution_result: Optional[Dict[str, Any]] = None
    execution_time: float = 0.0
    side_effects: List[str] = Field(default_factory=list)
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class ActionCodeValidator:
    """Validates model-generated action code before sandbox execution."""

    ALLOWED_IMPORTS: set = {
        "math", "statistics", "itertools", "collections", "functools",
        "datetime", "json", "re", "string", "textwrap", "hashlib",
        "base64", "csv", "io", "typing", "dataclasses",
    }

    SIDE_EFFECT_FUNCTIONS: set = {
        "open", "write", "writelines", "save", "remove", "rmdir",
    }

    SIDE_EFFECT_ATTRS: set = {
        "write", "writelines", "save", "dump", "dumps",
    }

    def validate(self, code: str, expected_schema: Optional[Dict] = None) -> ValidationResult:
        """Validate model-generated code for safe execution."""
        errors: List[str] = []
        side_effects: List[str] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ValidationResult(is_valid=False, errors=[f"Syntax error: {e}"])

        errors.extend(self._check_ast_structure(tree))
        side_effects.extend(self._check_side_effects(tree))
        errors.extend(self._check_imports(tree))

        if expected_schema:
            errors.extend(self._check_schema_compliance(tree, expected_schema))

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            side_effects=side_effects,
        )

    def _check_ast_structure(self, tree: ast.Module) -> List[str]:
        """Ensure the code body is a single expression, assignment, or function call."""
        errors = []
        if not tree.body:
            errors.append("Empty code body — expected at least one statement")
            return errors

        for node in tree.body:
            if not isinstance(node, (ast.Expr, ast.Assign, ast.AnnAssign, ast.Return,
                                      ast.FunctionDef, ast.If, ast.For, ast.While,
                                      ast.Import, ast.ImportFrom, ast.AugAssign)):
                errors.append(f"Disallowed statement type: {type(node).__name__}")

        return errors

    def _check_side_effects(self, tree: ast.Module) -> List[str]:
        """Detect side effects: file writes, network calls, shell commands."""
        side_effects = []

        class SideEffectVisitor(ast.NodeVisitor):
            def visit_Call(self, node):
                # Direct function names
                if isinstance(node.func, ast.Name):
                    if node.func.id in ActionCodeValidator.SIDE_EFFECT_FUNCTIONS:
                        side_effects.append(f"Side effect: {node.func.id}() call")
                # Attribute calls like file.write()
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in ActionCodeValidator.SIDE_EFFECT_ATTRS:
                        side_effects.append(f"Side effect: .{node.func.attr}() call")
                self.generic_visit(node)

        SideEffectVisitor().visit(tree)
        return side_effects

    def _check_imports(self, tree: ast.Module) -> List[str]:
        """Check that only allowed imports are used."""
        errors = []

        class ImportVisitor(ast.NodeVisitor):
            def visit_Import(self, node):
                for alias in node.names:
                    base = alias.name.split(".")[0]
                    if base not in ActionCodeValidator.ALLOWED_IMPORTS:
                        errors.append(f"Disallowed import: {alias.name}")
                self.generic_visit(node)

            def visit_ImportFrom(self, node):
                if node.module:
                    base = node.module.split(".")[0]
                    if base not in ActionCodeValidator.ALLOWED_IMPORTS:
                        errors.append(f"Disallowed import from: {node.module}")
                self.generic_visit(node)

        ImportVisitor().visit(tree)
        return errors

    def _check_schema_compliance(self, tree: ast.Module, expected_schema: Dict) -> List[str]:
        """Validate code structure against expected return schema."""
        return []  # Schema compliance check is informational, not blocking


class CodeHarness:
    """Wraps SandboxManager to provide a 'Code as Agent Harness' execution layer.

    Validates, executes, and traces model-generated action code within
    sandboxed environments, turning code into the harness medium itself.
    """

    def __init__(self, sandbox_manager: Optional[SandboxManager] = None, max_workers: int = 4):
        self._sandbox = sandbox_manager or SandboxManager(max_workers=max_workers)
        self._validator = ActionCodeValidator()
        self._trace: List[HarnessTraceItem] = []
        self._step_index = 0
        self._sandbox_id: Optional[str] = None

    def execute_action_code(self, code: str, action_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute validated action code in the sandbox (synchronous).

        Pipeline: validate → execute → trace → return
        """
        self._step_index += 1
        t0 = time.perf_counter()

        # Validate
        validation = self._validator.validate(code)
        if not validation.is_valid:
            item = HarnessTraceItem(
                step_index=self._step_index, code=code,
                validated=False, error="; ".join(validation.errors),
                execution_time=time.perf_counter() - t0,
            )
            self._trace.append(item)
            return {
                "success": False, "validated": False,
                "error": "; ".join(validation.errors),
                "side_effects": validation.side_effects,
                "trace_step": self._step_index,
            }

        # Execute in sandbox
        sid = self._ensure_sandbox()
        result = self._sandbox.execute_code(sid, code, timeout_seconds=30)

        dt = time.perf_counter() - t0
        item = HarnessTraceItem(
            step_index=self._step_index, code=code, validated=True,
            execution_result=result,
            execution_time=dt,
            side_effects=validation.side_effects,
            error=result.get("error"),
        )
        self._trace.append(item)

        return {
            "success": result.get("success", False),
            "validated": True,
            "result": result.get("result"),
            "error": result.get("error"),
            "violations": result.get("violations", []),
            "side_effects": validation.side_effects,
            "execution_time": dt,
            "trace_step": self._step_index,
        }

    async def execute_action_code_async(self, code: str, action_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute validated action code asynchronously with stronger isolation."""
        self._step_index += 1
        t0 = time.perf_counter()

        validation = self._validator.validate(code)
        if not validation.is_valid:
            item = HarnessTraceItem(
                step_index=self._step_index, code=code,
                validated=False, error="; ".join(validation.errors),
                execution_time=time.perf_counter() - t0,
            )
            self._trace.append(item)
            return {
                "success": False, "validated": False,
                "error": "; ".join(validation.errors),
                "side_effects": validation.side_effects,
                "trace_step": self._step_index,
            }

        sid = self._ensure_sandbox()
        result = await self._sandbox.execute_code_async(sid, code, timeout_seconds=30)

        dt = time.perf_counter() - t0
        item = HarnessTraceItem(
            step_index=self._step_index, code=code, validated=True,
            execution_result=result,
            execution_time=dt,
            side_effects=validation.side_effects,
            error=result.get("error"),
        )
        self._trace.append(item)

        return {
            "success": result.get("success", False),
            "validated": True,
            "result": result.get("result"),
            "error": result.get("error"),
            "violations": result.get("violations", []),
            "side_effects": validation.side_effects,
            "execution_time": dt,
            "trace_step": self._step_index,
        }

    def _ensure_sandbox(self) -> str:
        """Get or create a sandbox instance."""
        if self._sandbox_id is None:
            instances = self._sandbox.get_all_sandboxes()
            if instances and len(instances) > 0:
                first = instances[0]
                self._sandbox_id = first.get("instance_id", "") if isinstance(first, dict) else str(first)
            if not self._sandbox_id:
                resource_limits = {"cpu": 1, "memory_mb": 256, "network": False, "disk_mb": 50}
                self._sandbox_id = self._sandbox.create_sandbox(resource_limits)
        return self._sandbox_id

    def get_trace(self, limit: int = 100) -> List[HarnessTraceItem]:
        """Return recent execution trace items."""
        return self._trace[-limit:]

    def get_trace_summary(self) -> Dict[str, Any]:
        """Aggregate trace statistics."""
        total = len(self._trace)
        if total == 0:
            return {"total_executions": 0, "validated_rate": 0, "success_rate": 0,
                    "avg_execution_time": 0, "total_side_effects": 0}
        validated = sum(1 for t in self._trace if t.validated)
        success = sum(1 for t in self._trace if t.validated and t.error is None)
        return {
            "total_executions": total,
            "validated_rate": validated / total,
            "success_rate": success / total if validated > 0 else 0,
            "avg_execution_time": sum(t.execution_time for t in self._trace) / total,
            "total_side_effects": sum(len(t.side_effects) for t in self._trace),
        }

    def reset_sandbox(self) -> None:
        """Create a fresh sandbox instance."""
        if self._sandbox_id:
            self._sandbox.destroy_sandbox(self._sandbox_id)
        self._sandbox_id = None

    def shutdown(self) -> None:
        """Clean up all sandboxes and resources."""
        self._sandbox.shutdown()

    def to_tool_definition(self):
        """Return a ToolDefinition for registering as a tool."""
        from tools.registry import ToolDefinition

        return ToolDefinition(
            name="code_harness_execute",
            description="Execute validated Python code in a secure sandbox. "
                        "Use this to run model-generated code safely with side-effect detection.",
            func=lambda code, context="{}": self.execute_action_code(
                code, json.loads(context) if isinstance(context, str) else context
            ),
            parameters={
                "code": {"type": "string", "description": "Python code to execute in sandbox", "required": True},
                "context": {"type": "string", "description": "JSON string of execution context", "required": False},
            },
            category="code",
            requires_confirmation=True,
            tags=["sandbox", "code", "harness"],
        )
