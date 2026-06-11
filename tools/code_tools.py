"""Code Execution & Analysis Tools."""

import ast
from typing import Any, Dict

from tools.registry import ToolDefinition, ToolRegistry


def register_code_tools(registry: ToolRegistry):
    """Register all code-related tools."""
    registry.register_many([
        ToolDefinition(
            name="python_exec",
            description="Execute Python code in a sandboxed environment. Returns stdout and result.",
            func=_python_exec,
            parameters={
                "code": {"type": "string", "description": "Python code to execute"},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default: 10)"},
            },
            category="code",
            tags=["python", "execution", "compute"],
        ),
        ToolDefinition(
            name="code_analyze",
            description="Analyze Python code: extract functions, classes, imports, and complexity.",
            func=_code_analyze,
            parameters={
                "code": {"type": "string", "description": "Python source code to analyze"},
            },
            category="code",
            tags=["python", "analysis", "static"],
        ),
        ToolDefinition(
            name="json_format",
            description="Format, validate, or query JSON data.",
            func=_json_format,
            parameters={
                "json_string": {"type": "string", "description": "JSON string to process"},
                "operation": {"type": "string", "description": "'format', 'validate', or 'query' with a JMESPath expression"},
            },
            category="code",
            tags=["json", "format", "data"],
        ),
        ToolDefinition(
            name="regex_test",
            description="Test a regular expression against text. Returns all matches.",
            func=_regex_test,
            parameters={
                "pattern": {"type": "string", "description": "Regular expression pattern"},
                "text": {"type": "string", "description": "Text to test against"},
                "flags": {"type": "string", "description": "Regex flags: i=IGNORECASE, m=MULTILINE, s=DOTALL"},
                "replace": {"type": "string", "description": "Optional: replacement string (enables substitution mode)"},
            },
            category="code",
            tags=["regex", "text", "utility"],
        ),
    ])


def _python_exec(code: str, timeout: int = 10) -> Dict[str, Any]:
    """Execute Python code safely."""
    import io
    import sys
    import threading

    result_container = {}
    error_container = {}

    def target():
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture

        try:
            # Restricted builtins
            safe_builtins = {
                "abs": abs, "all": all, "any": any, "bool": bool, "dict": dict,
                "enumerate": enumerate, "filter": filter, "float": float, "int": int,
                "len": len, "list": list, "map": map, "max": max, "min": min,
                "print": print, "range": range, "round": round, "set": set,
                "sorted": sorted, "str": str, "sum": sum, "tuple": tuple,
                "type": type, "zip": zip, "True": True, "False": False, "None": None,
            }
            local_vars = {}
            exec(compile(code, "<sandbox>", "exec"), {"__builtins__": safe_builtins}, local_vars)

            if "result" in local_vars:
                result_container["value"] = local_vars["result"]
            else:
                result_container["value"] = local_vars.get("__return__")
        except Exception as e:
            error_container["error"] = f"{type(e).__name__}: {str(e)}"
        finally:
            sys.stdout = old_stdout
            result_container["stdout"] = stdout_capture.getvalue()

    thread = threading.Thread(target=target)
    thread.start()
    thread.join(timeout=min(timeout, 30))

    if thread.is_alive():
        return {"error": "Execution timed out", "stdout": result_container.get("stdout", "")}

    if error_container:
        return {"error": error_container["error"], "stdout": result_container.get("stdout", "")}

    return {
        "result": result_container.get("value"),
        "stdout": result_container.get("stdout", ""),
    }


def _code_analyze(code: str) -> Dict[str, Any]:
    """Analyze Python code structure."""
    try:
        tree = ast.parse(code)

        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append({
                    "name": node.name,
                    "line": node.lineno,
                    "args": [a.arg for a in node.args.args],
                    "decorators": [
                        d.id if isinstance(d, ast.Name) else str(d)
                        for d in node.decorator_list
                    ],
                })
            elif isinstance(node, ast.ClassDef):
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "methods": [
                        n.name for n in node.body
                        if isinstance(n, ast.FunctionDef)
                    ],
                })
            elif isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.append(f"{node.module}.{node.names[0].name}" if node.names else str(node.module))

        return {
            "total_lines": code.count("\n") + 1,
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "function_count": len(functions),
            "class_count": len(classes),
        }
    except SyntaxError as e:
        return {"error": f"Syntax error: {e}", "line": e.lineno}


def _json_format(json_string: str, operation: str = "format") -> Dict[str, Any]:
    """Process JSON: format, validate, or query."""
    import json as json_module

    try:
        data = json_module.loads(json_string)
    except json_module.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}", "position": e.pos}

    if operation == "validate":
        return {"valid": True, "type": type(data).__name__, "keys": list(data.keys()) if isinstance(data, dict) else None}

    elif operation == "format":
        formatted = json_module.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)
        return {"formatted": formatted, "type": type(data).__name__}

    elif operation.startswith("query:") or operation.startswith("."):
        # JMESPath query support
        try:
            import jmespath
            expression = operation.replace("query:", "").strip()
            result = jmespath.search(expression, data)
            return {"query": expression, "result": result, "type": type(result).__name__}
        except ImportError:
            return {"error": "JMESPath not installed. Install with: pip install jmespath"}

    return {"error": f"Unknown operation: {operation}"}


def _regex_test(pattern: str, text: str, flags: str = "", replace: str = None) -> Dict[str, Any]:
    """Test regex pattern against text."""
    import re

    re_flags = 0
    if "i" in flags:
        re_flags |= re.IGNORECASE
    if "m" in flags:
        re_flags |= re.MULTILINE
    if "s" in flags:
        re_flags |= re.DOTALL

    try:
        compiled = re.compile(pattern, re_flags)
    except re.error as e:
        return {"error": f"Invalid regex: {e}", "pattern": pattern}

    if replace is not None:
        result = compiled.sub(replace, text)
        return {"operation": "replace", "pattern": pattern, "result": result[:5000]}

    matches = []
    for m in compiled.finditer(text):
        match_info = {
            "match": m.group(),
            "start": m.start(),
            "end": m.end(),
            "groups": m.groups(),
        }
        if m.groupdict():
            match_info["named_groups"] = m.groupdict()
        matches.append(match_info)

    return {
        "pattern": pattern,
        "text_length": len(text),
        "match_count": len(matches),
        "matches": matches[:100],
    }
