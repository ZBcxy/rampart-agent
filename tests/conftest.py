"""Shared pytest fixtures for the Polaris Agent test suite.

To use these fixtures in test files, they are auto-discovered by pytest.
No explicit import needed — the function name as a parameter is sufficient.
"""

import pytest


# ── Core module fixtures ────────────────────────────────────────────────────


@pytest.fixture
def tool_registry():
    """A ToolRegistry with all 26 tools registered (register_all)."""
    from tools.registry import ToolRegistry

    r = ToolRegistry()
    r.register_all()
    return r


@pytest.fixture
def agent_config():
    """A minimal AgentConfig suitable for unit tests (no real LLM calls)."""
    from core.agent import AgentConfig

    return AgentConfig(
        model="test-model",
        provider="test",
        api_key="test-key",
        max_steps=5,
        max_retries=1,
    )


@pytest.fixture
def working_memory():
    """A fresh WorkingMemory instance."""
    from core.memory import WorkingMemory

    return WorkingMemory()


@pytest.fixture
def semantic_memory():
    """A fresh EmbeddingSemanticMemory instance."""
    from core.memory import EmbeddingSemanticMemory

    return EmbeddingSemanticMemory()


# ── Alignment fixtures ─────────────────────────────────────────────────────


@pytest.fixture
def align_guard():
    """AlignGuard with all default rules enabled."""
    from core.align import AlignGuard

    return AlignGuard(enabled=True)


@pytest.fixture
def policy_engine():
    """PolicyEngine at L2 supervised autonomy."""
    from core.align import AutonomyLevel, PolicyEngine

    return PolicyEngine(autonomy_level=AutonomyLevel.L2_SUPERVISED)


# ── Multi-agent fixtures ───────────────────────────────────────────────────


@pytest.fixture
def blackboard():
    """A fresh Blackboard for multi-agent tests."""
    from multi_agent.blackboard import Blackboard

    return Blackboard(name="test")


@pytest.fixture
def coordinator(blackboard):
    """A Coordinator attached to a fresh Blackboard."""
    from multi_agent.coordinator import Coordinator

    return Coordinator(blackboard=blackboard)


# ── Gateway fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def app():
    """Create a FastAPI app instance for gateway endpoint tests."""
    import os

    # Ensure no real API keys leak during tests
    os.environ.setdefault("LLM_MODEL", "test")
    os.environ.setdefault("LLM_PROVIDER", "test")
    os.environ.setdefault("POLARIS_MAX_STEPS", "1")

    from gateway.main import create_app

    return create_app()


@pytest.fixture
def client(app):
    """FastAPI TestClient for gateway endpoint smoke tests."""
    from fastapi.testclient import TestClient

    return TestClient(app)


# ── Performance / harness fixtures ──────────────────────────────────────────


@pytest.fixture
def performance_monitor():
    """A fresh PerformanceMonitor."""
    from core.performance import PerformanceMonitor

    return PerformanceMonitor()


@pytest.fixture
def failure_classifier():
    """A fresh FailureClassifier."""
    from core.failure_attribution import FailureClassifier

    return FailureClassifier()


@pytest.fixture
def entropy_auditor():
    """A fresh EntropyAuditor."""
    from core.entropy_audit import EntropyAuditor

    return EntropyAuditor()


@pytest.fixture
def context_selector():
    """A fresh ContextSelector."""
    from core.context_selector import ContextSelector

    return ContextSelector()


@pytest.fixture
def intervention_log():
    """A fresh InterventionLog."""
    from core.intervention import InterventionLog

    return InterventionLog()
