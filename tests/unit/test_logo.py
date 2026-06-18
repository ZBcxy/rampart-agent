"""Unit tests for Polaris Logo module."""

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
    # Force color support for testing (but disable actual ANSI)
    mod._SUPPORTS_COLOR = True
    return mod


class TestLogoGeneration:
    """Test that all logo styles generate non-empty, valid output."""

    def test_default_logo(self, logo_mod):
        logo = logo_mod.get_default_logo()
        assert logo is not None
        assert len(logo) > 0
        assert "POLARIS" in logo_mod._strip_ansi(logo)
        assert "Navigate Complexity with AI" in logo_mod._strip_ansi(logo)

    def test_minimal_logo(self, logo_mod):
        logo = logo_mod.get_minimal_logo()
        assert logo is not None
        assert len(logo) > 0
        plain = logo_mod._strip_ansi(logo)
        assert "POLARIS" in plain
        assert "Navigate Complexity with AI" in plain

    def test_box_logo(self, logo_mod):
        logo = logo_mod.get_box_logo()
        assert logo is not None
        assert len(logo) > 0
        plain = logo_mod._strip_ansi(logo)
        assert "POLARIS" in plain
        assert "Navigate Complexity with AI" in plain

    def test_logo_styles_are_different(self, logo_mod):
        default = logo_mod.get_default_logo()
        minimal = logo_mod.get_minimal_logo()
        box = logo_mod.get_box_logo()

        # Strip ANSI for comparison
        assert logo_mod._strip_ansi(default) != logo_mod._strip_ansi(minimal)
        assert logo_mod._strip_ansi(default) != logo_mod._strip_ansi(box)
        assert logo_mod._strip_ansi(minimal) != logo_mod._strip_ansi(box)

    def test_version_in_logo(self, logo_mod):
        for getter in [logo_mod.get_default_logo, logo_mod.get_minimal_logo, logo_mod.get_box_logo]:
            plain = logo_mod._strip_ansi(getter())
            assert logo_mod.VERSION in plain, f"Version missing in {getter.__name__}"


class TestPolarisLogoClass:
    """Test the PolarisLogo display class."""

    def test_create_default(self, logo_mod):
        pl = logo_mod.PolarisLogo()
        assert pl.style == "default"
        assert pl.animate is False  # not a tty in tests

    def test_create_minimal(self, logo_mod):
        pl = logo_mod.PolarisLogo(style="minimal")
        assert pl.style == "minimal"

    def test_create_box(self, logo_mod):
        pl = logo_mod.PolarisLogo(style="box")
        assert pl.style == "box"

    def test_show_info_control(self, logo_mod):
        pl = logo_mod.PolarisLogo(show_info=False)
        assert pl.show_info is False

    def test_display_version(self, logo_mod, capsys):
        pl = logo_mod.PolarisLogo()
        pl.display_version()
        captured = capsys.readouterr()
        plain = logo_mod._strip_ansi(captured.out)
        assert logo_mod.VERSION in plain
        assert "Polaris Agent" in plain

    def test_display_welcome(self, logo_mod, capsys):
        pl = logo_mod.PolarisLogo()
        pl.display_welcome()
        captured = capsys.readouterr()
        plain = logo_mod._strip_ansi(captured.out)
        assert "Polaris Agent" in plain or "help" in plain.lower()

    def test_display_info_panel(self, logo_mod, capsys):
        pl = logo_mod.PolarisLogo(model="test-model", status="Running")
        pl.display_info_panel()
        captured = capsys.readouterr()
        plain = logo_mod._strip_ansi(captured.out)
        assert "test-model" in plain
        assert "Running" in plain


class TestConstants:
    """Test brand constants."""

    def test_brand_mark(self, logo_mod):
        # BRAND_MARK should be a star character
        assert len(logo_mod.BRAND_MARK) > 0

    def test_version_string(self, logo_mod):
        assert logo_mod.VERSION is not None
        assert "." in logo_mod.VERSION

    def test_tagline(self, logo_mod):
        assert logo_mod.TAGLINE == "Navigate Complexity with AI"

    def test_author(self, logo_mod):
        assert logo_mod.AUTHOR is not None


class TestConvenienceFunctions:
    """Test backwards-compatible convenience functions."""

    def test_display_version_info(self, logo_mod, capsys):
        logo_mod.display_version_info()
        captured = capsys.readouterr()
        plain = logo_mod._strip_ansi(captured.out)
        assert logo_mod.VERSION in plain

    def test_display_welcome_func(self, logo_mod, capsys):
        logo_mod.display_welcome()
        captured = capsys.readouterr()
        assert len(captured.out) > 0

    def test_display_info_panel_func(self, logo_mod, capsys):
        logo_mod.display_info_panel(model="test-model")
        captured = capsys.readouterr()
        plain = logo_mod._strip_ansi(captured.out)
        assert "test-model" in plain


class TestTerminalHelpers:
    """Test terminal utility functions."""

    def test_terminal_width(self, logo_mod):
        w = logo_mod._term_width()
        assert w > 0
        assert isinstance(w, int)

    def test_strip_ansi(self, logo_mod):
        colored = "\033[36mHello\033[0m"
        assert logo_mod._strip_ansi(colored) == "Hello"

    def test_strip_ansi_multiple(self, logo_mod):
        colored = "\033[1m\033[93m✦\033[0m\033[0m"
        assert logo_mod._strip_ansi(colored) == "✦"
