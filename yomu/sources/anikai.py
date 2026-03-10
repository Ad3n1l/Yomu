"""
yomu · sources/anikai.py
Scraper for anikai.to — search, episode list, download link extraction.
"""

import re
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Optional

BASE_URL = "https://anikai.to"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": BASE_URL,
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


def search(query: str) -> list[dict]:
    resp = _get(f"{BASE_URL}/search", params={"keyword": query})
    soup = BeautifulSoup(resp.text, "lxml")
    results = []

    for card in soup.select(".film-poster, .flw-item, .item"):
        try:
            a = card.select_one("a[href]")
            if not a:
                continue
            href = a["href"]
            title_el = card.select_one(".film-name, .dynamic-name, h3, .name")
            title = title_el.get_text(strip=True) if title_el else a.get("title", "Unknown")
            thumb_el = card.select_one("img")
            thumb = (thumb_el.get("data-src") or thumb_el.get("src", "")) if thumb_el else ""
            anime_id = href.rstrip("/").split("/")[-1]
            status = ""
            for badge in card.select(".fdi-item, .tick, .status"):
                status = badge.get_text(strip=True)
                break
            results.append({
                "id": anime_id,
                "title": title,
                "url": urljoin(BASE_URL, href),
                "thumbnail": thumb,
                "status": status,
                "type": "",
                "year": "",
                "source": "anikai",
            })
        except Exception:
            continue
    return results


def get_episodes(anime_id: str) -> list[dict]:
    resp = _get(f"{BASE_URL}/{anime_id}")
    soup = BeautifulSoup(resp.text, "lxml")
    episodes = []

    ep_list = soup.select(
        "#episodes-content .ep-item, .episodes-ul .ep-item, .episode-list li a"
    ) or soup.select("a[href*='/episode'], a[href*='/ep-']")

    for ep in ep_list:
        href = ep.get("href", "")
        if not href:
            continue
        num_el = ep.select_one(".ssli-order") or ep
        num_text = num_el.get_text(strip=True) or ep.get("data-number", "?")
        title_el = ep.select_one(".ep-name")
        ep_title = title_el.get_text(strip=True) if title_el else f"Episode {num_text}"

        # anikai.to labels dub links in the href or button text
        audio = "eng" if "dub" in href.lower() or "dub" in ep_title.lower() else "jpn"

        episodes.append({
            "number": num_text,
            "title": ep_title,
            "url": urljoin(BASE_URL, href),
            "episode_id": href.rstrip("/").split("/")[-1],
            "audio": audio,
            "source": "anikai",
        })

    def sort_key(ep):
        try:
            return float(re.findall(r"[\d.]+", str(ep["number"]))[0])
        except Exception:
            return 0

    episodes.sort(key=sort_key)
    return episodes


def get_download_links(episode_url: str) -> list[dict]:
    """
    Returns list of {quality, url, audio, server, has_subs}.
    Tries to detect sub/dub from button labels and data attributes.
    """
    resp = _get(episode_url)
    soup = BeautifulSoup(resp.text, "lxml")
    links = []

    for btn in soup.select(
        ".server-item a, .download-btn a, .downloadsave a, "
        "a[href*='.mp4'], a[href*='download'], a[href*='googlevideo']"
    ):
        href = btn.get("href", "")
        if not href or href == "#":
            continue
        label = btn.get_text(strip=True).lower()
        quality = btn.get("data-quality", "")
        server  = btn.get("data-server", btn.get("data-id", ""))
        audio   = "eng" if "dub" in label else "jpn"
        has_subs = "sub" in label or "cc" in label

        if not quality:
            q_match = re.search(r"(\d{3,4})p", label)
            quality = f"{q_match.group(1)}p" if q_match else "unknown"

        links.append({
            "quality": quality,
            "url": href,
            "audio": audio,
            "has_subs": has_subs,
            "server": server,
            "source": "anikai",
        })

    # Inline JS source blobs
    for script in soup.find_all("script"):
        raw = script.string or ""
        for m in re.finditer(r'\{[^{}]*"file"\s*:\s*"(https?://[^"]+)"[^{}]*\}', raw):
            url = m.group(1)
            quality_m = re.search(r'"label"\s*:\s*"([^"]+)"', m.group(0))
            links.append({
                "quality": quality_m.group(1) if quality_m else "unknown",
                "url": url,
                "audio": "jpn",
                "has_subs": False,
                "server": "embedded",
                "source": "anikai",
            })

    return links
