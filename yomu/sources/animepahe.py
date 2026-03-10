"""
yomu · sources/animepahe.py
AnimePahe JSON API — search, episode listing, kwik link extraction + resolver.
AnimePahe exposes audio language (jpn/eng) and resolution per button — we use all of it.
"""

import re
import time
import requests
from typing import Optional
from urllib.parse import urljoin

BASE_URL = "https://animepahe.ru"
API_URL  = f"{BASE_URL}/api"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": BASE_URL,
    "Cookie": "__ddg1_=;__ddg2_=",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _get(url, params=None, retries=3) -> Optional[requests.Response]:
    for attempt in range(retries):
        try:
            r = SESSION.get(url, params=params, timeout=15)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))


# ── Search ────────────────────────────────────────────────────────────────────

def search(query: str) -> list[dict]:
    data = _get(API_URL, params={"m": "search", "q": query}).json()
    results = []
    for item in data.get("data", []):
        sid = item.get("session", "")
        results.append({
            "id": sid,
            "title": item.get("title", "Unknown"),
            "url": f"{BASE_URL}/anime/{sid}",
            "thumbnail": item.get("poster", ""),
            "status": item.get("status", ""),
            "type": item.get("type", ""),
            "year": str(item.get("year", "")),
            "episodes": item.get("episodes", 0),
            "source": "animepahe",
        })
    return results


# ── Episodes ──────────────────────────────────────────────────────────────────

def get_episodes(anime_session: str, page=1) -> tuple[list[dict], int]:
    data = _get(API_URL, params={
        "m": "release", "id": anime_session,
        "sort": "episode_asc", "page": page,
    }).json()

    total_pages = data.get("last_page", 1)
    episodes = []
    for item in data.get("data", []):
        ep_session = item.get("session", "")
        episodes.append({
            "number": str(item.get("episode", "?")),
            "title": f"Episode {item.get('episode', '?')}",
            "session": ep_session,
            "url": f"{BASE_URL}/play/{anime_session}/{ep_session}",
            "thumbnail": item.get("snapshot", ""),
            "duration": item.get("duration", ""),
            "source": "animepahe",
        })
    return episodes, total_pages


def get_all_episodes(anime_session: str) -> list[dict]:
    eps, total = get_episodes(anime_session, page=1)
    for p in range(2, total + 1):
        more, _ = get_episodes(anime_session, page=p)
        eps.extend(more)
        time.sleep(0.4)
    return eps


# ── Download links ────────────────────────────────────────────────────────────

def get_download_links(anime_session: str, ep_session: str) -> list[dict]:
    """
    Parses the play page for kwik buttons.
    Each button has: data-src (kwik URL), data-resolution, data-audio (jpn/eng).
    Returns list sorted by resolution descending.
    """
    play_url = f"{BASE_URL}/play/{anime_session}/{ep_session}"
    html = _get(play_url).text
    links = []

    # Primary pattern — button elements
    for m in re.finditer(
        r'<button[^>]+data-src="([^"]+)"[^>]+data-resolution="([^"]+)"[^>]*data-audio="([^"]+)"',
        html,
    ):
        kwik_url, resolution, audio = m.group(1), m.group(2), m.group(3)
        links.append({
            "quality": f"{resolution}p",
            "url": kwik_url,
            "audio": audio,           # "jpn" or "eng"
            "has_subs": audio == "jpn",  # jpn audio = subtitled
            "server": "kwik",
            "source": "animepahe",
            "_resolution": int(resolution) if resolution.isdigit() else 0,
        })

    # Fallback — bare kwik anchor tags
    if not links:
        for m in re.finditer(r'href="(https://kwik\.[a-z]+/[^"]+)"', html):
            links.append({
                "quality": "unknown",
                "url": m.group(1),
                "audio": "jpn",
                "has_subs": True,
                "server": "kwik",
                "source": "animepahe",
                "_resolution": 0,
            })

    # Sort best quality first
    links.sort(key=lambda x: x.get("_resolution", 0), reverse=True)
    return links


# ── Kwik resolver ─────────────────────────────────────────────────────────────

def resolve_kwik(kwik_url: str) -> Optional[str]:
    """
    Resolve kwik.si URL → direct .mp4 / .m3u8 URL.
    Kwik requires a POST with a CSRF token extracted from the page.
    """
    resp = _get(kwik_url)
    html = resp.text

    action = re.search(r'action="([^"]+)"', html)
    token  = re.search(r'name="_token"\s+value="([^"]+)"', html)

    if not action or not token:
        src = re.search(r"source='([^']+)'", html)
        return src.group(1) if src else None

    post_headers = {
        **HEADERS,
        "Referer": kwik_url,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    try:
        r = SESSION.post(
            action.group(1),
            data={"_token": token.group(1)},
            headers=post_headers,
            allow_redirects=False,
            timeout=15,
        )
        if r.status_code in (301, 302):
            return r.headers.get("Location")
        src = re.search(r"source='([^']+)'", r.text)
        if src:
            return src.group(1)
    except Exception:
        pass
    return None
