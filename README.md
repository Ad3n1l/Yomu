# yomu · 読む

> *yomu (読む)* — Japanese for "to read / to watch"

A Python CLI tool to search, browse, and download anime from **anikai.to** and **AnimePahe** — with quality selection, sub/dub filtering, subtitle options, episode ranges, watch history, and a watchlist.

```
  ██╗   ██╗ ██████╗ ███╗   ███╗██╗   ██╗
  ╚██╗ ██╔╝██╔═══██╗████╗ ████║██║   ██║
   ╚████╔╝ ██║   ██║██╔████╔██║██║   ██║
    ╚██╔╝  ██║   ██║██║╚██╔╝██║██║   ██║
     ██║   ╚██████╔╝██║ ╚═╝ ██║╚██████╔╝
     ╚═╝    ╚═════╝ ╚═╝     ╚═╝ ╚═════╝
```

---

## Features

| | |
|---|---|
| 🔍 **Search** | anikai.to, AnimePahe, or both at once |
| 🎵 **Audio** | Sub · Dub · Raw — filtered automatically per episode |
| 🎬 **Quality** | 1080p · 720p · 480p · 360p · best available |
| 📝 **Subtitles** | Embedded in mkv · External .srt · None |
| 📦 **Episodes** | Single · Range `1-12` · Picks `1,3,7` · All |
| 📋 **Watchlist** | Save anime, come back and download later |
| 🕑 **History** | Auto-logged on every download |
| 📁 **Smart path** | Termux → `~/storage/downloads/yomu/` · Desktop → `~/Downloads/yomu/` |

**Saved as:** `Attack on Titan - Ep004 [1080p][Sub][CC].mkv`

---

## Installation

There are two ways to install yomu. Use the **installer script** if your system is supported. Otherwise follow the **manual install** steps.

---

### Method 1 — Installer script (recommended)

Supports: **Termux (Android)**, **Ubuntu / Debian**, **macOS**

The installer automatically detects your system, installs all dependencies (Python, git, yt-dlp, pip packages), clones this repo, and registers the `yomu` command.

**Using curl:**
```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ad3n1l/yomu/main/install.sh)
```

**Using wget:**
```bash
bash <(wget -qO- https://raw.githubusercontent.com/ad3n1l/yomu/main/install.sh)
```

> **Termux only:** Run `termux-setup-storage` once before installing yomu so it can save downloads to `~/storage/downloads/`.

After install, just run:
```bash
yomu
```

If `yomu` isn't found after installing, reload your shell:
```bash
source ~/.bashrc   # or source ~/.zshrc
```

---

### Method 2 — Manual install

For any system the installer doesn't cover: Arch Linux, Fedora, Windows (WSL), Alpine, or anywhere you prefer to do things yourself.

#### 1. Requirements

- Python 3.10 or newer
- git
- pip

#### 2. Install yt-dlp

yt-dlp is required for AnimePahe (kwik.si) and any HLS/embedded sources.

```bash
# pip (universal)
pip install yt-dlp

# Arch Linux
sudo pacman -S yt-dlp

# Fedora
sudo dnf install yt-dlp

# Homebrew (macOS)
brew install yt-dlp

# Termux
pkg install yt-dlp
```

#### 3. Clone the repo

```bash
git clone https://github.com/ad3n1l/yomu ~/.local/yomu
cd ~/.local/yomu
```

#### 4. Install Python dependencies

```bash
pip install -e .
```

This installs `requests`, `beautifulsoup4`, `lxml`, and `yt-dlp`, and registers the `yomu` command via pip's entry points.

#### 5. Make sure the command is on PATH

```bash
# Check if it works
yomu --help

# If not found, add pip's script dir to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

> On some systems (Debian/Ubuntu 23.04+) pip may need `--break-system-packages`:
> ```bash
> pip install --break-system-packages -e .
> ```

---

### Updating

```bash
# Installer method
git -C ~/.local/yomu pull    # or ~/.yomu-src on Termux

# Manual method
cd ~/.local/yomu && git pull
```

### Uninstalling

```bash
pip uninstall yomu
rm -rf ~/.local/yomu       # or ~/.yomu-src on Termux
rm -f ~/.local/bin/yomu    # if a wrapper was created
```

---

## Usage

```bash
yomu
```

### Full flow

```
yomu
 │
 ├─ 1. Search
 │       Enter title → pick source (anikai.to / AnimePahe / Both)
 │       → select anime from results
 │
 ├─ 2. Episode selection
 │       a       = all episodes
 │       5       = single episode
 │       1-12    = range
 │       1,3,7   = specific episodes
 │       l       = browse paginated list
 │
 ├─ 3. Preferences  (set once, applied to every episode in the batch)
 │       Audio     : Sub (jpn) · Dub (eng) · Raw · Best available
 │       Quality   : 1080p · 720p · 480p · 360p · Best available
 │       Subtitles : Embedded (baked into mkv) · External .srt · None
 │       Sub lang  : en / ja / etc.
 │
 └─ 4. Download
         Filters each episode's links by your audio + quality choice
         Falls back gracefully if exact match isn't available
         yt-dlp handles kwik.si, m3u8, and embedded players
         Direct HTTP for plain mp4 links
         Saved to:
           Termux  → ~/storage/downloads/yomu/<Title>/
           Desktop → ~/Downloads/yomu/<Title>/
```

### Other menus

| Menu | What it does |
|---|---|
| Watchlist | Save an anime, download episodes later |
| History | View every episode you've downloaded |
| Downloads log | Full log with quality, audio, file path |

---

## Source notes

### AnimePahe
Uses the official JSON API for search and episode data — very reliable. Download links go through **kwik.si**; always choose yt-dlp when prompted. Sub/Dub availability depends on what AnimePahe has licensed; most anime are sub-only.

### anikai.to
HTML scraping via BeautifulSoup. Works well for most titles. If something breaks after a site layout change, [open an issue](https://github.com/ad3n1l/yomu/issues).

---

## Storage

| | Path |
|---|---|
| Database | `~/.yomu/yomu.db` |
| Downloads (Termux) | `~/storage/downloads/yomu/<Title>/` |
| Downloads (Desktop/macOS) | `~/Downloads/yomu/<Title>/` |

---

## Built by

[Kopret](https://kopret.vercel.app) · [devkopret@gmail.com](mailto:devkopret@gmail.com)

---

## License

MIT
