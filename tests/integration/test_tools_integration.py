"""Integration tests for the tools ecosystem."""

import json
import os
import tempfile

import pytest
from tools.registry import ToolRegistry


@pytest.fixture
def registry():
    r = ToolRegistry()
    r.register_all()
    return r


class TestFileTools:
    def test_write_and_read(self, registry):
        # file_write requires confirmation, use auto_confirm callback
        result = registry.execute(
            "file_write",
            path="/tmp/polaris_test_write.txt",
            content="Hello World!",
            mode="w",
            confirm_callback=lambda msg: True,
        )
        assert result["success"] is True

        # Read back
        result = registry.execute("file_read", path="/tmp/polaris_test_write.txt")
        assert result["success"] is True
        assert "Hello World!" in result["result"]["content"]

        # Cleanup
        os.unlink("/tmp/polaris_test_write.txt")

    def test_list_directory(self, registry):
        result = registry.execute("file_list", path="/tmp", pattern="*.txt", recursive=False)
        assert result["success"] is True
        assert "items" in result["result"]

    def test_file_info(self, registry):
        result = registry.execute("file_info", path="/etc/hostname")
        if result["success"]:
            assert "size_bytes" in result["result"]


class TestWebTools:
    def test_url_encode_decode(self, registry):
        # Encode
        result = registry.execute("url_encode", text="hello world!", operation="encode")
        assert result["success"]
        assert "%" in result["result"]["output"]

        # Decode
        result = registry.execute("url_encode", text="hello%20world%21", operation="decode")
        assert result["success"]
        assert result["result"]["output"] == "hello world!"

    def test_web_fetch_invalid(self, registry):
        result = registry.execute("web_fetch", url="http://invalid.nonexistent.example.local")
        # Should not crash; returns error in result
        assert isinstance(result, dict)


class TestCodeTools:
    def test_python_exec(self, registry):
        result = registry.execute("python_exec", code="result = 2 + 2\nprint('done')")
        assert result["success"]
        assert result["result"]["result"] == 4
        assert "done" in result["result"]["stdout"]

    def test_code_analyze(self, registry):
        code = '''
def hello(name):
    return f"Hello, {name}"

class Greeter:
    def greet(self, name):
        return hello(name)
'''
        result = registry.execute("code_analyze", code=code)
        assert result["success"]
        # hello + greet = 2 functions (greet is inside class but counted as FunctionDef)
        assert result["result"]["function_count"] == 2
        assert result["result"]["class_count"] == 1

    def test_json_format(self, registry):
        result = registry.execute("json_format", json_string='{"b":2,"a":1}', operation="format")
        assert result["success"]
        assert '"a": 1' in result["result"]["formatted"]

    def test_regex_test(self, registry):
        result = registry.execute("regex_test", pattern=r"\d{3}-\d{4}", text="Phone: 123-4567 and 987-6543")
        assert result["success"]
        assert result["result"]["match_count"] == 2

    def test_python_exec_timeout(self, registry):
        # Busy-loop for timeout testing (no imports needed in sandbox)
        result = registry.execute("python_exec", code="x = 0\nwhile x < 10**9:\n x += 1", timeout=1)
        assert result["success"] is True
        assert "timed out" in result["result"].get("error", "").lower()


class TestDataTools:
    def test_text_stats(self, registry):
        result = registry.execute("text_process", text="Hello world! This is a test.", operation="stats")
        assert result["success"]
        assert result["result"]["word_count"] == 6
        assert result["result"]["line_count"] == 1

    def test_calc(self, registry):
        result = registry.execute("calc", expression="2 + 3 * 4")
        assert result["success"]
        assert result["result"]["result"] == 14

    def test_csv_parse(self, registry):
        csv_data = "name,age,city\nAlice,30,NYC\nBob,25,LA"
        result = registry.execute("csv_parse", csv_content=csv_data)
        assert result["success"]
        assert result["result"]["row_count"] == 2
        assert result["result"]["rows"][0]["name"] == "Alice"

    def test_data_transform(self, registry):
        data = json.dumps([{"name": "A", "value": 10}, {"name": "B", "value": 5}, {"name": "C", "value": 20}])
        result = registry.execute("data_transform", data=data, operation="sort", params={"key": "value"})
        assert result["success"]
        assert result["result"]["result"][0]["value"] == 5


class TestSystemTools:
    def test_system_info(self, registry):
        result = registry.execute("system_info")
        assert result["success"]
        assert "python_version" in result["result"]

    def test_time_now(self, registry):
        result = registry.execute("time_now")
        assert result["success"]
        assert "iso" in result["result"]
        assert "year" in result["result"]

    def test_env_var(self, registry):
        result = registry.execute("env_var", name="PATH")
        assert result["success"]
        assert result["result"]["exists"] is True


class TestToolRegistry:
    def test_search_tools(self, registry):
        results = registry.search("file")
        assert len(results) > 0
        assert any("file" in t.name for t in results)

    def test_category_listing(self, registry):
        file_tools = registry.list_by_category("file")
        assert len(file_tools) >= 9

        web_tools = registry.list_by_category("web")
        assert len(web_tools) >= 4

    def test_openai_functions(self, registry):
        functions = registry.get_openai_functions(categories=["code"])
        assert len(functions) == 4
        for func in functions:
            assert "function" in func
            assert "name" in func["function"]

    def test_execution_stats(self, registry):
        registry.execute("calc", expression="1+1")
        stats = registry.get_execution_stats()
        assert stats["total_executions"] > 0
