"""Prompt Management — Versioned, templated prompts with variable interpolation.

Usage:
    from core.prompts import PromptManager
    pm = PromptManager()
    prompt = pm.render("ooda.observe", goal="analyze data", context="...")
"""

from core.prompts.manager import PromptManager

__all__ = ["PromptManager"]
