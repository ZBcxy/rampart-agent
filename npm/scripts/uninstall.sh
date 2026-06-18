#!/usr/bin/env bash
# ✦ Polaris Agent — npm preuninstall script
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
echo -e "${CYAN}✦ Polaris Agent — npm uninstall${RESET}"
echo ""

# ── Pip uninstall ─────────────────────────────────────────────────────────

echo "▸ Python package"

for py in python3.12 python3.11 python3; do
    if command -v "$py" &>/dev/null; then
        if "$py" -c "import cli.polaris_cli" 2>/dev/null; then
            "$py" -m pip uninstall polaris-agent -y -q 2>/dev/null && ok "Removed polaris-agent" || warn "pip uninstall note: may need manual cleanup"
            break
        fi
    fi
done

# ── Remove ~/.local/bin/polaris ───────────────────────────────────────────

if [ -f "$HOME/.local/bin/polaris" ]; then
    rm -f "$HOME/.local/bin/polaris"
    ok "Removed ~/.local/bin/polaris"
fi

if [ -f "$HOME/.local/bin/polaris.bat" ]; then
    rm -f "$HOME/.local/bin/polaris.bat"
    ok "Removed ~/.local/bin/polaris.bat"
fi

# ── Data directory ────────────────────────────────────────────────────────

POLARIS_HOME="${POLARIS_HOME:-$HOME/.polaris}"

if [ -d "$POLARIS_HOME" ]; then
    echo ""
    echo -e "  ${YELLOW}Keep data directory?${RESET}"
    echo -e "  ${DIM}$POLARIS_HOME${RESET}"
    echo -e "  ${DIM}(contains config, sessions, profiles, history)${RESET}"
    echo ""

    # In non-interactive mode, keep data by default
    if [ -t 0 ]; then
        read -p "  Remove data? [y/N] " -n 1 -r REPLY
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            rm -rf "$POLARIS_HOME"
            ok "Removed $POLARIS_HOME"
        else
            info "Kept data at $POLARIS_HOME"
        fi
    else
        info "Non-interactive — data kept at $POLARIS_HOME"
        info "To remove manually: rm -rf $POLARIS_HOME"
    fi
fi

# ── PATH cleanup ──────────────────────────────────────────────────────────

BIN_DIR="$HOME/.local/bin"
CLEANED=0

for rc in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.profile" "$HOME/.bash_profile"; do
    if [ -f "$rc" ]; then
        # Remove Polaris PATH lines
        if grep -q "# Polaris Agent PATH" "$rc" 2>/dev/null; then
            # Create temp file without Polaris lines
            sed -i.bak '/# Polaris Agent PATH/d; /^export PATH=.*\.local\/bin:\$PATH"$/d' "$rc" 2>/dev/null || true
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
echo -e "${GREEN}✦ Polaris Agent has been uninstalled.${RESET}"
echo ""
echo -e "  ${DIM}Reinstall anytime:${RESET}"
echo -e "  ${CYAN}npm install -g polaris-agent${RESET}"
echo -e "  ${CYAN}pip install polaris-agent${RESET}"
echo ""
