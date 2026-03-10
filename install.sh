#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════╗
# ║              yomu · 読む — installer                     ║
# ║   anikai.to + AnimePahe CLI downloader by Kopret         ║
# ║   https://github.com/ad3n1l/yomu                         ║
# ╚══════════════════════════════════════════════════════════╝

set -e

REPO="https://github.com/ad3n1l/yomu"
REPO_RAW="https://raw.githubusercontent.com/ad3n1l/yomu/main"

# ── Colors ────────────────────────────────────────────────────────────────────
RS="\033[0m"
B="\033[1m"
D="\033[2m"
G="\033[92m"
C="\033[96m"
Y="\033[93m"
RE="\033[91m"

info()    { echo -e "  ${C}•${RS} $*"; }
success() { echo -e "  ${G}✓${RS} $*"; }
warn()    { echo -e "  ${Y}⚠${RS}  $*"; }
error()   { echo -e "  ${RE}✗${RS} $*" >&2; exit 1; }
step()    { echo -e "\n  ${B}$*${RS}"; echo -e "  ${D}$(printf '─%.0s' {1..50})${RS}"; }

# ── Banner ────────────────────────────────────────────────────────────────────
echo ""
echo -e "${C}${B}"
echo '  ██╗   ██╗ ██████╗ ███╗   ███╗██╗   ██╗'
echo '  ╚██╗ ██╔╝██╔═══██╗████╗ ████║██║   ██║'
echo '   ╚████╔╝ ██║   ██║██╔████╔██║██║   ██║'
echo '    ╚██╔╝  ██║   ██║██║╚██╔╝██║██║   ██║'
echo '     ██║   ╚██████╔╝██║ ╚═╝ ██║╚██████╔╝'
echo '     ╚═╝    ╚═════╝ ╚═╝     ╚═╝ ╚═════╝ '
echo -e "${RS}"
echo -e "  ${D}読む · anime downloader installer${RS}"
echo ""

# ── Detect system ─────────────────────────────────────────────────────────────
step "Detecting system"

IS_TERMUX=false
IS_MACOS=false
IS_DEBIAN=false

if [[ -n "$PREFIX" && "$PREFIX" == *"com.termux"* ]]; then
    IS_TERMUX=true
    info "Detected: Termux (Android)"
elif [[ "$(uname)" == "Darwin" ]]; then
    IS_MACOS=true
    info "Detected: macOS"
elif [[ -f /etc/debian_version ]]; then
    IS_DEBIAN=true
    info "Detected: Debian / Ubuntu"
else
    warn "Unknown system — treating as generic Linux (Debian-style)"
    IS_DEBIAN=true
fi

# ── Check for git ─────────────────────────────────────────────────────────────
step "Checking dependencies"

if ! command -v git &>/dev/null; then
    warn "git not found — installing..."
    if $IS_TERMUX; then
        pkg install -y git
    elif $IS_MACOS; then
        # macOS: git comes with Xcode CLI tools
        xcode-select --install 2>/dev/null || true
        # Wait briefly in case it triggers the GUI installer
        sleep 2
        command -v git &>/dev/null || error "Please install git manually: https://git-scm.com"
    elif $IS_DEBIAN; then
        sudo apt-get update -qq && sudo apt-get install -y git
    fi
    success "git installed"
else
    success "git $(git --version | awk '{print $3}')"
fi

# ── Check / install Python 3 ──────────────────────────────────────────────────
if ! command -v python3 &>/dev/null; then
    warn "python3 not found — installing..."
    if $IS_TERMUX; then
        pkg install -y python
    elif $IS_MACOS; then
        command -v brew &>/dev/null \
            && brew install python3 \
            || error "Install Python 3 from https://python.org or install Homebrew first."
    elif $IS_DEBIAN; then
        sudo apt-get update -qq && sudo apt-get install -y python3 python3-pip
    fi
fi

PYTHON=$(command -v python3)
PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
success "Python $PY_VER"

# Minimum Python 3.10 required (for match statements / type hints in yomu)
PY_MAJOR=$("$PYTHON" -c "import sys; print(sys.version_info.major)")
PY_MINOR=$("$PYTHON" -c "import sys; print(sys.version_info.minor)")
if [[ "$PY_MAJOR" -lt 3 || ( "$PY_MAJOR" -eq 3 && "$PY_MINOR" -lt 10 ) ]]; then
    error "yomu requires Python 3.10+. You have $PY_VER. Please upgrade Python."
fi

# ── pip ───────────────────────────────────────────────────────────────────────
if ! "$PYTHON" -m pip --version &>/dev/null; then
    warn "pip not found — installing..."
    if $IS_TERMUX; then
        pkg install -y python
    elif $IS_DEBIAN; then
        sudo apt-get install -y python3-pip
    elif $IS_MACOS; then
        "$PYTHON" -m ensurepip --upgrade 2>/dev/null || \
            error "Could not install pip. Try: python3 -m ensurepip"
    fi
fi
success "pip available"

# ── yt-dlp ────────────────────────────────────────────────────────────────────
step "Installing yt-dlp"

if command -v yt-dlp &>/dev/null; then
    success "yt-dlp already installed ($(yt-dlp --version))"
else
    if $IS_TERMUX; then
        pkg install -y yt-dlp && success "yt-dlp installed via pkg"
    elif $IS_MACOS && command -v brew &>/dev/null; then
        brew install yt-dlp && success "yt-dlp installed via brew"
    else
        "$PYTHON" -m pip install -q yt-dlp && success "yt-dlp installed via pip"
    fi
fi

# ── Python dependencies ───────────────────────────────────────────────────────
step "Installing Python dependencies"

PIP_FLAGS=""
# On system Python (Debian/Ubuntu 23.04+) we need --break-system-packages
if $IS_DEBIAN && "$PYTHON" -m pip install --help 2>&1 | grep -q "break-system"; then
    PIP_FLAGS="--break-system-packages"
fi

"$PYTHON" -m pip install -q $PIP_FLAGS requests beautifulsoup4 lxml
success "requests, beautifulsoup4, lxml installed"

# ── Clone / update yomu ───────────────────────────────────────────────────────
step "Pulling yomu from GitHub"

# Decide install location
if $IS_TERMUX; then
    INSTALL_DIR="$HOME/.yomu-src"
elif $IS_MACOS; then
    INSTALL_DIR="$HOME/.local/yomu"
else
    INSTALL_DIR="$HOME/.local/yomu"
fi

if [[ -d "$INSTALL_DIR/.git" ]]; then
    info "Existing install found — updating..."
    git -C "$INSTALL_DIR" pull --ff-only
    success "Updated to latest"
else
    info "Cloning $REPO → $INSTALL_DIR"
    git clone --depth 1 "$REPO" "$INSTALL_DIR"
    success "Cloned"
fi

# ── Install yomu package ──────────────────────────────────────────────────────
step "Installing yomu"

"$PYTHON" -m pip install -q $PIP_FLAGS -e "$INSTALL_DIR"
success "yomu package installed"

# ── Create the `yomu` command ─────────────────────────────────────────────────
step "Setting up the yomu command"

# Find where pip puts scripts
SCRIPT_DIR=$("$PYTHON" -m pip show yomu 2>/dev/null | grep ^Location | awk '{print $2}')

# Try to locate the installed entry-point binary
YOMU_BIN=$(command -v yomu 2>/dev/null || true)

if [[ -z "$YOMU_BIN" ]]; then
    # pip installed the script somewhere not on PATH — create a wrapper manually
    if $IS_TERMUX; then
        BIN_DIR="$PREFIX/bin"
    elif $IS_MACOS; then
        BIN_DIR="$HOME/.local/bin"
        mkdir -p "$BIN_DIR"
    else
        BIN_DIR="$HOME/.local/bin"
        mkdir -p "$BIN_DIR"
    fi

    cat > "$BIN_DIR/yomu" <<WRAPPER
#!/usr/bin/env bash
exec "$PYTHON" -m yomu "\$@"
WRAPPER
    chmod +x "$BIN_DIR/yomu"
    YOMU_BIN="$BIN_DIR/yomu"
    success "Wrapper created at $YOMU_BIN"
else
    success "yomu command at $YOMU_BIN"
fi

# ── PATH check ────────────────────────────────────────────────────────────────
step "Checking PATH"

YOMU_BIN_DIR=$(dirname "$YOMU_BIN")
SHELL_RC=""

if $IS_TERMUX; then
    SHELL_RC="$HOME/.bashrc"
elif [[ "$SHELL" == *"zsh"* ]]; then
    SHELL_RC="$HOME/.zshrc"
else
    SHELL_RC="$HOME/.bashrc"
fi

if ! echo "$PATH" | tr ':' '\n' | grep -qx "$YOMU_BIN_DIR"; then
    warn "$YOMU_BIN_DIR is not in PATH — adding to $SHELL_RC"
    echo "" >> "$SHELL_RC"
    echo "# yomu" >> "$SHELL_RC"
    echo "export PATH=\"$YOMU_BIN_DIR:\$PATH\"" >> "$SHELL_RC"
    warn "Run:  source $SHELL_RC  (or restart your terminal)"
else
    success "PATH is already set up"
fi

# ── Termux: storage access reminder ──────────────────────────────────────────
if $IS_TERMUX; then
    echo ""
    warn "Termux users: if this is your first time, run:"
    echo -e "  ${C}termux-setup-storage${RS}"
    echo -e "  ${D}(allows saving downloads to ~/storage/downloads/yomu/)${RS}"
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "  ${B}${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RS}"
echo -e "  ${G}${B} yomu is installed! ${RS}"
echo -e "  ${B}${G}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RS}"
echo ""
echo -e "  Run ${C}${B}yomu${RS} to start"
echo ""
echo -e "  ${D}To update later:  git -C $INSTALL_DIR pull${RS}"
echo -e "  ${D}To uninstall:     pip uninstall yomu && rm -rf $INSTALL_DIR${RS}"
echo ""
