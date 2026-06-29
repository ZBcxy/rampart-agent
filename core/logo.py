#!/usr/bin/env python3
"""Rampart Agent — Terminal Brand Identity

⬡ Rampart (壁垒智能体)
Brand mark: ⬡ U+2B21 hexagon
Tagline: Fortify Your Intelligence
"""

import os
import sys
import shutil
import platform
import getpass

__version__ = "1.1.0"
__author__ = "Rampart Team"

# —— Terminal capability detection ————————————————————————————————————————————

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
    return char if _HAS_UNICODE else fallback


def _term_width() -> int:
    try:
        w = shutil.get_terminal_size().columns
        return w if w > 0 else 80
    except Exception:
        return 80


def _strip_ansi(text: str) -> str:
    import re
    return re.sub(r"\033\[[0-9;]*m", "", text)


# —— Brand constants ————————————————————————————————————————————————————————————

BRAND_MARK = _symbol("⬡", "[]")
VERSION = __version__
BUILD_DATE = "2026-06-29"
AUTHOR = "Rampart Team"
TAGLINE = "Fortify Your Intelligence"


# —— Logo ——————————————————————————————————————————————————————————————————————

def get_logo() -> str:
    w = min(_term_width(), 80)
    lines = [
        f"        {_c('dim', '▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄')}",
        f"        {_c('dim', '█' + ' ' * 25 + '█')}",
        f"        {_c('dim', '█')}    {_c('yellow', _c('bold', '⬡'))}     {_c('dim', '█')}        {_c('cyan', _c('bold', 'Rampart'))}",
        f"        {_c('dim', '█▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄█')}",
        f"        {_c('dim', '▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓')}",
        "",
        f"     {_c('cyan', '╭──╮')} {_c('bold', _c('white', 'R A M P A R T'))} {_c('cyan', '╰' + '─' * (w - 27))}",
        f"        {_c('blue', TAGLINE)}",
        f"     {_c('dim', f'v{VERSION}  |  {AUTHOR}')}",
    ]
    return "\n".join(lines)


# —— Info panel ————————————————————————————————————————————————————————————————

def display_info_panel(model: str = "", status: str = "Ready", mode: str = "Interactive") -> None:
    user = getpass.getuser()
    workspace = os.path.basename(os.getcwd())
    model = model or os.environ.get("LLM_MODEL", "not configured")
    w = min(_term_width(), 70)
    inner = w - 2

    def row(label: str, value: str, label2: str = "", value2: str = "") -> str:
        left = f"  [{label}]  {value}"
        if label2:
            left += f"    [{label2}]  {value2}"
        pad = inner - len(_strip_ansi(left))
        return f"{_c('cyan', '│')}{left}{' ' * max(0, pad)}{_c('cyan', '│')}"

    print(f"""
{_c('cyan', '╭' + '─' * inner + '╮')}
{row('Model', model[:28], 'Status', status)}
{row('User', user[:28], 'Mode', mode)}
{row('Workspace', workspace[:26], 'Version', VERSION)}
{_c('cyan', '╰' + '─' * inner + '╯')}
""")


def display_version() -> None:
    w = min(_term_width(), 60)
    print(f"""
{_c('cyan', '╭' + '─' * (w - 2) + '╮')}
{_c('cyan', '│')}  {_c('bold', f'{BRAND_MARK} Rampart Agent')}{' ' * (w - 23)}{_c('cyan', '│')}
{_c('cyan', '├' + '─' * (w - 2) + '┤')}
{_c('cyan', '│')}  Version:    {VERSION:<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Build Date: {BUILD_DATE:<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Author:     {AUTHOR:<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Python:     {platform.python_version():<30}{_c('cyan', '│')}
{_c('cyan', '│')}  Platform:   {platform.platform()[:29]:<30}{_c('cyan', '│')}
{_c('cyan', '╰' + '─' * (w - 2) + '╯')}
""")


def display_welcome() -> None:
    print(f"""
{_c('green', _c('bold', '═' * min(_term_width(), 80)))}
  {_c('bold', f'{BRAND_MARK} Rampart Agent — {TAGLINE}')}
  {_c('dim', f'Type "help" for usage, "exit" to quit.')}
{_c('green', _c('bold', '═' * min(_term_width(), 80)))}
""")


def display_splash(animate: bool = False) -> None:
    os.system("cls" if os.name == "nt" else "clear")
    print(get_logo())


# —— CLI entry point ————————————————————————————————————————————————————————————

def main():
    import argparse

    parser = argparse.ArgumentParser(
        prog="rampart-logo",
        description=f"{BRAND_MARK} Rampart Agent — Brand Identity Display",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     Show full logo with info panel
  %(prog)s --version           Version card only
  %(prog)s --welcome           Welcome banner only
        """,
    )
    parser.add_argument("--version", "-v", action="store_true")
    parser.add_argument("--welcome", "-w", action="store_true")
    args = parser.parse_args()

    if args.version:
        display_version()
    elif args.welcome:
        display_welcome()
    else:
        display_splash()
        display_info_panel()


if __name__ == "__main__":
    main()
