"""Unit tests for Rampart Logo module."""

import importlib.util as iu
from pathlib import Path

import pytest


@pytest.fixture
def logo_mod():
    """Import logo module directly, bypassing core.__init__."""
    src = Path(__file__).parent.parent.parent / "core" / "logo.py"
    spec = iu.spec_from_file_location("_logo_test", str(src))
    mod = iu.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestLogoGeneration:
    """Test the single unified logo output."""

    def test_logo_contains_brand(self, logo_mod):
        logo = logo_mod.get_logo()
        assert "R A M P A R T" in logo

    def test_logo_contains_version(self, logo_mod):
        logo = logo_mod.get_logo()
        assert logo_mod.VERSION in logo

    def test_logo_contains_author(self, logo_mod):
        logo = logo_mod.get_logo()
        assert logo_mod.AUTHOR in logo

    def test_logo_contains_tagline(self, logo_mod):
        logo = logo_mod.get_logo()
        assert "Fortify Your Intelligence" in logo

    def test_logo_contains_brand_mark(self, logo_mod):
        logo = logo_mod.get_logo()
        assert logo_mod.BRAND_MARK in logo


class TestRampartDisplayFunctions:
    """Test display / info panel functions."""

    def test_display_version(self, logo_mod, capsys):
        logo_mod.display_version()
        captured = capsys.readouterr().out
        assert "Rampart Agent" in captured
        assert logo_mod.VERSION in captured

    def test_display_welcome(self, logo_mod, capsys):
        logo_mod.display_welcome()
        captured = capsys.readouterr().out
        assert "Rampart Agent" in captured

    def test_display_info_panel(self, logo_mod, capsys):
        logo_mod.display_info_panel(model="test-model", status="Running")
        captured = capsys.readouterr().out
        assert "test-model" in captured
        assert "Running" in captured


class TestConstants:
    """Test brand constants."""

    def test_brand_mark(self, logo_mod):
        assert logo_mod.BRAND_MARK in ("⬡", "[]")

    def test_version_string(self, logo_mod):
        assert "." in logo_mod.VERSION

    def test_tagline(self, logo_mod):
        assert logo_mod.TAGLINE == "Fortify Your Intelligence"

    def test_author(self, logo_mod):
        assert "Rampart" in logo_mod.AUTHOR


class TestTerminalHelpers:
    """Test utility functions."""

    def test_terminal_width(self, logo_mod):
        w = logo_mod._term_width()
        assert isinstance(w, int)
        assert w > 0

    def test_strip_ansi(self, logo_mod):
        result = logo_mod._strip_ansi("\033[36mHello\033[0m")
        assert result == "Hello"

    def test_strip_ansi_multiple(self, logo_mod):
        result = logo_mod._strip_ansi("\033[1m\033[94mBold Blue\033[0m")
        assert result == "Bold Blue"
