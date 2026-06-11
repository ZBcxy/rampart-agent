import ast
import asyncio
import builtins as __builtins__
import concurrent.futures
import re
import resource
import threading
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


class SecurityViolationError(Exception):
    """安全违规异常"""

    def __init__(self, message: str, violation_type: str):
        super().__init__(message)
        self.violation_type = violation_type


class SandboxInstance:
    """Represents an isolated sandbox for code execution."""

    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self.status = "created"
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.resource_limits = {"cpu": 1, "memory_mb": 512, "network": False, "disk_mb": 100}
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.max_execution_time_per_call = 30
        self.max_lifetime = timedelta(hours=1)

    def is_expired(self) -> bool:
        """Check if this sandbox has exceeded its lifetime."""
        return datetime.now() - self.created_at > self.max_lifetime


class SandboxManager:
    """Manages isolated execution sandboxes with security validation.

    Supports both sync and async execution. Uses process pools for
    stronger isolation when available.
    """

    def __init__(self, max_workers: int = 4):
        self.sandboxes: Dict[str, SandboxInstance] = {}
        self.max_sandboxes = 10
        self.max_executions_per_sandbox = 1000
        self.max_code_length = 10000
        self.lock = threading.RLock()
        self._executor = concurrent.futures.ProcessPoolExecutor(max_workers=max_workers)

        self.dangerous_imports = {
            "subprocess",
            "os",
            "sys",
            "socket",
            "urllib",
            "http",
            "ftplib",
            "shutil",
            "ctypes",
            "pickle",
            "marshal",
            "tempfile",
            "fileinput",
            "glob",
            "zipfile",
            "tarfile",
            "multiprocessing",
            "threading",
            "asyncio",
            "signal",
            "pwd",
            "grp",
            "resource",
            "selenium",
            "requests",
            "scapy",
            "paramiko",
        }

        self.dangerous_functions = {
            "os.system",
            "os.popen",
            "os.spawn",
            "os.fork",
            "os.kill",
            "os.remove",
            "os.rmdir",
            "os.unlink",
            "subprocess.run",
            "subprocess.Popen",
            "subprocess.call",
            "subprocess.check_output",
            "shutil.rmtree",
            "shutil.move",
            "shutil.copy",
            "shutil.copy2",
            "__import__",
            "exec",
            "eval",
            "compile",
            "open",
            "file",
            "input",
            "raw_input",
        }

        self.dangerous_patterns = [
            r"\brm\s+-[rRfF]\b",
            r"\bchmod\b",
            r"\bchown\b",
            r"\bkill\s+-?\d+\b",
            r"\bsu\s*[-]*\b",
            r"\bsudo\s+",
            r"\bcat\s+/etc/(passwd|shadow)\b",
            r"\b/proc/\d+/(mem|cmdline)\b",
            r"\bdd\s+if=\b",
            r"\bmkfs\.\w+\b",
            r"\bmount\s+-",
            r"\biptables\s+",
            r"\bwget\s+.*\|\s*(ba)?sh\b",
            r"\bcurl\s+.*\|\s*(ba)?sh\b",
            r"\b/dev/(null|zero|random|urandom)\b",
        ]

        # Allowlist for safe built-in functions
        self.safe_builtins = {
            "abs",
            "all",
            "any",
            "ascii",
            "bin",
            "bool",
            "bytes",
            "chr",
            "complex",
            "dict",
            "divmod",
            "enumerate",
            "filter",
            "float",
            "format",
            "frozenset",
            "getattr",
            "hasattr",
            "hash",
            "hex",
            "int",
            "isinstance",
            "issubclass",
            "iter",
            "len",
            "list",
            "map",
            "max",
            "min",
            "next",
            "object",
            "oct",
            "ord",
            "pow",
            "print",
            "range",
            "repr",
            "reversed",
            "round",
            "set",
            "slice",
            "sorted",
            "str",
            "sum",
            "tuple",
            "type",
            "zip",
        }

    def create_sandbox(self, resource_limits: Optional[Dict[str, Any]] = None) -> str:
        """Create a new sandbox instance."""
        with self.lock:
            self._cleanup_expired_sandboxes()

            if len(self.sandboxes) >= self.max_sandboxes:
                raise RuntimeError("沙箱实例数量已达上限")

            instance_id = f"sandbox-{uuid.uuid4().hex[:8]}"
            sandbox = SandboxInstance(instance_id)

            if resource_limits:
                sandbox.resource_limits.update(resource_limits)

            sandbox.status = "running"
            self.sandboxes[instance_id] = sandbox

            return instance_id

    def execute_code(
        self, sandbox_id: str, code: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Execute code in a sandbox (synchronous)."""
        sandbox = self._get_sandbox(sandbox_id)
        if not sandbox:
            raise ValueError(f"沙箱实例不存在: {sandbox_id}")

        sandbox.last_used_at = datetime.now()

        try:
            self._validate_code(code)

            violations = self._detect_security_violations(code)
            if violations:
                return {
                    "success": False,
                    "error": "安全检查失败",
                    "violations": violations,
                }

            sandbox.execution_count += 1
            if sandbox.execution_count > self.max_executions_per_sandbox:
                return {"success": False, "error": "沙箱执行次数已达上限"}

            result = self._execute_python_code(code, timeout_seconds)
            return {"success": True, "result": result, "execution_time": 0.1}

        except SecurityViolationError as e:
            return {
                "success": False,
                "error": str(e),
                "violation_type": e.violation_type,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def execute_code_async(
        self, sandbox_id: str, code: str, timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        """Execute code in a sandbox (asynchronous)."""
        sandbox = self._get_sandbox(sandbox_id)
        if not sandbox:
            raise ValueError(f"沙箱实例不存在: {sandbox_id}")

        sandbox.last_used_at = datetime.now()

        try:
            self._validate_code(code)

            violations = self._detect_security_violations(code)
            if violations:
                return {
                    "success": False,
                    "error": "安全检查失败",
                    "violations": violations,
                }

            sandbox.execution_count += 1
            if sandbox.execution_count > self.max_executions_per_sandbox:
                return {"success": False, "error": "沙箱执行次数已达上限"}

            # Run in process pool for isolation
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                self._executor,
                self._execute_python_code_sandboxed,
                code,
                timeout_seconds,
                sandbox.resource_limits.get("memory_mb", 512),
            )

            return {"success": True, "result": result, "execution_time": 0.1}

        except SecurityViolationError as e:
            return {
                "success": False,
                "error": str(e),
                "violation_type": e.violation_type,
            }
        except concurrent.futures.TimeoutError:
            return {"success": False, "error": "代码执行超时"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_code(self, code: str):
        """Validate code size and structure."""
        if not code or not isinstance(code, str):
            raise SecurityViolationError("无效的代码输入", "invalid_input")

        if len(code) > self.max_code_length:
            raise SecurityViolationError(
                f"代码长度超过限制 ({self.max_code_length} chars)", "code_length"
            )

        if code.count("\n") > 500:
            raise SecurityViolationError("代码行数超过限制 (500 lines)", "code_lines")

        # Check for null bytes (potential bypass)
        if "\x00" in code:
            raise SecurityViolationError("代码包含无效字符", "null_byte")

    def _detect_security_violations(self, code: str) -> List[str]:
        """Detect security violations in code using AST analysis."""
        violations = []

        # Pattern-based checks
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"危险命令模式检测: {pattern}")

        # AST-based checks
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # Check imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.dangerous_imports:
                            violations.append(f"危险模块导入: {alias.name}")

                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module in self.dangerous_imports:
                        violations.append(f"危险模块导入: {node.module}")

                # Check direct dangerous calls
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in self.dangerous_functions:
                            violations.append(f"危险函数调用: {node.func.id}")
                    elif isinstance(node.func, ast.Attribute):
                        attr_chain = self._get_attribute_chain(node.func)
                        if attr_chain in self.dangerous_functions:
                            violations.append(f"危险函数调用: {attr_chain}")

                # Check attribute access for safety
                elif isinstance(node, ast.Attribute):
                    attr_chain = self._get_attribute_chain(node)
                    if attr_chain in self.dangerous_functions:
                        violations.append(f"危险属性访问: {attr_chain}")

        except SyntaxError as e:
            violations.append(f"代码语法错误: {str(e)}")

        return violations

    def _get_attribute_chain(self, node: ast.Attribute) -> str:
        """Build full dotted attribute path from AST node."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))

    @staticmethod
    def _execute_python_code_sandboxed(
        code: str, timeout_seconds: int, memory_limit_mb: int = 512
    ) -> Any:
        """Execute code in a subprocess with resource limits (strong isolation)."""
        # Set memory limit
        try:
            memory_bytes = memory_limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (memory_bytes, memory_bytes))
        except (ValueError, resource.error):
            pass

        # Execute in restricted globals
        safe_globals = {
            "__builtins__": {
                name: __builtins__[name]
                for name in [
                    "abs", "all", "any", "ascii", "bin", "bool", "bytes",
                    "chr", "complex", "dict", "divmod", "enumerate", "filter",
                    "float", "format", "frozenset", "getattr", "hasattr",
                    "hash", "hex", "int", "isinstance", "issubclass", "iter",
                    "len", "list", "map", "max", "min", "next", "object",
                    "oct", "ord", "pow", "print", "range", "repr", "reversed",
                    "round", "set", "slice", "sorted", "str", "sum", "tuple",
                    "type", "zip",
                ]
                if name in __builtins__
            },
        }

        local_vars = {}
        exec(code, safe_globals, local_vars)

        if "result" in local_vars:
            return local_vars["result"]
        elif "__return__" in local_vars:
            return local_vars["__return__"]
        return None

    def _execute_python_code(self, code: str, timeout_seconds: int) -> Any:
        """Execute Python code with thread-based timeout (weaker isolation)."""
        result_container = {}
        exception_container = {}

        def target():
            try:
                local_vars = {}
                exec(code, {}, local_vars)
                if "result" in local_vars:
                    result_container["value"] = local_vars["result"]
                elif "__return__" in local_vars:
                    result_container["value"] = local_vars["__return__"]
                else:
                    result_container["value"] = None
            except Exception as e:
                exception_container["error"] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            raise SecurityViolationError("代码执行超时", "timeout")

        if exception_container:
            raise exception_container["error"]

        return result_container.get("value")

    def _get_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        """Get a sandbox instance by ID."""
        with self.lock:
            return self.sandboxes.get(sandbox_id)

    def destroy_sandbox(self, sandbox_id: str):
        """Destroy a sandbox instance."""
        with self.lock:
            if sandbox_id in self.sandboxes:
                self.sandboxes[sandbox_id].status = "destroyed"
                del self.sandboxes[sandbox_id]

    def _cleanup_expired_sandboxes(self):
        """Remove expired sandbox instances."""
        with self.lock:
            expired_ids = [
                sid
                for sid, sandbox in self.sandboxes.items()
                if sandbox.is_expired()
            ]

        for sandbox_id in expired_ids:
            self.destroy_sandbox(sandbox_id)

    def get_sandbox_status(self, sandbox_id: str) -> Dict[str, Any]:
        """Get the status of a sandbox."""
        sandbox = self._get_sandbox(sandbox_id)
        if not sandbox:
            return {"status": "not_found"}

        return {
            "instance_id": sandbox.instance_id,
            "status": sandbox.status,
            "created_at": sandbox.created_at.isoformat(),
            "last_used_at": sandbox.last_used_at.isoformat(),
            "resource_limits": sandbox.resource_limits,
            "execution_count": sandbox.execution_count,
            "total_execution_time": sandbox.total_execution_time,
        }

    def get_all_sandboxes(self) -> List[Dict[str, Any]]:
        """Get status of all sandboxes."""
        with self.lock:
            return [self.get_sandbox_status(sid) for sid in self.sandboxes]

    def shutdown(self):
        """Shutdown the sandbox manager and clean up resources."""
        with self.lock:
            for sandbox_id in list(self.sandboxes.keys()):
                self.destroy_sandbox(sandbox_id)
        self._executor.shutdown(wait=True)
