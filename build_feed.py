#!/usr/bin/env python3
"""Build a personal podcast feed of today's NPR Morning Edition stories.

Each story becomes one episode whose audio streams straight from NPR's own
servers (nothing is re-hosted). Episodes are dated so that, within a day, they
play in broadcast order. Safe to run several times a morning: new stories are
added, existing ones are kept, and the feed keeps the last few days.

Usage: python build_feed.py [--date YYYY-MM-DD] [--out docs]
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")
PROGRAM_URL = "https://www.npr.org/programs/morning-edition/"
ARCHIVE_URL = "https://www.npr.org/programs/morning-edition/archive?date={m}-{d}-{y}"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
KEEP_DAYS = int(os.environ.get("KEEP_DAYS", "3"))
FEED_TITLE = os.environ.get("FEED_TITLE", "My Morning Edition")
SITE_URL = os.environ.get("SITE_URL", "")  # e.g. https://you.github.io/npr-me-feed


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


# ---------------------------------------------------------------- parsing
DATA_AUDIO_RE = re.compile(r"""data-audio\s*=\s*(['"])(.*?)\1""", re.S)
MP3_RE = re.compile(r"""https?://[^\s"'<>]+?\.mp3(?:\?[^\s"'<>]*)?""")
EPISODE_LINK_RE = re.compile(
    r"""https?://www\.npr\.org/programs/morning-edition/(\d{4})/(\d{2})/(\d{2})/\d+/[^"'\s<>]*""")


def _clean_url(u: str) -> str:
    return html.unescape(u).replace("\\/", "/")


def _key(u: str) -> str:
    """Identity of an audio file, ignoring tracking query strings."""
    return _clean_url(u).split("?")[0].lower()


def _is_me_audio(u: str, ymd: str) -> bool:
    k = _key(u)
    return ymd in k and ("/me/" in k or f"{ymd}_me_" in k)


def parse_stories(page: str, day: dt.date) -> list[dict]:
    """Return today's stories in page order: [{title, audio, story_url, duration}]."""
    ymd = day.strftime("%Y%m%d")
    stories: dict[str, dict] = {}

    # Strategy 1: JSON in data-audio attributes on play buttons.
    for _, raw in DATA_AUDIO_RE.findall(page):
        try:
            data = json.loads(html.unescape(raw))
        except ValueError:
            continue
        url = data.get("audioUrl") or data.get("url") or ""
        if not url or not _is_me_audio(url, ymd):
            continue
        k = _key(url)
        if k not in stories:
            stories[k] = {
                "title": (data.get("title") or "").strip(),
                "audio": _clean_url(url),
                "story_url": _clean_url(data.get("storyUrl") or data.get("link") or ""),
                "duration": int(data.get("duration") or 0),
            }

    # Strategy 2: any Morning Edition MP3 link, titled from the nearest heading before it.
    for m in MP3_RE.finditer(page):
        url = m.group(0)
        if not _is_me_audio(url, ymd) or _key(url) in stories:
            continue
        before = page[max(0, m.start() - 6000):m.start()]
        heads = re.findall(r"<h[1-4][^>]*>(.*?)</h[1-4]>", before, re.S)
        title = re.sub(r"<[^>]+>", "", heads[-1]).strip() if heads else ""
        stories[_key(url)] = {"title": html.unescape(title), "audio": _clean_url(url),
                              "story_url": "", "duration": 0}

    out = list(stories.values())
    for i, s in enumerate(out, 1):
        if not s["title"]:
            slug = s["audio"].split("?")[0].rsplit("/", 1)[-1].rsplit(".", 1)[0]
            slug = re.sub(rf"^{ymd}_me_", "", slug)
            s["title"] = slug.replace("_", " ").replace("-", " ").strip().capitalize() or f"Story {i}"
    return out


def find_today_page(day: dt.date) -> str | None:
    """Fetch the program page; fall back to the date archive to find today's episode."""
    main = fetch(PROGRAM_URL)
    if parse_stories(main, day):  # only counts audio dated today
        return main
    archive = fetch(ARCHIVE_URL.format(m=f"{day.month:02d}", d=f"{day.day:02d}", y=day.year))
    want = (f"{day.year}", f"{day.month:02d}", f"{day.day:02d}")
    for m in EPISODE_LINK_RE.finditer(archive):
        if m.group(1, 2, 3) == want:
            return fetch(html.unescape(m.group(0)))
    return None


# ---------------------------------------------------------------- feed
def build_rss(items: list[dict], site: str) -> str:
    now = format_datetime(dt.datetime.now(dt.timezone.utc))
    art = f"{site}/cover.png" if site else ""
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd">',
        "<channel>",
        f"<title>{escape(FEED_TITLE)}</title>",
        f"<link>{escape(site or 'https://www.npr.org/programs/morning-edition/')}</link>",
        "<description>Personal feed of today's NPR Morning Edition stories, "
        "linked to NPR's own audio.</description>",
        "<language>en-us</language>",
        f"<lastBuildDate>{now}</lastBuildDate>",
        "<itunes:block>Yes</itunes:block>",
    ]
    if art:
        parts.append(f'<itunes:image href="{escape(art)}"/>')
    for it in items:
        pub = format_datetime(dt.datetime.fromisoformat(it["pub"]))
        desc = it.get("story_url") or ""
        parts += [
            "<item>",
            f"<title>{escape(it['episode_title'])}</title>",
            f'<guid isPermaLink="false">{escape(it["guid"])}</guid>',
            f"<pubDate>{pub}</pubDate>",
            f'<enclosure url="{escape(it["audio"])}" length="0" type="audio/mpeg"/>',
            f"<description>{escape(desc)}</description>",
        ]
        if it.get("story_url"):
            parts.append(f"<link>{escape(it['story_url'])}</link>")
        if it.get("duration"):
            parts.append(f"<itunes:duration>{it['duration']}</itunes:duration>")
        parts.append("</item>")
    parts += ["</channel>", "</rss>", ""]
    return "\n".join(parts)


def merge(state: list[dict], day: dt.date, stories: list[dict]) -> list[dict]:
    known = {s["guid"] for s in state}
    base = dt.datetime.combine(day, dt.time(5, 0), tzinfo=ET)
    todays = [s for s in state if s["day"] == day.isoformat()]
    n = len(todays)
    for s in stories:
        guid = _key(s["audio"])
        if guid in known:
            continue
        n += 1
        state.append({
            "guid": guid, "day": day.isoformat(), "seq": n,
            "episode_title": f"{day.strftime('%a %b')} {day.day} · {n:02d} · {s['title']}",
            "audio": s["audio"], "story_url": s["story_url"], "duration": s["duration"],
            # one minute apart, in broadcast order
            "pub": (base + dt.timedelta(minutes=n)).isoformat(),
        })
        known.add(guid)
    cutoff = (day - dt.timedelta(days=KEEP_DAYS - 1)).isoformat()
    state = [s for s in state if s["day"] >= cutoff]
    state.sort(key=lambda s: s["pub"], reverse=True)  # newest first, as feeds expect
    return state


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today in US Eastern)")
    ap.add_argument("--out", default="docs")
    a = ap.parse_args()
    day = dt.date.fromisoformat(a.date) if a.date else dt.datetime.now(ET).date()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    state_path = out / "state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else []

    page = find_today_page(day)
    stories = parse_stories(page, day) if page else []
    print(f"{day}: found {len(stories)} Morning Edition stories")
    for s in stories:
        print("  -", s["title"])

    state = merge(state, day, stories)
    state_path.write_text(json.dumps(state, indent=1))
    (out / "feed.xml").write_text(build_rss(state, SITE_URL.rstrip("/")))
    if not stories:
        print("No stories yet for today; feed left with earlier days.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
