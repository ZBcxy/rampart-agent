"""Prompt Manager — Load, version, and render prompt templates."""

import json
from pathlib import Path
from string import Template
from typing import Any, Dict, Optional


class PromptManager:
    """Manages versioned prompt templates with variable interpolation.

    Templates are stored as JSON files with metadata (version, model, description).
    Supports hot-reloading and fallback to built-in defaults.
    """

    DEFAULT_TEMPLATES = {
        "ooda.observe": {
            "version": "1.0",
            "model": "any",
            "template": """You are in the OBSERVE phase of the OODA loop. Gather information.

User Goal: ${goal}
Previous Actions: ${previous_actions}
Current Context: ${context}
Available Tools: ${available_tools}

Analyze the situation. Output JSON:
{
    "understanding": "Your understanding",
    "knowledge_gaps": ["What you don't know"],
    "information_to_gather": ["What to collect"],
    "confidence": 0.0-1.0
}""",
        },
        "ooda.orient": {
            "version": "1.0",
            "model": "any",
            "template": """You are in the ORIENT phase. Synthesize observations into insights.

User Goal: ${goal}
Observations: ${observations}
Current Plan: ${plan}
Available Tools: ${available_tools}

Output JSON:
{
    "synthesis": "Synthesis of observations",
    "key_insights": ["Key insights"],
    "risks": ["Potential risks"],
    "revised_plan_needed": true/false,
    "confidence": 0.0-1.0
}""",
        },
        "ooda.decide": {
            "version": "1.0",
            "model": "any",
            "template": """You are in the DECIDE phase. Choose the best action.

User Goal: ${goal}
Synthesis: ${synthesis}
Key Insights: ${insights}
Risks: ${risks}
Available Tools: ${available_tools}

Output JSON:
{
    "reasoning": "Why this action",
    "actions": [
        {
            "type": "tool_call|think|ask_user|complete",
            "tool": "tool name",
            "arguments": {},
            "description": "What this does",
            "expected_outcome": "Expected result",
            "confidence": 0.0-1.0
        }
    ],
    "fallback": "Plan B"
}""",
        },
        "ooda.act": {
            "version": "1.0",
            "model": "any",
            "template": """You are in the ACT phase. Assess execution results.

Actions Taken: ${actions}
Results: ${results}

Output JSON:
{
    "assessment": "What happened",
    "success": true/false,
    "lessons_learned": ["What we learned"],
    "should_continue": true/false,
    "next_phase": "observe|orient|decide|act|complete"
}""",
        },
        "planner.generate": {
            "version": "1.0",
            "model": "any",
            "template": """Generate an execution plan from a user goal.

User Goal: ${goal}
Context: ${context}

Output a JSON plan tree:
{
    "goal_interpretation": "Restate goal clearly",
    "reasoning": "Why this approach",
    "plan_tree": {
        "type": "action",
        "content": "Step description",
        "confidence": 0.85,
        "children": [...]
    }
}

Node types: action, branch, parallel, human.
Limit plans to 3-8 top-level steps, max depth 4. Output ONLY valid JSON.""",
        },
        "planner.revise": {
            "version": "1.0",
            "model": "any",
            "template": """Revise an execution plan based on observations.

Original Plan: ${original_plan}
Failed Observations: ${observations}
Current Context: ${context}

Generate a revised JSON plan tree. Fix or replace failed steps.
Add retry/fallback where needed. Output ONLY valid JSON.""",
        },
        "system.base": {
            "version": "1.0",
            "model": "any",
            "template": """You are Polaris Agent, an autonomous multi-agent framework.

Capabilities:
- OODA loop planning and execution
- 26 built-in tools (file, web, code, data, system)
- Multi-agent coordination via blackboard
- MCP and A2A protocol support

Current tools: ${available_tools}
Autonomy level: ${autonomy_level}

Always respond with actionable plans. Be concise and precise.""",
        },
    }

    def __init__(self, templates_dir: Optional[str] = None):
        """
        Initialize the prompt manager.

        Args:
            templates_dir: Directory for custom template overrides
        """
        self.templates_dir = Path(templates_dir) if templates_dir else None
        self._templates: Dict[str, Dict] = dict(self.DEFAULT_TEMPLATES)
        self._load_custom_templates()

    def _load_custom_templates(self):
        """Load custom templates from disk, overriding defaults."""
        if not self.templates_dir or not self.templates_dir.exists():
            return

        for f in self.templates_dir.glob("*.json"):
            try:
                with open(f) as fp:
                    data = json.load(fp)
                    name = data.get("name", f.stem)
                    self._templates[name] = data
            except Exception:
                pass

    def render(self, name: str, **variables) -> str:
        """Render a prompt template with variables.

        Args:
            name: Template name (e.g., "ooda.observe")
            **variables: Variables to interpolate

        Returns:
            Rendered prompt string
        """
        tmpl = self._templates.get(name)
        if not tmpl:
            raise ValueError(f"Template not found: {name}. Available: {list(self._templates.keys())}")

        template_str = tmpl["template"]
        try:
            return Template(template_str).safe_substitute(**variables)
        except Exception:
            # Fallback: simple format
            for k, v in variables.items():
                template_str = template_str.replace(f"${{{k}}}", str(v))
            return template_str

    def get_metadata(self, name: str) -> Dict[str, Any]:
        """Get template metadata (version, model, etc.)."""
        tmpl = self._templates.get(name, {})
        return {
            "name": name,
            "version": tmpl.get("version", "unknown"),
            "model": tmpl.get("model", "any"),
        }

    def list_templates(self) -> Dict[str, str]:
        """List all available templates with versions."""
        return {name: t["version"] for name, t in self._templates.items()}

    def register(self, name: str, template: str, version: str = "1.0", model: str = "any"):
        """Register a custom template at runtime."""
        self._templates[name] = {
            "version": version,
            "model": model,
            "template": template,
        }

    def export_templates(self, directory: str):
        """Export all templates as JSON files."""
        out = Path(directory)
        out.mkdir(parents=True, exist_ok=True)
        for name, tmpl in self._templates.items():
            data = {"name": name, "version": tmpl["version"], "model": tmpl["model"], "template": tmpl["template"]}
            safe_name = name.replace(".", "_")
            with open(out / f"{safe_name}.json", "w") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
