"""
yomu · downloader.py
- Termux  → ~/storage/downloads/yomu/<Anime>/
- Desktop → ~/Downloads/yomu/<Anime>/
- Filename: Attack on Titan - Ep004 [1080p][Dub].mkv
- Direct HTTP for plain mp4, yt-dlp for kwik/m3u8/embed
- Subtitle modes: embedded (baked in), external (.srt), none
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import requests

# ── Audio label map ───────────────────────────────────────────────────────────
AUDIO_LABEL = {
    "jpn": "Sub", "ja": "Sub",
    "eng": "Dub", "en": "Dub",
    "sub": "Sub", "dub": "Dub",
    "raw": "Raw",
}

# ── Download dir ──────────────────────────────────────────────────────────────

def get_download_dir() -> Path:
    is_termux = (
        "com.termux" in os.environ.get("PREFIX", "")
        or os.path.exists("/data/data/com.termux")
    )
    return (
        Path.home() / "storage" / "downloads" / "yomu"
        if is_termux
        else Path.home() / "Downloads" / "yomu"
    )

DOWNLOAD_DIR = get_download_dir()

# ── Filename builder ──────────────────────────────────────────────────────────

def _san(name: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", name).strip()

def build_filename(title, ep_num, quality="", audio="", sub_mode="none", ext="mkv") -> str:
    try:
        ep = f"{int(float(ep_num)):03d}"
    except Exception:
        ep = str(ep_num).zfill(2)

    tags = []
    if quality and quality not in ("best", "unknown", ""):
        tags.append(quality if quality.endswith("p") else f"{quality}p")
    if audio:
        tags.append(AUDIO_LABEL.get(audio.lower(), audio.upper()))
    if sub_mode == "embedded":
        tags.append("CC")

    tag_str = "".join(f"[{t}]" for t in tags)
    return f"{_san(title)} - Ep{ep} {tag_str}".rstrip() + f".{ext}"

# ── Progress bar ──────────────────────────────────────────────────────────────

def _bar(done: int, total: int, w=38):
    G = "\033[92m"; D = "\033[2m"; R = "\033[0m"
    if total > 0:
        ratio = min(done / total, 1.0)
        filled = int(w * ratio)
        pct = f"{ratio*100:5.1f}%"
    else:
        filled, pct = 0, "  ??%"
    bar = f"{G}{'█'*filled}{R}{'░'*(w-filled)}"
    mb  = done / 1_048_576
    tot = f"/{total/1_048_576:.1f}MB" if total > 0 else ""
    sys.stdout.write(f"\r  [{bar}] {pct}  {D}{mb:.1f}MB{tot}{R}  ")
    sys.stdout.flush()

# ── Direct HTTP ───────────────────────────────────────────────────────────────

def direct_download(url: str, dest: Path, referer="") -> Path:
    hdrs = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0",
    }
    if referer:
        hdrs["Referer"] = referer
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part")
    with requests.get(url, headers=hdrs, stream=True, timeout=30) as r:
        r.raise_for_status()
        total = int(r.headers.get("Content-Length", 0))
        done  = 0
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(chunk_size=256 * 1024):
                if chunk:
                    f.write(chunk)
                    done += len(chunk)
                    _bar(done, total)
    sys.stdout.write("\n")
    tmp.rename(dest)
    return dest

# ── yt-dlp ────────────────────────────────────────────────────────────────────

def ytdlp_download(
    url: str,
    dest_dir: Path,
    stem: str,
    referer="",
    quality="best",
    audio="",
    sub_mode="none",
    sub_lang="en",
) -> Optional[Path]:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError(
            "yt-dlp is not installed.\n"
            "  Termux : pkg install yt-dlp\n"
            "  pip    : pip install yt-dlp\n"
            "  apt    : sudo apt install yt-dlp"
        )
    dest_dir.mkdir(parents=True, exist_ok=True)
    out = str(dest_dir / f"{_san(stem)}.%(ext)s")
    cmd = ["yt-dlp", "--no-warnings", "--progress", "-o", out]

    if referer:
        cmd += ["--referer", referer]

    # Quality
    if quality not in ("best", "unknown", ""):
        q = quality.rstrip("p")
        if q.isdigit():
            cmd += ["-f", f"bestvideo[height<={q}]+bestaudio/best[height<={q}]/best"]

    # Subtitles
    if sub_mode == "embedded":
        cmd += ["--embed-subs", "--sub-lang", sub_lang, "--convert-subs", "srt"]
    elif sub_mode == "external":
        cmd += ["--write-subs", "--write-auto-subs", "--sub-lang", sub_lang, "--convert-subs", "srt"]

    cmd += ["--merge-output-format", "mkv", url]

    if subprocess.run(cmd).returncode != 0:
        raise RuntimeError("yt-dlp failed")

    prefix = _san(stem)[:24]
    candidates = sorted(
        [f for f in dest_dir.iterdir() if f.stem.startswith(prefix)],
        key=lambda p: p.stat().st_mtime, reverse=True
    )
    return candidates[0] if candidates else None

# ── Main entry ────────────────────────────────────────────────────────────────

def download_episode(
    anime_title: str,
    episode_number: str,
    url: str,
    quality="best",
    audio="",
    referer="",
    sub_mode="none",     # "embedded" | "external" | "none"
    sub_lang="en",
    force_ytdlp=False,
) -> Path:
    folder = DOWNLOAD_DIR / _san(anime_title)

    use_ytdlp = (
        force_ytdlp
        or "kwik" in url
        or ".m3u8" in url
        or sub_mode == "embedded"
    )

    ext = "mkv" if use_ytdlp else (
        url.split("?")[0].rsplit(".", 1)[-1] if "." in url.split("?")[0] else "mp4"
    )
    if len(ext) > 4 or not ext.isalnum():
        ext = "mp4"

    filename = build_filename(anime_title, episode_number, quality, audio, sub_mode, ext)
    dest = folder / filename
    stem = filename.rsplit(".", 1)[0]

    B = "\033[1m"; D = "\033[2m"; C = "\033[96m"; G = "\033[92m"; R = "\033[0m"
    print(f"\n  {B}{'─'*52}{R}")
    print(f"  {B}{anime_title}{R}  —  Ep {episode_number}")
    print(f"  Quality   {D}:{R} {C}{quality or 'best'}{R}")
    print(f"  Audio     {D}:{R} {C}{AUDIO_LABEL.get(audio.lower(), audio or 'default')}{R}")
    print(f"  Subtitles {D}:{R} {C}{sub_mode}{R}")
    print(f"  File      {D}:{R} {D}{dest}{R}")
    print(f"  Method    {D}:{R} {'yt-dlp' if use_ytdlp else 'Direct HTTP'}")
    print(f"  {B}{'─'*52}{R}\n")

    if use_ytdlp:
        return ytdlp_download(url, folder, stem, referer, quality, audio, sub_mode, sub_lang) or dest
    else:
        return direct_download(url, dest, referer)
