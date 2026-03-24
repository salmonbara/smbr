#!/bin/bash

set -e

# ─── Colors ───────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()    { echo -e "${CYAN}[*]${NC} $1"; }
success() { echo -e "${GREEN}[+]${NC} $1"; }
warn()    { echo -e "${YELLOW}[!]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }

echo ""
echo -e "${CYAN}  ███████╗███╗   ███╗██████╗ ██████╗ ${NC}"
echo -e "${CYAN}  ██╔════╝████╗ ████║██╔══██╗██╔══██╗${NC}"
echo -e "${CYAN}  ███████╗██╔████╔██║██████╔╝██████╔╝${NC}"
echo -e "${CYAN}  ╚════██║██║╚██╔╝██║██╔══██╗██╔══██╗${NC}"
echo -e "${CYAN}  ███████║██║ ╚═╝ ██║██████╔╝██║  ██║${NC}"
echo -e "${CYAN}  ╚══════╝╚═╝     ╚═╝╚═════╝ ╚═╝  ╚═╝${NC}"
echo ""
echo -e "  Pentest Recon & Exploitation Assistant"
echo ""

# ─── 1. Check Python ──────────────────────────────────────────────────────────
info "Checking Python..."

if ! command -v python3 &>/dev/null; then
    error "Python 3 is required but not installed.\n  sudo apt install python3 python3-pip"
fi

PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 8 ]; }; then
    error "Python 3.8+ required. Found: $PY_VERSION"
fi

success "Python $PY_VERSION found"

# ─── 2. Check pip ─────────────────────────────────────────────────────────────
if ! command -v pip3 &>/dev/null && ! python3 -m pip --version &>/dev/null; then
    error "pip not found.\n  sudo apt install python3-pip"
fi

# ─── 3. Check git ─────────────────────────────────────────────────────────────
if ! command -v git &>/dev/null; then
    error "git is required but not installed.\n  sudo apt install git"
fi

# ─── 4. Locate or clone repo ──────────────────────────────────────────────────

# When piped via curl, BASH_SOURCE[0] is empty — so SCRIPT_DIR will be empty
# When run as `bash install.sh`, BASH_SOURCE[0] is the actual script path
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]:-}" )" 2>/dev/null && pwd || echo "" )"
REMOTE_DIR="$HOME/.smbr/src"

if [ -n "$SCRIPT_DIR" ] && [ -f "$SCRIPT_DIR/smbr" ] && [ -d "$SCRIPT_DIR/smbrlib" ]; then
    # Running from inside a cloned repo
    info "Local repo detected at $SCRIPT_DIR"
    INSTALL_DIR="$SCRIPT_DIR"
    success "Using local files — skipping clone"

elif [ -d "$REMOTE_DIR/.git" ]; then
    # Already installed — update
    info "Updating existing installation..."
    git -C "$REMOTE_DIR" pull --quiet
    success "Updated to latest version"
    INSTALL_DIR="$REMOTE_DIR"

else
    # Fresh install via curl
    info "Cloning smbr..."
    mkdir -p "$(dirname "$REMOTE_DIR")"
    git clone --quiet https://github.com/salmonbara/smbr "$REMOTE_DIR"
    success "Cloned to $REMOTE_DIR"
    INSTALL_DIR="$REMOTE_DIR"
fi

# ─── 5. Install Python dependencies ──────────────────────────────────────────
info "Installing Python dependencies..."

PKGS="typer rich textual pyperclip"

# Try normal pip first
if python3 -m pip install --quiet --upgrade $PKGS 2>/dev/null; then
    success "Dependencies installed"

# Kali / Debian / Ubuntu 23.04+ block system pip — retry with --break-system-packages
elif python3 -m pip install --quiet --upgrade --break-system-packages $PKGS 2>/dev/null; then
    success "Dependencies installed (--break-system-packages)"

else
    error "Could not install dependencies automatically.\n  Try manually:\n  pip install --break-system-packages typer rich textual pyperclip"
fi

# ─── 6. Decide bin directory ──────────────────────────────────────────────────
if [ -w /usr/local/bin ]; then
    BIN_DIR="/usr/local/bin"
else
    BIN_DIR="$HOME/.local/bin"
    mkdir -p "$BIN_DIR"
fi

# ─── 7. Create launcher scripts ───────────────────────────────────────────────
info "Installing launchers to $BIN_DIR..."

cat > "$INSTALL_DIR/.smbr_launcher" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/smbr" "\$@"
EOF
chmod +x "$INSTALL_DIR/.smbr_launcher"

cat > "$INSTALL_DIR/.s_launcher" << EOF
#!/bin/bash
exec python3 "$INSTALL_DIR/smbr" arsenal "\$@"
EOF
chmod +x "$INSTALL_DIR/.s_launcher"

ln -sf "$INSTALL_DIR/.smbr_launcher" "$BIN_DIR/smbr"
ln -sf "$INSTALL_DIR/.s_launcher"    "$BIN_DIR/s"

# ─── 8. PATH check ────────────────────────────────────────────────────────────
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    warn "$BIN_DIR is not in your PATH"
    echo ""
    echo "  Add this to your ~/.bashrc or ~/.zshrc:"
    echo -e "  ${YELLOW}export PATH=\"\$PATH:$BIN_DIR\"${NC}"
    echo ""
    echo "  Then reload:"
    echo -e "  ${YELLOW}source ~/.bashrc${NC}"
    echo ""
fi

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
success "Installation complete!"
echo ""
echo "  Commands available:"
echo -e "  ${CYAN}smbr${NC}   → main tool"
echo -e "  ${CYAN}s${NC}      → shortcut for smbr arsenal (TUI)"
echo ""
echo "  Quick start:"
echo -e "  ${YELLOW}smbr --help${NC}"
echo -e "  ${YELLOW}smbr recon 10.10.10.10${NC}"
echo -e "  ${YELLOW}s${NC}"
echo ""