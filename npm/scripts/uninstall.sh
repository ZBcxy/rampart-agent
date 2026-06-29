#!/usr/bin/env bash
# ✦ Rampart Agent — npm preuninstall script
# Cleans up the Python package and data when npm uninstall is run.
set -e

# ── Color helpers ─────────────────────────────────────────────────────────

if [ -t 1 ]; then
    GREEN='\033[32m'; YELLOW='\033[33m'; CYAN='\033[36m'; RED='\033[31m'; DIM='\033[2m'; RESET='\033[0m'
else
    GREEN=''; YELLOW=''; CYAN=''; RED=''; DIM=''; RESET=''
fi

ok()   { echo -e "  ${GREEN}✓${RESET} $1"; }
warn() { echo -e "  ${YELLOW}!${RESET} $1"; }
info() { echo -e "  ${CYAN}ℹ${RESET} $1"; }

echo ""
echo -e "${CYAN}✦ Rampart Agent — npm uninstall${RESET}"
echo ""

# ── Pip uninstall ─────────────────────────────────────────────────────────

echo "▸ Python package"

for py in python3.12 python3.11 python3; do
    if command -v "$py" &>/dev/null; then
        if "$py" -c "import cli.rampart_cli" 2>/dev/null; then
            "$py" -m pip uninstall rampart-agent -y -q 2>/dev/null && ok "Removed rampart-agent" || warn "pip uninstall note: may need manual cleanup"
            break
        fi
    fi
done

# ── Remove ~/.local/bin/rampart ───────────────────────────────────────────

if [ -f "$HOME/.local/bin/rampart" ]; then
    rm -f "$HOME/.local/bin/rampart"
    ok "Removed ~/.local/bin/rampart"
fi

if [ -f "$HOME/.local/bin/rampart.bat" ]; then
    rm -f "$HOME/.local/bin/rampart.bat"
    ok "Removed ~/.local/bin/rampart.bat"
fi

# ── Data directory ────────────────────────────────────────────────────────

RAMPART_HOME="${RAMPART_HOME:-$HOME/.rampart}"

if [ -d "$RAMPART_HOME" ]; then
    echo ""
    echo -e "  ${YELLOW}Keep data directory?${RESET}"
    echo -e "  ${DIM}$RAMPART_HOME${RESET}"
    echo -e "  ${DIM}(contains config, sessions, profiles, history)${RESET}"
    echo ""

    # In non-interactive mode, keep data by default
    if [ -t 0 ]; then
        read -p "  Remove data? [y/N] " -n 1 -r REPLY
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$RAMPART_HOME"
            ok "Removed $RAMPART_HOME"
        else
            info "Kept data at $RAMPART_HOME"
        fi
    else
        info "Non-interactive — data kept at $RAMPART_HOME"
        info "To remove manually: rm -rf $RAMPART_HOME"
    fi
fi

# ── PATH cleanup ──────────────────────────────────────────────────────────

BIN_DIR="$HOME/.local/bin"
CLEANED=0

for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile" "$HOME/.bash_profile"; do
    if [ -f "$rc" ]; then
        # Remove Rampart PATH lines
        if grep -q "# Rampart Agent PATH" "$rc" 2>/dev/null; then
            # Create temp file without Rampart lines
            sed -i.bak '/# Rampart Agent PATH/d; /^export PATH=.*\.local\/bin:\$PATH"$/d' "$rc" 2>/dev/null || true
            rm -f "${rc}.bak"
            CLEANED=$((CLEANED + 1))
        fi
    fi
done

if [ $CLEANED -gt 0 ]; then
    ok "Cleaned PATH from shell profiles"
fi

# ── Done ──────────────────────────────────────────────────────────────────

echo ""
echo -e "${GREEN}✦ Rampart Agent has been uninstalled.${RESET}"
echo ""
echo -e "  ${DIM}Reinstall anytime:${RESET}"
echo -e "  ${CYAN}npm install -g rampart-agent${RESET}"
echo -e "  ${CYAN}pip install rampart-agent${RESET}"
echo ""
