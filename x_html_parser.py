from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from bs4 import BeautifulSoup


_WS_RE = re.compile(r"\s+")
_STATUS_RE = re.compile(r"/status/(\d+)")


def _norm_text(s: str) -> str:
    return _WS_RE.sub(" ", (s or "").replace("\u200b", " ").strip()).strip()


def _first(iterable: Iterable[str], pred) -> Optional[str]:
    for x in iterable:
        if pred(x):
            return x
    return None


@dataclass(frozen=True)
class ProfileInfo:
    name: str = ""
    handle: str = ""
    description: str = ""
    profile_url: str = ""
    user_id: str = ""
    follows: Optional[int] = None
    following: Optional[int] = None
    tweets: Optional[int] = None


def parse_profile_info(soup: BeautifulSoup) -> ProfileInfo:
    script = soup.select_one('script[data-testid="UserProfileSchema-test"]')
    if not script:
        return ProfileInfo()

    raw = (script.string or "").strip()
    if not raw:
        return ProfileInfo()

    try:
        obj = json.loads(raw)
    except Exception:
        return ProfileInfo()

    entity = (obj or {}).get("mainEntity") or {}
    stats = entity.get("interactionStatistic") or []
    stats_map: Dict[str, Optional[int]] = {}
    for it in stats:
        name = (it or {}).get("name")
        count = (it or {}).get("userInteractionCount")
        if name and isinstance(count, (int, float)):
            stats_map[name] = int(count)

    handle = _norm_text(str(entity.get("additionalName") or ""))
    if handle and not handle.startswith("@"):
        handle = "@" + handle

    return ProfileInfo(
        name=_norm_text(str(entity.get("name") or "")),
        handle=handle,
        description=_norm_text(str(entity.get("description") or "")),
        profile_url=_norm_text(str(entity.get("url") or "")),
        user_id=_norm_text(str(entity.get("identifier") or "")),
        follows=stats_map.get("Follows"),
        following=stats_map.get("Friends"),
        tweets=stats_map.get("Tweets"),
    )


def _extract_status_url(tweet_el) -> Tuple[str, str]:
    hrefs = []
    for a in tweet_el.select('a[href*="/status/"]'):
        href = a.get("href") or ""
        if not href:
            continue
        if "/photo/" in href or "/video/" in href:
            continue
        href = href.split("?", 1)[0]
        hrefs.append(href)

    href = hrefs[0] if hrefs else ""
    status_id = ""
    m = _STATUS_RE.search(href)
    if m:
        status_id = m.group(1)

    full = f"https://x.com{href}" if href.startswith("/") else href
    return full, status_id


def _extract_user(tweet_el) -> Tuple[str, str]:
    user_block = tweet_el.select_one('[data-testid="User-Name"]')
    if not user_block:
        return "", ""

    parts = [_norm_text(x) for x in user_block.stripped_strings]
    parts = [p for p in parts if p and p != "·"]

    handle = _first(parts, lambda x: x.startswith("@")) or ""
    name = _first(parts, lambda x: not x.startswith("@")) or ""
    return name, handle


def _extract_datetime(tweet_el) -> Tuple[str, str]:
    t = tweet_el.find("time")
    if not t:
        return "", ""
    dt = (t.get("datetime") or "").strip()
    display = _norm_text(t.get_text(" ", strip=True))
    if dt:
        try:
            iso = datetime.fromisoformat(dt.replace("Z", "+00:00")).isoformat()
        except Exception:
            iso = dt
    else:
        iso = ""
    return iso, display


def _extract_text(tweet_el) -> str:
    txt = tweet_el.select_one('[data-testid="tweetText"]')
    if not txt:
        return ""
    return _norm_text(txt.get_text(" ", strip=True))


def _extract_hashtags_mentions(tweet_el) -> Tuple[List[str], List[str]]:
    txt = tweet_el.select_one('[data-testid="tweetText"]')
    if not txt:
        return [], []

    hashtags: List[str] = []
    mentions: List[str] = []
    for a in txt.select("a"):
        href = (a.get("href") or "").strip()
        label = _norm_text(a.get_text(" ", strip=True))
        if not label:
            continue
        if "/hashtag/" in href or label.startswith("#"):
            if label.startswith("#"):
                hashtags.append(label)
            else:
                hashtags.append("#" + label.lstrip("#"))
        if "/@" in href or label.startswith("@"):
            if label.startswith("@"):
                mentions.append(label)
            else:
                mentions.append("@" + label.lstrip("@"))

    def _dedupe(xs: List[str]) -> List[str]:
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return _dedupe(hashtags), _dedupe(mentions)


def _extract_media_urls(tweet_el) -> List[str]:
    urls: List[str] = []

    for img in tweet_el.select('[data-testid="tweetPhoto"] img'):
        src = (img.get("src") or "").strip()
        if src:
            urls.append(src)

    for div in tweet_el.select('[data-testid="tweetPhoto"]'):
        style = (div.get("style") or "").strip()
        if "url(" in style:
            m = re.search(r'url\\(["\\\']?(.*?)["\\\']?\\)', style)
            if m:
                urls.append(m.group(1))

    seen = set()
    out = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def parse_x_profile_html(html: str) -> Tuple[ProfileInfo, List[Dict[str, Any]]]:
    soup = BeautifulSoup(html, "lxml")
    profile = parse_profile_info(soup)

    tweets: List[Dict[str, Any]] = []
    for el in soup.select('[data-testid="tweet"]'):
        status_url, status_id = _extract_status_url(el)
        author_name, author_handle = _extract_user(el)
        created_at_iso, created_at_display = _extract_datetime(el)
        text = _extract_text(el)
        hashtags, mentions = _extract_hashtags_mentions(el)
        media_urls = _extract_media_urls(el)

        if not (status_url or text or created_at_iso):
            continue

        tweets.append(
            {
                "profile_name": profile.name,
                "profile_handle": profile.handle,
                "profile_description": profile.description,
                "profile_url": profile.profile_url,
                "profile_user_id": profile.user_id,
                "profile_follows": profile.follows,
                "profile_following": profile.following,
                "profile_tweets": profile.tweets,
                "tweet_id": status_id,
                "tweet_url": status_url,
                "tweet_created_at": created_at_iso,
                "tweet_created_at_display": created_at_display,
                "tweet_author_name": author_name,
                "tweet_author_handle": author_handle,
                "tweet_text": text,
                "tweet_hashtags": ",".join(hashtags),
                "tweet_mentions": ",".join(mentions),
                "tweet_media_urls": "|".join(media_urls),
            }
        )

    return profile, tweets


def parse_x_profile_html_file(path: str) -> Tuple[ProfileInfo, List[Dict[str, Any]]]:
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        html = f.read()
    return parse_x_profile_html(html)
