"""Data Processing Tools - Transform, analyze, and manipulate data."""

import csv
import io
from typing import Any, Dict

from tools.registry import ToolDefinition, ToolRegistry


def register_data_tools(registry: ToolRegistry):
    """Register all data processing tools."""
    registry.register_many([
        ToolDefinition(
            name="text_process",
            description="Process text: count words, extract entities, summarize, translate.",
            func=_text_process,
            parameters={
                "text": {"type": "string", "description": "Text to process"},
                "operation": {"type": "string", "description": "Operation: 'stats', 'summarize', 'keywords', 'sentiment'"},
            },
            category="data",
            tags=["text", "nlp", "analysis"],
        ),
        ToolDefinition(
            name="csv_parse",
            description="Parse CSV data and return as structured JSON.",
            func=_csv_parse,
            parameters={
                "csv_content": {"type": "string", "description": "Raw CSV content"},
                "delimiter": {"type": "string", "description": "CSV delimiter (default: ',')"},
                "has_header": {"type": "boolean", "description": "First row is header (default: true)"},
                "max_rows": {"type": "integer", "description": "Maximum rows to return"},
            },
            category="data",
            tags=["csv", "parse", "tabular"],
        ),
        ToolDefinition(
            name="calc",
            description="Perform mathematical calculations. Supports expressions with +,-,*,/,**,%,sqrt,sin,cos,log.",
            func=_calc,
            parameters={
                "expression": {"type": "string", "description": "Math expression to evaluate"},
            },
            category="data",
            tags=["math", "calculation", "compute"],
        ),
        ToolDefinition(
            name="data_transform",
            description="Transform data: filter, map, sort, group, aggregate on JSON arrays.",
            func=_data_transform,
            parameters={
                "data": {"type": "string", "description": "JSON array string to transform"},
                "operation": {"type": "string", "description": "Operation: 'sort', 'filter', 'group', 'stats'"},
                "params": {"type": "object", "description": "Operation parameters (key, condition, etc.)"},
            },
            category="data",
            tags=["transform", "json", "analysis"],
        ),
    ])


def _text_process(text: str, operation: str = "stats") -> Dict[str, Any]:
    """Process text with various operations."""
    import re

    if operation == "stats":
        words = text.split()
        lines = text.split("\n")
        chars = len(text)
        char_no_space = len(text.replace(" ", "").replace("\n", "").replace("\t", ""))

        return {
            "word_count": len(words),
            "line_count": len(lines),
            "char_count": chars,
            "char_no_space": char_no_space,
            "avg_word_length": sum(len(w) for w in words) / max(len(words), 1),
            "avg_line_length": sum(len(l) for l in lines) / max(len(lines), 1),
        }

    elif operation == "keywords":
        # Simple keyword extraction by frequency
        words = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
        from collections import Counter
        counter = Counter(words)
        # Remove common stopwords
        stopwords = {"the", "and", "for", "that", "this", "with", "from", "have", "are", "was", "not", "but", "you", "all", "can", "has", "had", "her", "his", "its", "our", "out", "some", "than", "then", "them", "these", "those", "when", "what", "where", "which", "who", "will", "would", "your"}
        keywords = [(word, count) for word, count in counter.most_common(50) if word not in stopwords]
        return {"keywords": keywords[:20]}

    elif operation == "summarize":
        # Simple extractive summary: take first and most representative sentences
        import re
        sentences = re.split(r"[.!?]+", text)
        sentences = [s.strip() for s in sentences if len(s.strip()) > 20]
        # First sentence + sentences with key terms
        summary_sentences = sentences[:1] if sentences else []
        if len(sentences) > 2:
            summary_sentences.append(sentences[len(sentences) // 2])
        if len(sentences) > 1:
            summary_sentences.append(sentences[-1])
        return {
            "summary": ". ".join(summary_sentences) + ".",
            "original_sentences": len(sentences),
            "summary_sentences": len(summary_sentences),
            "compression_ratio": len(summary_sentences) / max(len(sentences), 1),
        }

    elif operation == "sentiment":
        # Basic sentiment analysis
        positive = {"good", "great", "excellent", "amazing", "wonderful", "fantastic", "love", "happy", "best", "awesome", "beautiful", "perfect", "nice", "positive", "outstanding", "brilliant", "superb", "terrific"}
        negative = {"bad", "terrible", "awful", "horrible", "worst", "hate", "ugly", "poor", "negative", "failure", "fail", "sad", "angry", "disappointing", "wrong", "broken", "useless", "pathetic"}

        words = text.lower().split()
        pos_count = sum(1 for w in words if w in positive)
        neg_count = sum(1 for w in words if w in negative)

        if pos_count > neg_count:
            sentiment = "positive"
            score = min(1.0, pos_count / max(len(words), 1) * 10)
        elif neg_count > pos_count:
            sentiment = "negative"
            score = min(1.0, neg_count / max(len(words), 1) * 10)
        else:
            sentiment = "neutral"
            score = 0.0

        return {
            "sentiment": sentiment,
            "score": score,
            "positive_words": pos_count,
            "negative_words": neg_count,
        }

    return {"error": f"Unknown operation: {operation}"}


def _csv_parse(csv_content: str, delimiter: str = ",", has_header: bool = True, max_rows: int = 1000) -> Dict[str, Any]:
    """Parse CSV content."""
    reader = csv.reader(io.StringIO(csv_content), delimiter=delimiter)

    headers = None
    if has_header:
        try:
            headers = next(reader)
        except StopIteration:
            return {"error": "Empty CSV"}

    rows = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        if headers:
            rows.append({headers[j]: row[j] if j < len(row) else "" for j in range(len(headers))})
        else:
            rows.append(row)

    return {
        "headers": headers,
        "row_count": len(rows),
        "column_count": len(headers) if headers else (len(rows[0]) if rows else 0),
        "rows": rows,
    }


def _calc(expression: str) -> Dict[str, Any]:
    """Evaluate a mathematical expression."""
    import math
    import re

    # Sanitize and prepare
    allowed_names = {
        "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos,
        "tan": math.tan, "log": math.log, "log10": math.log10,
        "log2": math.log2, "exp": math.exp, "abs": abs,
        "pi": math.pi, "e": math.e, "ceil": math.ceil,
        "floor": math.floor, "round": round,
        "pow": pow, "sum": sum, "min": min, "max": max,
    }

    # Check for unsafe patterns
    if re.search(r"[a-zA-Z_][a-zA-Z0-9_]*\s*\(", expression):
        # Only allow specific function calls
        func_pattern = r"([a-zA-Z_][a-zA-Z0-9_]*)\s*\("
        for match in re.finditer(func_pattern, expression):
            func_name = match.group(1)
            if func_name not in allowed_names:
                return {"error": f"Function not allowed: {func_name}"}

    try:
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return {"expression": expression, "result": result}
    except Exception as e:
        return {"error": str(e), "expression": expression}


def _data_transform(data: str, operation: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
    """Transform JSON array data."""
    import json

    try:
        items = json.loads(data)
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}

    if not isinstance(items, list):
        return {"error": "Data must be a JSON array"}

    params = params or {}
    key = params.get("key", "")

    if operation == "sort":
        reverse = params.get("reverse", False)
        if key:
            items = sorted(items, key=lambda x: x.get(key, 0) if isinstance(x, dict) else x, reverse=reverse)
        else:
            items = sorted(items, reverse=reverse)
        return {"count": len(items), "result": items[:500]}

    elif operation == "filter":
        condition = params.get("condition", "")
        if key and condition:
            # Simple key-value or key-condition filtering
            try:
                if condition.startswith(">"):
                    threshold = float(condition[1:])
                    items = [x for x in items if isinstance(x, dict) and x.get(key, 0) > threshold]
                elif condition.startswith("<"):
                    threshold = float(condition[1:])
                    items = [x for x in items if isinstance(x, dict) and x.get(key, 0) < threshold]
                elif condition.startswith("="):
                    val = condition[1:]
                    items = [x for x in items if isinstance(x, dict) and str(x.get(key, "")) == val]
                elif condition.startswith("contains"):
                    val = condition[8:].strip()
                    items = [x for x in items if isinstance(x, dict) and val.lower() in str(x.get(key, "")).lower()]
            except (ValueError, TypeError):
                pass
        return {"count": len(items), "result": items[:500]}

    elif operation == "group":
        if key:
            groups = {}
            for item in items:
                if isinstance(item, dict):
                    group_key = str(item.get(key, "unknown"))
                    groups.setdefault(group_key, []).append(item)
            return {"groups": {k: len(v) for k, v in groups.items()}, "group_count": len(groups)}

    elif operation == "stats":
        if key:
            values = [x.get(key, 0) for x in items if isinstance(x, dict)]
        else:
            values = [x for x in items if isinstance(x, (int, float))]

        if not values:
            return {"error": "No numeric values found"}

        return {
            "count": len(values),
            "sum": sum(values),
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / len(values),
            "median": sorted(values)[len(values) // 2],
        }

    return {"error": f"Unknown operation: {operation}"}
