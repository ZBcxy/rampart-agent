#!/usr/bin/env python3
"""Polaris Agent — Terminal Brand Identity

✦ Polaris (北极星智能体)
Brand mark: ✦ U+2726 four-pointed star
Tagline: Navigate Complexity with AI

Three display styles:
  default — Big Dipper → Polaris narrative (北斗七星叙事风)
  minimal — Bare symbol + version (极简符号风)
  box     — Starfield card (星空主题风)
"""

import os
import sys
import time
import shutil
import platform
import getpass

__version__ = "1.1.0"
__author__ = "Polaris Team"

# ── Terminal capability detection ──────────────────────────────────────────

_HAS_UNICODE = sys.stdout.encoding and "utf" in sys.stdout.encoding.lower()
_SUPPORTS_COLOR = (
    hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
) or os.environ.get("FORCE_COLOR", False) or os.environ.get("CLICOLOR_FORCE", False)
_NO_COLOR = os.environ.get("NO_COLOR", False)


def _c(code: str, text: str) -> str:
    """Apply ANSI color if terminal supports it."""
    if not _SUPPORTS_COLOR or _NO_COLOR:
        return text
    colors = {
        "cyan": "\033[36m",
        "blue": "\033[94m",
        "bold": "\033[1m",
        "yellow": "\033[93m",
        "green": "\033[92m",
        "white": "\033[97m",
        "dim": "\033[2m",
        "reset": "\033[0m",
        "magenta": "\033[95m",
    }
    return f"{colors.get(code, '')}{text}{colors['reset']}"


def _symbol(char: str, fallback: str = "*") -> str:
    """Return a Unicode symbol or safe fallback."""
    return char if _HAS_UNICODE else fallback


def _term_width() -> int:
    try:
        w = shutil.get_terminal_size().columns
        return w if w > 0 else 80
    except Exception:
        return 80


# ── Brand constants ────────────────────────────────────────────────────────

BRAND_MARK = _symbol("✦", "*")
STAR = _symbol("★", "*")
DOT = _symbol("·", ".")
DIAMOND = _symbol("◆", "<>")

VERSION = __version__
BUILD_DATE = "2026-06-18"
AUTHOR = "Polaris Team"
TAGLINE = "Navigate Complexity with AI"
SUBTITLE = "Autonomous Agent Framework"


# ── Logo generators ────────────────────────────────────────────────────────

def get_default_logo() -> str:
    """北斗七星叙事风 — Big Dipper pointing to Polaris.

    Dubhe and Merak (the Pointer stars) form a line that leads to Polaris,
    the North Star. This logo tells that story.
    """
    w = min(_term_width(), 80)

    # Big Dipper asterism → Polaris
    lines = [
        f"         {_c('dim', DOT + '  ' + DOT + '  ' + DOT)}           {_c('dim', 'Dubhe · Merak · Phecda')}",
        f"           {_c('dim', DOT + '  ' + DOT)}                 {_c('dim', 'Megrez · Alioth')}",
        f"            {_c('dim', DOT)}                    {_c('dim', 'Mizar')}",
        f"             {_c('dim', DOT)}                   {_c('dim', 'Alkaid')}",
        f"              {_c('yellow', _c('bold', BRAND_MARK))}                  {_c('cyan', _c('bold', 'Polaris ✦'))}",
        "",
        f"     {_c('cyan', '═══')} {_c('bold', _c('white', 'P O L A R I S'))} {_c('cyan', '═' * (w - 30))}",
        f"        {_c('blue', TAGLINE)}",
        f"     {_c('dim', f'v{VERSION}  |  {AUTHOR}')}",
    ]
    return "\n".join(lines)


def get_minimal_logo() -> str:
    """极简符号风 — single line brand mark, similar to Claude Code's ⦿."""
    return (
        f"\n{_c('yellow', _c('bold', BRAND_MARK))} "
        f"{_c('bold', _c('white', 'POLARIS'))} "
        f"{_c('dim', f'— {TAGLINE}')}"
        f"\n{_c('dim', f'v{VERSION}')}\n"
    )


def get_box_logo() -> str:
    """星空主题风 — framed card with starfield feel."""
    w = min(_term_width(), 72)
    inner = w - 2

    def row(left: str, center: str, right: str = "") -> str:
        pad = inner - len(_strip_ansi(center))
        return f"{_c('cyan', left)}{center}{' ' * max(0, pad)}{_c('cyan', right)}"

    lines = [
        _c("cyan", "┌" + "─" * inner + "┐"),
        row("│", f"   {_c('dim', DOT)}  {_c('dim', DOT)}  {BRAND_MARK}  {_c('dim', DOT)}  {_c('dim', DOT)}  {_c('dim', DOT)}", "│"),
        row("│", "", "│"),
        row("│", f"     {_c('bold', _c('white', 'P O L A R I S   A G E N T'))}", "│"),
        row("│", f"      {_c('blue', TAGLINE)}", "│"),
        row("│", "", "│"),
        row("│", f"   {_c('dim', f'v{VERSION}  |  {AUTHOR}  |  {platform.python_version()}')}", "│"),
        _c("cyan", "└" + "─" * inner + "┘"),
    ]
    return "\n".join(lines)


def _strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


# ── Animated loading ───────────────────────────────────────────────────────

def _animate_starfield(frames: int = 8, duration: float = 0.6) -> None:
    """Brief starfield twinkle before logo appears."""
    if not _SUPPORTS_COLOR:
        return
    stars = [DOT, "·", "˙", "⋅", "∙"]
    interval = duration / frames
    for i in range(frames):
        s = stars[i % len(stars)]
        print(f"\r  {_c('yellow', s)}", end="", flush=True)
        time.sleep(interval)
    print("\r" + " " * 8 + "\r", end="")


# ── PolarisLogo class ──────────────────────────────────────────────────────

class PolarisLogo:
    """Display Polaris Agent brand identity in the terminal.

    Usage:
        logo = PolarisLogo(style="default", animate=True)
        logo.display()

        logo.display_version()
        logo.display_info_panel(model="gpt-4o")
    """

    def __init__(
        self,
        style: str = "default",
        animate: bool = False,
        show_info: bool = True,
        model: str = "",
        status: str = "Ready",
        mode: str = "Interactive",
    ):
        self.style = style
        self.animate = animate and _SUPPORTS_COLOR and not _NO_COLOR
        self.show_info = show_info
        self.model = model
        self.status = status
        self.mode = mode

    def display(self) -> None:
        """Show full splash screen: logo + optional info panel."""
        # Clear screen for clean presentation
        if self.show_info:
            os.system("cls" if os.name == "nt" else "clear")

        if self.animate:
            _animate_starfield()

        if self.style == "minimal":
            print(get_minimal_logo())
        elif self.style == "box":
            print(get_box_logo())
        else:
            print(get_default_logo())

        if self.show_info:
            self.display_info_panel()

    def display_version(self) -> None:
        """Show version card."""
        w = min(_term_width(), 60)
        print(f"""
{_c('cyan', '┌' + '─' * (w - 2) + '┐')}
{_c('cyan', '│')}  {_c('bold', f'{BRAND_MARK} Polaris Agent')}{' ' * (w - 23)}{_c('cyan', '│')}
{_c('cyan', '├' + '─' * (w - 2) + '┤')}
{_c('cyan', '│')}  Version:    {VERSION:<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Build Date: {BUILD_DATE:<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Author:     {AUTHOR:<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Python:     {platform.python_version():<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Platform:   {platform.platform()[:29]:<30}{_c('cyan', '│')}
{_c('cyan', '└' + '─' * (w - 2) + '┘')}
""")

    def display_welcome(self) -> None:
        """Show welcome banner."""
        print(f"""
{_c('green', _c('bold', '═' * min(_term_width(), 80)))}
  {_c('bold', f'{BRAND_MARK} Polaris Agent — {TAGLINE}')}
  {_c('dim', f'Type "help" for usage, "exit" to quit.')}
{_c('green', _c('bold', '═' * min(_term_width(), 80)))}
""")

    def display_info_panel(self) -> None:
        """Show compact runtime info panel."""
        user = getpass.getuser()
        workspace = os.path.basename(os.getcwd())
        model = self.model or os.environ.get("LLM_MODEL", "not configured")
        w = min(_term_width(), 70)
        inner = w - 2

        def row(label: str, value: str, label2: str = "", value2: str = "") -> str:
            left = f"  [{label}]  {value}"
            if label2:
                left += f"    [{label2}]  {value2}"
            pad = inner - len(_strip_ansi(left))
            return f"{_c('cyan', '│')}{left}{' ' * max(0, pad)}{_c('cyan', '│')}"

        print(f"""
{_c('cyan', '┌' + '─' * inner + '┐')}
{row('Model', model[:28], 'Status', self.status)}
{row('User', user[:28], 'Mode', self.mode)}
{row('Workspace', workspace[:26], 'Version', VERSION)}
{_c('cyan', '└' + '─' * inner + '┘')}
""")


# ── Convenience functions (backwards-compatible) ───────────────────────────

def display_splash(animate: bool = False, style: str = "default") -> None:
    PolarisLogo(style=style, animate=animate, show_info=True).display()


def display_version_info() -> None:
    PolarisLogo().display_version()


def display_welcome() -> None:
    PolarisLogo().display_welcome()


def display_info_panel(model: str = "", status: str = "Ready", mode: str = "Interactive") -> None:
    PolarisLogo(model=model, status=status, mode=mode).display_info_panel()


# ── CLI entry point ────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="polaris-logo",
        description=f"{BRAND_MARK} Polaris Agent — Brand Identity Display",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                        Show full logo with info panel
  %(prog)s --style minimal         Minimal single-line logo
  %(prog)s --style box             Framed card logo
  %(prog)s --no-animate            Skip animation
  %(prog)s --version               Version card only
  %(prog)s --welcome               Welcome banner only
        """,
    )

    parser.add_argument("--style", "-s", choices=["default", "minimal", "box"], default="default")
    parser.add_argument("--animate", "-a", action="store_true", default=True)
    parser.add_argument("--no-animate", action="store_true")
    parser.add_argument("--version", "-v", action="store_true")
    parser.add_argument("--info", "-i", action="store_true")
    parser.add_argument("--welcome", "-w", action="store_true")
    args = parser.parse_args()

    if args.no_animate:
        args.animate = False

    logo = PolarisLogo(style=args.style, animate=args.animate, show_info=True)

    if args.version:
        logo.display_version()
    elif args.welcome:
        logo.display_welcome()
    elif args.info:
        logo.display_info_panel()
    else:
        logo.display()


if __name__ == "__main__":
    main()
