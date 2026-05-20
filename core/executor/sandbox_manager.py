import ast
import re
import uuid
import time
import threading
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

class SecurityViolationError(Exception):
    """安全违规异常"""
    def __init__(self, message: str, violation_type: str):
        super().__init__(message)
        self.violation_type = violation_type


class SandboxInstance:
    def __init__(self, instance_id: str):
        self.instance_id = instance_id
        self.status = "created"
        self.created_at = datetime.now()
        self.last_used_at = datetime.now()
        self.resource_limits = {"cpu": 1, "memory": 512, "network": False}
        self.execution_count = 0
        self.total_execution_time = 0.0
        self.max_execution_time_per_call = 30


class SandboxManager:
    def __init__(self):
        self.sandboxes: Dict[str, SandboxInstance] = {}
        self.max_sandboxes = 10
        self.max_executions_per_sandbox = 1000
        self.max_code_length = 10000
        self.lock = threading.Lock()
        
        self.dangerous_imports = {
            'subprocess', 'os', 'sys', 'socket', 'urllib', 'http', 'ftplib',
            'shutil', 'ctypes', 'pickle', 'marshal', 'eval', 'exec',
            'tempfile', 'fileinput', 'glob', 'zipfile', 'tarfile',
            'multiprocessing', 'threading', 'asyncio', 'signal', 'pwd', 'grp'
        }
        
        self.dangerous_functions = {
            'os.system', 'os.popen', 'os.spawn', 'os.fork', 'os.kill',
            'subprocess.run', 'subprocess.Popen', 'subprocess.call',
            'shutil.rmtree', 'shutil.move', 'shutil.copy',
            '__import__', 'exec', 'eval', 'compile',
            'open', 'file', 'input', 'raw_input'
        }
        
        self.dangerous_patterns = [
            r"\brm\s+-[rRfF]\b",
            r"\bchmod\b",
            r"\bchown\b",
            r"\bkill\s+\d+\b",
            r"\bsu\s*[-]*",
            r"\bsudo\s+",
            r"\bcat\s+/etc/passwd\b",
            r"\bcat\s+/etc/shadow\b",
            r"\b/proc/\d+/mem\b",
            r"\b/proc/\d+/cmdline\b"
        ]

    def create_sandbox(self, resource_limits: Optional[Dict[str, Any]] = None) -> str:
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

    def execute_code(self, sandbox_id: str, code: str, timeout_seconds: int = 30) -> Dict[str, Any]:
        sandbox = self._get_sandbox(sandbox_id)
        if not sandbox:
            raise ValueError(f"沙箱实例不存在: {sandbox_id}")

        sandbox.last_used_at = datetime.now()

        try:
            self._validate_code(code)
            
            violations = self._detect_security_violations(code)
            if violations:
                return {"success": False, "error": "安全检查失败", "violations": violations}

            sandbox.execution_count += 1
            if sandbox.execution_count > self.max_executions_per_sandbox:
                return {"success": False, "error": "沙箱执行次数已达上限"}

            result = self._execute_python_code(code, timeout_seconds)
            return {"success": True, "result": result, "execution_time": 0.1}
        except SecurityViolationError as e:
            return {"success": False, "error": str(e), "violation_type": e.violation_type}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _validate_code(self, code: str):
        if len(code) > self.max_code_length:
            raise SecurityViolationError("代码长度超过限制", "code_length")
        
        if code.count('\n') > 500:
            raise SecurityViolationError("代码行数超过限制", "code_lines")

    def _detect_security_violations(self, code: str) -> List[str]:
        violations = []
        
        for pattern in self.dangerous_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                violations.append(f"危险命令模式: {pattern}")

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in self.dangerous_imports:
                            violations.append(f"危险模块导入: {alias.name}")
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module in self.dangerous_imports:
                        violations.append(f"危险模块导入: {node.module}")
                
                elif isinstance(node, ast.Name):
                    if node.id in ['open', 'eval', 'exec']:
                        violations.append(f"危险函数调用: {node.id}")
                
                elif isinstance(node, ast.Attribute):
                    attr_chain = self._get_attribute_chain(node)
                    if attr_chain in self.dangerous_functions:
                        violations.append(f"危险属性访问: {attr_chain}")
                
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id in ['__import__', 'eval', 'exec']:
                            violations.append(f"危险函数调用: {node.func.id}")
                    elif isinstance(node.func, ast.Attribute):
                        attr_chain = self._get_attribute_chain(node.func)
                        if attr_chain in self.dangerous_functions:
                            violations.append(f"危险函数调用: {attr_chain}")
        except SyntaxError:
            violations.append("代码语法错误")

        return violations

    def _get_attribute_chain(self, node: ast.Attribute) -> str:
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return '.'.join(reversed(parts))

    def _execute_python_code(self, code: str, timeout_seconds: int) -> Any:
        result_container = {}
        exception_container = {}
        
        def target():
            try:
                local_vars = {}
                exec(code, {}, local_vars)
                if "result" in local_vars:
                    result_container['value'] = local_vars["result"]
                elif "__return__" in local_vars:
                    result_container['value'] = local_vars["__return__"]
                else:
                    result_container['value'] = None
            except Exception as e:
                exception_container['error'] = e

        thread = threading.Thread(target=target)
        thread.start()
        thread.join(timeout=timeout_seconds)

        if thread.is_alive():
            raise SecurityViolationError("代码执行超时", "timeout")
        
        if exception_container:
            raise exception_container['error']
        
        return result_container.get('value')

    def _get_sandbox(self, sandbox_id: str) -> Optional[SandboxInstance]:
        with self.lock:
            return self.sandboxes.get(sandbox_id)

    def destroy_sandbox(self, sandbox_id: str):
        with self.lock:
            if sandbox_id in self.sandboxes:
                self.sandboxes[sandbox_id].status = "destroyed"
                del self.sandboxes[sandbox_id]

    def _cleanup_expired_sandboxes(self):
        expired_ids = []
        with self.lock:
            for sandbox_id, sandbox in self.sandboxes.items():
                if sandbox.is_expired():
                    expired_ids.append(sandbox_id)

        for sandbox_id in expired_ids:
            self.destroy_sandbox(sandbox_id)

    def get_sandbox_status(self, sandbox_id: str) -> Dict[str, Any]:
        sandbox = self._get_sandbox(sandbox_id)
        if not sandbox:
            return {"status": "not_found"}

        return {
            "instance_id": sandbox.instance_id,
            "status": sandbox.status,
            "created_at": sandbox.created_at.isoformat(),
            "last_used_at": sandbox.last_used_at.isoformat(),
            "resource_limits": sandbox.resource_limits,
            "execution_count": sandbox.execution_count
        }

    def get_all_sandboxes(self) -> List[Dict[str, Any]]:
        with self.lock:
            return [self.get_sandbox_status(sid) for sid in self.sandboxes.keys()]
