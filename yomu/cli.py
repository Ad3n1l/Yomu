"""
yomu · cli.py
Full interactive flow:
  Search → Pick anime → Select episodes → Quality → Audio → Subtitles → Download
"""

import sys
import re
from typing import Optional

# ── Colors ────────────────────────────────────────────────────────────────────
RS = "\033[0m"
B  = "\033[1m"
D  = "\033[2m"
G  = "\033[92m"
C  = "\033[96m"
Y  = "\033[93m"
RE = "\033[91m"
M  = "\033[95m"
W  = "\033[97m"
BL = "\033[94m"

def co(text, *codes): return "".join(codes) + str(text) + RS
def hr(n=52):         print(co("  " + "─" * n, D))


# ── Prompt / menu helpers ─────────────────────────────────────────────────────

def prompt(msg: str, default="") -> str:
    suf = co(f" [{default}]", D) if default else ""
    try:
        val = input(co("  › ", C) + msg + suf + " ").strip()
        return val or default
    except (KeyboardInterrupt, EOFError):
        print()
        sys.exit(0)


def choose(items: list, label_fn=None, title="Select", back=True) -> Optional[int]:
    """Numbered single-pick menu. Returns 0-based index or None."""
    if not items:
        print(co("  (no results)", D))
        return None
    print()
    pad = max(0, 46 - len(title))
    print(co(f"  ── {title} ", B) + co("─" * pad, D))
    for i, item in enumerate(items, 1):
        label = label_fn(item) if label_fn else str(item)
        print(f"  {co(str(i).rjust(3), Y)}  {label}")
    if back:
        print(f"\n  {co('  0', Y)}  {co('← back', D)}")
    print()
    while True:
        raw = prompt("Pick").strip()
        if raw == "0" and back:
            return None
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(items):
                return idx
        print(co("  Invalid, try again.", RE))


def paginate(items: list, label_fn=None, title="Select", page_size=20) -> Optional[int]:
    """Paginated menu for long episode lists."""
    total = len(items)
    pages = max(1, (total + page_size - 1) // page_size)
    page  = 0
    while True:
        s, e = page * page_size, min((page + 1) * page_size, total)
        print()
        print(co(f"  ── {title}  ({page+1}/{pages}) ", B) + co("─" * 28, D))
        for i, item in enumerate(items[s:e], s + 1):
            label = label_fn(item) if label_fn else str(item)
            print(f"  {co(str(i).rjust(4), Y)}  {label}")
        nav = []
        if page > 0:       nav.append(co("p=prev", D))
        if page < pages-1: nav.append(co("n=next", D))
        nav.append(co("0=back", D))
        print("\n  " + "   ".join(nav)); print()
        raw = prompt("Number / n / p / 0").lower()
        if raw == "0":                        return None
        if raw == "n" and page < pages - 1:   page += 1; continue
        if raw == "p" and page > 0:           page -= 1; continue
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < total:
                return idx
        print(co("  Invalid.", RE))


def confirm(msg: str) -> bool:
    return prompt(f"{msg} [y/N]").lower() in ("y", "yes")


# ── Banner ────────────────────────────────────────────────────────────────────

BANNER = r"""
  ██╗   ██╗ ██████╗ ███╗   ███╗██╗   ██╗
  ╚██╗ ██╔╝██╔═══██╗████╗ ████║██║   ██║
   ╚████╔╝ ██║   ██║██╔████╔██║██║   ██║
    ╚██╔╝  ██║   ██║██║╚██╔╝██║██║   ██║
     ██║   ╚██████╔╝██║ ╚═╝ ██║╚██████╔╝
     ╚═╝    ╚═════╝ ╚═╝     ╚═╝ ╚═════╝
"""

def banner():
    print(co(BANNER, C))
    from yomu.downloader import DOWNLOAD_DIR
    print(co(f"  読む  ·  anikai.to + AnimePahe", D))
    print(co(f"  Downloads → {DOWNLOAD_DIR}", D))
    print()


# ── STEP 1 — Search ───────────────────────────────────────────────────────────

def do_search() -> Optional[dict]:
    query = prompt("Search anime")
    if not query:
        return None

    src_idx = choose(
        ["anikai.to", "AnimePahe", "Both"],
        label_fn=str, title="Source",
    )
    if src_idx is None:
        return None

    results = []
    print()

    if src_idx in (0, 2):
        print(co("  Searching anikai.to …", D), end=" ", flush=True)
        try:
            from yomu.sources.anikai import search
            r = search(query)
            results.extend(r)
            print(co(f"{len(r)} results", G))
        except Exception as e:
            print(co(f"error: {e}", RE))

    if src_idx in (1, 2):
        print(co("  Searching AnimePahe …", D), end=" ", flush=True)
        try:
            from yomu.sources.animepahe import search
            r = search(query)
            results.extend(r)
            print(co(f"{len(r)} results", G))
        except Exception as e:
            print(co(f"error: {e}", RE))

    if not results:
        print(co("\n  No results found.", Y))
        return None

    def label(a):
        src_col = BL if a["source"] == "anikai" else M
        src     = co(f"[{a['source']:^10}]", src_col)
        meta    = "  ".join(filter(None, [a.get("type",""), a.get("year",""), a.get("status","")]))
        return f"{src}  {co(a['title'], W)}  {co(meta, D)}"

    idx = choose(results, label_fn=label, title=f"Results — \"{query}\"")
    return results[idx] if idx is not None else None


# ── STEP 2 — Fetch & select episodes ─────────────────────────────────────────

def fetch_episodes(anime: dict) -> list[dict]:
    print(co(f"\n  Fetching episodes …", D), end=" ", flush=True)
    try:
        if anime["source"] == "anikai":
            from yomu.sources.anikai import get_episodes
            eps = get_episodes(anime["id"])
        else:
            from yomu.sources.animepahe import get_all_episodes
            eps = get_all_episodes(anime["id"])
        print(co(f"{len(eps)} episodes", G))
        return eps
    except Exception as e:
        print(co(f"error: {e}", RE))
        return []


def _ep_num(ep) -> float:
    try:
        return float(re.findall(r"[\d.]+", str(ep["number"]))[0])
    except Exception:
        return 0


def select_episodes(episodes: list[dict]) -> list[dict]:
    """
    Let user pick:  a=all  |  N  |  N-M  |  N,M,K  |  browse list
    Returns the chosen subset.
    """
    total = len(episodes)
    print()
    hr()
    print(co(f"  {total} episodes available", W))
    print(f"  {co('a', Y)}      = all episodes")
    print(f"  {co('N', Y)}      = single  (e.g. {co('5', C)})")
    print(f"  {co('N-M', Y)}    = range   (e.g. {co('1-12', C)})")
    print(f"  {co('N,M,K', Y)}  = picks   (e.g. {co('1,3,7', C)})")
    print(f"  {co('l', Y)}      = browse list")
    hr()

    raw = prompt("Episodes").strip().lower()

    if raw == "a":
        return episodes

    if raw == "l":
        idx = paginate(
            episodes,
            label_fn=lambda e: f"Ep {e['number'].rjust(4)}  {co(e.get('title',''), D)}",
            title="Episodes",
        )
        return [episodes[idx]] if idx is not None else []

    ep_map  = {ep["number"]: ep for ep in episodes}
    idx_map = {str(i + 1): ep for i, ep in enumerate(episodes)}

    def resolve(tok):
        tok = tok.strip()
        return ep_map.get(tok) or ep_map.get(tok.lstrip("0") or "0") or idx_map.get(tok)

    if "-" in raw and "," not in raw:
        parts = raw.split("-", 1)
        try:
            a, b = float(parts[0]), float(parts[1])
            sel = [ep for ep in episodes if a <= _ep_num(ep) <= b]
            if sel:
                return sel
        except ValueError:
            pass

    if "," in raw:
        sel = [ep for tok in raw.split(",") if (ep := resolve(tok))]
        if sel:
            return sel

    ep = resolve(raw)
    if ep:
        return [ep]

    print(co("  Couldn't parse — opening episode list.", Y))
    idx = paginate(
        episodes,
        label_fn=lambda e: f"Ep {e['number'].rjust(4)}  {co(e.get('title',''), D)}",
        title="Episodes",
    )
    return [episodes[idx]] if idx is not None else []


# ── STEP 3 — Download preferences ────────────────────────────────────────────

def pick_preferences(links_sample: list[dict]) -> dict:
    """
    Given a sample of available links (from first episode), let user choose:
    - Audio: Sub / Dub / Raw / Best available
    - Quality: 1080p / 720p / 480p / 360p / Best available
    - Subtitles: Embedded / External .srt / None
    Returns prefs dict.
    """
    print()
    hr()
    print(co("  Download preferences", B))
    hr()

    # ── Audio ─────────────────────────────────────────────────────────────────
    # Detect what's actually available from the links
    available_audio = sorted({l.get("audio", "").lower() for l in links_sample if l.get("audio")})
    audio_options = []
    if "jpn" in available_audio or "ja" in available_audio or not available_audio:
        audio_options.append(("jpn", "Sub  (Japanese audio + subtitles)"))
    if "eng" in available_audio or "en" in available_audio:
        audio_options.append(("eng", "Dub  (English audio)"))
    if "raw" in available_audio:
        audio_options.append(("raw", "Raw  (no subtitles)"))
    audio_options.append(("", "Best available  (no preference)"))

    print()
    audio_idx = choose(
        audio_options,
        label_fn=lambda x: x[1],
        title="Audio",
        back=False,
    )
    audio = audio_options[audio_idx][0] if audio_idx is not None else ""

    # ── Quality ───────────────────────────────────────────────────────────────
    # Detect available resolutions
    available_q = sorted(
        {l.get("quality","") for l in links_sample if l.get("quality","") not in ("","unknown")},
        key=lambda q: int(q.rstrip("p")) if q.rstrip("p").isdigit() else 0,
        reverse=True,
    )
    quality_options = [(q, q) for q in available_q] if available_q else []
    quality_options += [
        ("1080p", "1080p  (Full HD)"),
        ("720p",  "720p   (HD)"),
        ("480p",  "480p   (SD)"),
        ("360p",  "360p   (Low)"),
    ]
    # Deduplicate while preserving order
    seen = set()
    quality_options_deduped = []
    for q, label in quality_options:
        if q not in seen:
            seen.add(q)
            quality_options_deduped.append((q, label))
    quality_options_deduped.append(("best", "Best available  (auto)"))

    quality_idx = choose(
        quality_options_deduped,
        label_fn=lambda x: x[1],
        title="Quality",
        back=False,
    )
    quality = quality_options_deduped[quality_idx][0] if quality_idx is not None else "best"

    # ── Subtitles ─────────────────────────────────────────────────────────────
    sub_options = [
        ("embedded", "Embedded  — baked into the video file (mkv)"),
        ("external", "External  — download .srt alongside the video"),
        ("none",     "None      — no subtitles"),
    ]
    sub_idx = choose(
        sub_options,
        label_fn=lambda x: x[1],
        title="Subtitles",
        back=False,
    )
    sub_mode = sub_options[sub_idx][0] if sub_idx is not None else "none"

    # Sub language (only if subtitles enabled)
    sub_lang = "en"
    if sub_mode != "none":
        sub_lang = prompt("Subtitle language code", default="en")

    # ── yt-dlp preference ─────────────────────────────────────────────────────
    force_ytdlp = confirm("Force yt-dlp for all downloads? (recommended for AnimePahe/kwik)")

    prefs = {
        "audio": audio,
        "quality": quality,
        "sub_mode": sub_mode,
        "sub_lang": sub_lang,
        "force_ytdlp": force_ytdlp,
    }

    print()
    hr()
    print(co("  Your preferences", B))
    print(f"  Audio     : {co(audio or 'best available', C)}")
    print(f"  Quality   : {co(quality, C)}")
    print(f"  Subtitles : {co(sub_mode, C)}" + (f"  lang={co(sub_lang,Y)}" if sub_mode != "none" else ""))
    print(f"  yt-dlp    : {co('yes', G) if force_ytdlp else co('auto', D)}")
    hr()

    return prefs


# ── STEP 4 — Fetch links + filter + download ──────────────────────────────────

def get_links(anime: dict, ep: dict) -> list[dict]:
    print(co(f"  Fetching links Ep {ep['number']} …", D), end=" ", flush=True)
    try:
        if anime["source"] == "anikai":
            from yomu.sources.anikai import get_download_links
            links = get_download_links(ep["url"])
        else:
            from yomu.sources.animepahe import get_download_links
            links = get_download_links(anime["id"], ep["session"])
        print(co(f"{len(links)} links", G))
        return links
    except Exception as e:
        print(co(f"error: {e}", RE))
        return []


def filter_links(links: list[dict], prefs: dict) -> Optional[dict]:
    """
    Filter links by audio and quality preference.
    Falls back gracefully if exact match not found.
    Returns the best matching single link.
    """
    if not links:
        return None

    audio   = prefs.get("audio", "")
    quality = prefs.get("quality", "best")

    # Filter by audio first
    audio_filtered = links
    if audio:
        candidates = [l for l in links if l.get("audio","").lower() == audio.lower()]
        if candidates:
            audio_filtered = candidates
        else:
            print(co(f"  ⚠ No {audio} audio found, using best available.", Y))

    # Filter by quality
    if quality not in ("best", "", "unknown"):
        q_match = [l for l in audio_filtered if l.get("quality","") == quality]
        if q_match:
            return q_match[0]
        # Try next best quality (pick highest available ≤ requested)
        req = int(quality.rstrip("p")) if quality.rstrip("p").isdigit() else 9999
        ranked = sorted(
            audio_filtered,
            key=lambda l: abs(int(l["quality"].rstrip("p")) - req)
            if l.get("quality","").rstrip("p").isdigit() else 9999
        )
        if ranked:
            chosen = ranked[0]
            if chosen.get("quality") != quality:
                print(co(f"  ⚠ {quality} not found — using {chosen.get('quality','?')} instead.", Y))
            return chosen

    # Best available — return highest resolution
    ranked = sorted(
        audio_filtered,
        key=lambda l: int(l["quality"].rstrip("p")) if l.get("quality","").rstrip("p").isdigit() else 0,
        reverse=True,
    )
    return ranked[0] if ranked else audio_filtered[0]


def do_download_batch(anime: dict, episodes: list[dict], prefs: dict):
    from yomu import db
    from yomu.downloader import download_episode

    # Get sample links from first episode to show pref options
    # (prefs should already be collected before calling this)

    total = len(episodes)
    print()
    print(co(f"  Downloading {total} episode(s) of {anime['title']}", B))
    hr()

    ok, fail = 0, 0
    for i, ep in enumerate(episodes, 1):
        print(co(f"\n  [{i}/{total}]", Y), co(f"Episode {ep['number']}", W))

        links = get_links(anime, ep)
        if not links:
            print(co(f"  ✗ No links found, skipping.", RE))
            fail += 1
            continue

        link = filter_links(links, prefs)
        if not link:
            print(co("  ✗ No matching link, skipping.", RE))
            fail += 1
            continue

        url     = link["url"]
        quality = link.get("quality", prefs["quality"])
        audio   = link.get("audio",   prefs["audio"])

        # Resolve kwik if not using yt-dlp
        if "kwik" in url and not prefs["force_ytdlp"]:
            print(co("  Resolving kwik …", D), end=" ", flush=True)
            try:
                from yomu.sources.animepahe import resolve_kwik
                resolved = resolve_kwik(url)
                if resolved:
                    url = resolved
                    print(co("OK", G))
                else:
                    print(co("failed → yt-dlp fallback", Y))
                    prefs = {**prefs, "force_ytdlp": True}
            except Exception as e:
                print(co(f"error: {e} → yt-dlp fallback", Y))
                prefs = {**prefs, "force_ytdlp": True}

        referer = ep.get("url", anime.get("url", ""))

        try:
            path = download_episode(
                anime_title    = anime["title"],
                episode_number = ep["number"],
                url            = url,
                quality        = quality,
                audio          = audio,
                referer        = referer,
                sub_mode       = prefs["sub_mode"],
                sub_lang       = prefs["sub_lang"],
                force_ytdlp    = prefs["force_ytdlp"],
            )
            print(co(f"  ✓  Saved: {path}", G))
            ok += 1
            db.add_download(
                source=anime["source"], anime_id=anime["id"],
                anime_title=anime["title"], episode=ep["number"],
                quality=quality, audio=audio, sub_mode=prefs["sub_mode"],
                file_path=str(path),
            )
            db.add_history(
                source=anime["source"], anime_id=anime["id"],
                anime_title=anime["title"], episode=ep["number"],
            )
        except Exception as e:
            print(co(f"  ✗  Failed: {e}", RE))
            fail += 1

    print()
    hr()
    print(co(f"  Done.  {ok} downloaded", G) + co(f"  {fail} failed" if fail else "", RE))
    hr()


# ── Anime detail screen ───────────────────────────────────────────────────────

def anime_screen(anime: dict):
    from yomu import db
    while True:
        print()
        hr()
        print(co(f"  {anime['title']}", B + W))
        print(f"  {co('Source:', D)} {co(anime['source'], C)}   "
              f"{co(anime.get('type',''), D)}  {co(anime.get('year',''), D)}")
        if anime.get("url"):
            print(f"  {co(anime['url'], D)}")
        hr()

        action = choose(
            ["Download episodes", "Add to watchlist", "← Back"],
            label_fn=str, title="Action", back=False,
        )

        if action == 0:
            episodes = fetch_episodes(anime)
            if not episodes:
                continue
            selected = select_episodes(episodes)
            if not selected:
                continue

            # Grab sample links from ep 1 to help populate available qualities/audio
            sample_links = get_links(anime, selected[0])
            prefs = pick_preferences(sample_links)

            if confirm(f"\n  Start downloading {len(selected)} episode(s)?"):
                do_download_batch(anime, selected, prefs)

        elif action == 1:
            db.add_watchlist(anime["source"], anime["id"], anime["title"])
            print(co(f"  ✓  Added to watchlist.", G))

        elif action == 2:
            return


# ── History ───────────────────────────────────────────────────────────────────

def show_history():
    from yomu import db
    rows = db.get_history()
    print()
    hr()
    print(co("  Watch History", B))
    hr()
    if not rows:
        print(co("  Nothing here yet.", D))
    for r in rows:
        sc = BL if r["source"] == "anikai" else M
        src = co(f"[{r['source']:^10}]", sc)
        ep  = co(f"  Ep {r['episode']}", D) if r.get("episode") else ""
        ts  = r["watched_at"][:16].replace("T", " ")
        print(f"  {src}  {co(r['anime_title'], W)}{ep}  {co(ts, D)}")
    print()
    if rows and confirm("Clear all history?"):
        db.clear_history()
        print(co("  Cleared.", G))


def show_downloads():
    from yomu import db
    rows = db.get_downloads()
    print()
    hr()
    print(co("  Downloads Log", B))
    hr()
    if not rows:
        print(co("  Nothing here yet.", D))
    for r in rows:
        sc = BL if r["source"] == "anikai" else M
        src = co(f"[{r['source']:^10}]", sc)
        ep  = f"Ep {r['episode']}" if r.get("episode") else "?"
        tags = "  ".join(filter(None, [r.get("quality",""), r.get("audio",""), r.get("sub_mode","")]))
        ts  = r["downloaded_at"][:16].replace("T", " ")
        print(f"  {src}  {co(r['anime_title'], W)}  {co(ep, Y)}  {co(tags, C)}")
        if r.get("file_path"):
            print(f"         {co(r['file_path'], D)}")
    print()


# ── Watchlist ─────────────────────────────────────────────────────────────────

def show_watchlist():
    from yomu import db
    while True:
        rows = db.get_watchlist()
        print()
        hr()
        print(co("  Watchlist", B))
        hr()
        if not rows:
            print(co("  Your watchlist is empty.", D))
            print()
            return
        for i, r in enumerate(rows, 1):
            sc  = BL if r["source"] == "anikai" else M
            src = co(f"[{r['source']:^10}]", sc)
            ts  = r["added_at"][:10]
            print(f"  {co(str(i).rjust(3), Y)}  {src}  {co(r['anime_title'], W)}  {co(ts, D)}")
        print(f"\n  {co('  0', Y)}  {co('← Back', D)}")
        print()
        raw = prompt("Pick to manage, 0 to go back")
        if raw == "0" or not raw:
            return
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(rows):
                r = rows[idx]
                anime = {
                    "id": r["anime_id"], "title": r["anime_title"],
                    "source": r["source"], "url": "",
                }
                action = choose(
                    ["Download episodes", "Remove from watchlist"],
                    label_fn=str, title=r["anime_title"],
                )
                if action == 0:
                    eps = fetch_episodes(anime)
                    if eps:
                        sel = select_episodes(eps)
                        if sel:
                            sample = get_links(anime, sel[0])
                            prefs  = pick_preferences(sample)
                            if confirm(f"  Start downloading {len(sel)} episode(s)?"):
                                do_download_batch(anime, sel, prefs)
                elif action == 1:
                    db.remove_watchlist(r["source"], r["anime_id"])
                    print(co(f"  ✓  Removed.", G))


# ── Main menu ─────────────────────────────────────────────────────────────────

def main():
    banner()
    while True:
        hr()
        print(f"  {co('1', Y)}  🔍  Search anime")
        print(f"  {co('2', Y)}  📋  Watchlist")
        print(f"  {co('3', Y)}  🕑  History")
        print(f"  {co('4', Y)}  📥  Downloads log")
        print(f"  {co('0', Y)}  ✕   Exit")
        hr()
        print()
        c = prompt("Choose")
        if   c == "1": anime = do_search();  anime and anime_screen(anime)
        elif c == "2": show_watchlist()
        elif c == "3": show_history()
        elif c == "4": show_downloads()
        elif c == "0": print(co("\n  また今度ね。 (またこんどね — see you next time)\n", C)); sys.exit(0)
        else:          print(co("  Invalid.", RE))
