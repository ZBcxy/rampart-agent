"""Web Tools - HTTP requests, web search, content fetching."""

import urllib.parse
from typing import Any, Dict, Optional

import requests

from tools.registry import ToolDefinition, ToolRegistry


def register_web_tools(registry: ToolRegistry):
    """Register all web tools."""
    registry.register_many([
        ToolDefinition(
            name="web_search",
            description="Search the web using DuckDuckGo instant answers.",
            func=_web_search,
            parameters={
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (default: 10)"},
            },
            category="web",
            tags=["search", "web", "information"],
        ),
        ToolDefinition(
            name="web_fetch",
            description="Fetch and extract text content from a URL.",
            func=_web_fetch,
            parameters={
                "url": {"type": "string", "description": "URL to fetch"},
                "max_length": {"type": "integer", "description": "Max content length to return"},
                "extract_text": {"type": "boolean", "description": "Extract readable text from HTML"},
            },
            category="web",
            tags=["http", "fetch", "scraping"],
        ),
        ToolDefinition(
            name="http_request",
            description="Make an HTTP request with full control over method, headers, and body.",
            func=_http_request,
            parameters={
                "url": {"type": "string", "description": "Request URL"},
                "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)"},
                "headers": {"type": "object", "description": "HTTP headers as key-value pairs"},
                "body": {"type": "string", "description": "Request body (for POST/PUT/PATCH)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds"},
            },
            category="web",
            tags=["http", "api", "request"],
        ),
        ToolDefinition(
            name="url_encode",
            description="URL-encode or decode a string.",
            func=_url_encode,
            parameters={
                "text": {"type": "string", "description": "Text to encode/decode"},
                "operation": {"type": "string", "description": "'encode' or 'decode'"},
            },
            category="web",
            tags=["url", "encoding", "utility"],
        ),
    ])


def _web_search(query: str, max_results: int = 10) -> Dict[str, Any]:
    """Search using DuckDuckGo instant answer API."""
    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()

        results = []

        # Abstract
        if data.get("AbstractText"):
            results.append({
                "title": data.get("AbstractSource", "DuckDuckGo"),
                "snippet": data["AbstractText"],
                "url": data.get("AbstractURL", ""),
                "type": "abstract",
            })

        # Related topics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                    "snippet": topic["Text"],
                    "url": topic.get("FirstURL", ""),
                    "type": "related",
                })

        # Also try to fetch from related topics
        for topic in data.get("Results", [])[:max_results]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append({
                    "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                    "snippet": topic["Text"],
                    "url": topic.get("FirstURL", ""),
                    "type": "result",
                })

        return {
            "query": query,
            "results_count": len(results),
            "results": results[:max_results],
        }
    except Exception as e:
        return {"error": f"Search failed: {str(e)}", "query": query, "results": []}


def _web_fetch(url: str, max_length: int = 10000, extract_text: bool = True) -> Dict[str, Any]:
    """Fetch and extract content from a URL."""
    import re

    try:
        headers = {
            "User-Agent": "Rampart-Agent/1.0 (Web Fetcher)",
            "Accept": "text/html,application/xhtml+xml,text/plain",
        }
        resp = requests.get(url, headers=headers, timeout=15, allow_redirects=True)
        resp.raise_for_status()

        content = resp.text

        if extract_text and "text/html" in resp.headers.get("content-type", ""):
            # Simple HTML text extraction
            content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<style[^>]*>.*?</style>", "", content, flags=re.DOTALL | re.IGNORECASE)
            content = re.sub(r"<[^>]+>", " ", content)
            content = re.sub(r"\s+", " ", content).strip()

        if len(content) > max_length:
            content = content[:max_length] + f"\n\n[... truncated, total: {len(content)} chars]"

        return {
            "url": url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("content-type", "unknown"),
            "content_length": len(resp.text),
            "content": content,
        }
    except requests.RequestException as e:
        return {"error": f"Fetch failed: {str(e)}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


def _http_request(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    body: Optional[str] = None,
    timeout: int = 30,
) -> Dict[str, Any]:
    """Make a raw HTTP request."""
    try:
        req_headers = {"User-Agent": "Rampart-Agent/1.0"}
        if headers:
            req_headers.update(headers)

        resp = requests.request(
            method=method.upper(),
            url=url,
            headers=req_headers,
            data=body,
            timeout=timeout,
            allow_redirects=True,
        )

        return {
            "url": url,
            "method": method.upper(),
            "status_code": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:5000],
            "elapsed_seconds": resp.elapsed.total_seconds(),
        }
    except Exception as e:
        return {"error": str(e), "url": url, "method": method.upper()}


def _url_encode(text: str, operation: str = "encode") -> Dict[str, Any]:
    """URL encode or decode."""
    if operation == "encode":
        encoded = urllib.parse.quote(text, safe="")
        return {"input": text, "output": encoded, "operation": "encode"}
    elif operation == "decode":
        decoded = urllib.parse.unquote(text)
        return {"input": text, "output": decoded, "operation": "decode"}
    else:
        return {"error": f"Unknown operation: {operation}. Use 'encode' or 'decode'."}
