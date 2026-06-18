#!/usr/bin/env bash
# ✦ Polaris Agent — npm postinstall script
# Bootstraps the Python polaris-agent package after npm install.
set -e

cat << 'BANNER'

╭──────────────────────────────────────╮
│  ✦ Polaris Agent — npm install       │
│  Navigate Complexity with AI         │
╰──────────────────────────────────────╯

BANNER

# ── Color helpers ─────────────────────────────────────────────────────────

if [ -t 1 ]; then
    GREEN='\033[32m'; YELLOW='\033[33m'; CYAN='\033[36m'; RED='\033[31m'; DIM='\033[2m'; RESET='\033[0m'
else
    GREEN=''; YELLOW=''; CYAN=''; RED=''; DIM=''; RESET=''
fi

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}!${RESET} $1"; }
err()  { echo -e "  ${RED}✗${RESET} $1"; }
info() { echo -e "  ${CYAN}ℹ${RESET} $1"; }

# ── Check Python ──────────────────────────────────────────────────────────

echo ""
echo "▸ Python"

PYTHON=""
for py in python3.12 python3.11 python3; do
    if command -v "$py" &>/dev/null; then
        VER=$("$py" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "0")
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -ge 3 ] && [ "$MINOR" -ge 11 ] 2>/dev/null; then
            PYTHON="$py"
            ok "Python $VER ($py)"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python 3.11+ is required but not found."
    echo ""
    echo "  Install Python 3.11+ then run:"
    echo "    pip install polaris-agent"
    echo ""
    echo "  Or use Docker:"
    echo "    docker run -p 8000:8000 ghcr.io/zbcxy/polaris-agent:latest"
    echo ""
    exit 1
fi

# ── Check pip ─────────────────────────────────────────────────────────────

echo ""
echo "▸ pip"

if ! "$PYTHON" -m pip --version &>/dev/null; then
    warn "pip not found. Installing..."
    "$PYTHON" -m ensurepip --upgrade 2>/dev/null || true
fi

if "$PYTHON" -m pip --version &>/dev/null; then
    ok "pip ready"
else
    err "Failed to install pip."
    exit 1
fi

# ── Install polaris-agent ─────────────────────────────────────────────────

echo ""
echo "▸ Polaris Agent"

# Check if already installed
if "$PYTHON" -c "import cli.polaris_cli" 2>/dev/null; then
    INSTALLED_VER=$("$PYTHON" -c "from core.logo import __version__; print(__version__)" 2>/dev/null || echo "?")
    ok "Already installed (v$INSTALLED_VER)"
else
    info "Installing polaris-agent via pip..."
    if "$PYTHON" -m pip install polaris-agent -q 2>/dev/null; then
        ok "Installed successfully"
    else
        # Fallback: try to find the package locally
        LOCAL_DIR="$(dirname "$(dirname "$(dirname "$(readlink -f "$0")")")")"
        if [ -f "$LOCAL_DIR/pyproject.toml" ]; then
            info "Installing from local source: $LOCAL_DIR"
            "$PYTHON" -m pip install -e "$LOCAL_DIR" -q 2>/dev/null && ok "Installed (local)" || warn "Local install had issues — may need --user flag"
        else
            warn "Could not install from PyPI."
            info "The npm package is a wrapper. Install the Python package manually:"
            info "  pip install polaris-agent"
            info "  curl -sSL https://raw.githubusercontent.com/ZBcxy/polaris-agent/main/install.py | python3"
        fi
    fi
fi

# ── Verify CLI ────────────────────────────────────────────────────────────

echo ""
echo "▸ CLI"

if command -v polaris &>/dev/null; then
    POLARIS_PATH=$(command -v polaris)
    if [ "$POLARIS_PATH" != "$(npm root -g 2>/dev/null || echo '')/polaris-agent/bin/polaris" ]; then
        ok "polaris command available: $POLARIS_PATH"
    else
        ok "polaris command available"
    fi
elif [ -x "$HOME/.local/bin/polaris" ]; then
    ok "polaris at ~/.local/bin/polaris"
elif "$PYTHON" -c "import cli.polaris_cli" 2>/dev/null; then
    ok "polaris importable as Python module"
else
    warn "polaris CLI not fully linked yet."
    info "Use: $PYTHON -m cli.polaris_cli"
fi

# ── Done ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}╭────────────────────────────────────────────────╮${RESET}"
echo -e "${GREEN}│${RESET}  ${CYAN}✦${RESET} ${GREEN}Polaris Agent is ready!${RESET}                      ${GREEN}│${RESET}"
echo -e "${GREEN}│${RESET}                                                ${GREEN}│${RESET}"
echo -e "${GREEN}│${RESET}  First time? Run: ${CYAN}polaris init${RESET}                 ${GREEN}│${RESET}"
echo -e "${GREEN}│${RESET}  Start:          ${CYAN}polaris${RESET}                        ${GREEN}│${RESET}"
echo -e "${GREEN}╰────────────────────────────────────────────────╯${RESET}"
echo ""
