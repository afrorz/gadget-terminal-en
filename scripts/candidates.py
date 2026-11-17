"""Pick China-related candidates from the Japanese GT digest.

The Japanese edition (afrorz/gadget-terminal, public) collects ~30 items every
morning into data/digest/YYYY-MM-DD.json. This script reads the latest two days,
keeps items about Chinese brands or from Chinese sources, drops items already
covered by an English post, and writes data/candidates.md for the writer.

    python scripts/candidates.py            # fetch from GitHub
    python scripts/candidates.py --local ../GadgetTerminal   # read a local checkout
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = "https://raw.githubusercontent.com/afrorz/gadget-terminal/main/data/digest/{d}.json"
JST = dt.timezone(dt.timedelta(hours=9))

CN_SOURCES = {"ithome_cn", "gizmochina", "huaweicentral"}
CN_WORDS = re.compile(
    r"\b(China|Chinese|Xiaomi|Redmi|POCO|Huawei|Honor|OPPO|vivo|iQOO|realme|OnePlus|Meizu|ZTE|"
    r"nubia|RedMagic|Red Magic|Lenovo|Legion|Ayaneo|AYANEO|GPD|Anbernic|Retroid|AYN|MOONDROP|"
    r"FiiO|Dreame|Roborock|Ecovacs|DJI|Insta360|Ugreen|UGREEN|Baseus|Anker|Mijia|Youpin|"
    r"Tencent|Alibaba|Baidu|ByteDance|Pico|Unitree|Tecno|Infinix|itel|Transsion|Black Shark|"
    r"Ulefone|Doogee|Oukitel|Blackview|Minisforum|Beelink|Chuwi|Teclast|Thunderobot|Mechrevo|"
    r"MagicBook|MatePad|MateBook|HarmonyOS)\b",
    re.I,
)
KANA = re.compile(r"[぀-ヿ]")
SKIP_SOURCES = {"makuake"}
SKIP_WORDS = re.compile(r"\b(deal|save \$|\d+% off|record low|discount|coupon)\b", re.I)


def load_digest(day: dt.date, local: Path | None) -> list[dict]:
    d = day.isoformat()
    try:
        if local:
            p = local / "data" / "digest" / f"{d}.json"
            if not p.exists():
                return []
            data = json.loads(p.read_text(encoding="utf-8"))
        else:
            with urllib.request.urlopen(RAW.format(d=d), timeout=30) as r:
                data = json.loads(r.read().decode("utf-8"))
    except Exception as e:  # noqa: BLE001 - a missing day is normal
        print(f"skip {d}: {e}", file=sys.stderr)
        return []
    for it in data.get("items", []):
        it["_digest"] = d
    return data.get("items", [])


# Sites that refuse WebFetch but publish full article text in their RSS feed.
# Reading the feed is the intended machine-readable route, so we use that instead.
FULLTEXT_FEEDS = ["https://www.gizmochina.com/feed/"]


def feed_fulltext() -> dict[str, str]:
    """Map article URL -> plain text from RSS <content:encoded>."""
    import html
    import xml.etree.ElementTree as ET

    out: dict[str, str] = {}
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    for feed in FULLTEXT_FEEDS:
        try:
            req = urllib.request.Request(feed, headers={"User-Agent": "GadgetTerminalEN-feedreader/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                root = ET.fromstring(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"feed {feed}: {e}", file=sys.stderr)
            continue
        for item in root.iter("item"):
            link = (item.findtext("link") or "").strip().rstrip("/")
            body = item.findtext("content:encoded", default="", namespaces=ns)
            text = html.unescape(re.sub(r"<[^>]+>", " ", body))
            text = re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", text)).strip()
            if link and text:
                out[link] = text
    return out


def covered_urls() -> set[str]:
    urls: set[str] = set()
    for f in (ROOT / "content" / "posts").glob("*.md"):
        urls.update(u.rstrip("/") for u in re.findall(r"url:\s*\"?(\S+?)\"?\s*$", f.read_text(encoding="utf-8"), re.M))
    return urls


def is_china(it: dict) -> bool:
    if it.get("source_id") in CN_SOURCES:
        return True
    if it.get("source_id") in SKIP_SOURCES or KANA.search(it.get("title", "")):
        return False  # Japanese crowdfunding pages are the Japanese edition's beat
    return bool(CN_WORDS.search(f"{it.get('title', '')} {it.get('summary', '')}"))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", type=Path)
    ap.add_argument("--out", type=Path, default=ROOT / "data" / "candidates.md")
    a = ap.parse_args()

    today = dt.datetime.now(JST).date()
    items = load_digest(today, a.local) + load_digest(today - dt.timedelta(days=1), a.local)
    done = covered_urls()
    seen, picked = set(), []
    for it in items:
        urls = [it.get("url", ""), it.get("canonical", "")] + list(it.get("related_urls") or [])
        if any(u and u.rstrip("/") in done for u in urls):
            continue
        key = (it.get("canonical") or it.get("url", "")).rstrip("/")
        if key in seen or not is_china(it) or SKIP_WORDS.search(it.get("title", "")):
            continue
        seen.add(key)
        picked.append(it)
    picked.sort(key=lambda x: (x["_digest"], x.get("score", 0)), reverse=True)

    full = feed_fulltext()
    ftdir = a.out.parent / "fulltext"
    ftdir.mkdir(parents=True, exist_ok=True)

    lines = [f"# Candidates {today.isoformat()} ({len(picked)} items)", ""]
    for i, it in enumerate(picked, 1):
        lines += [
            f"## {i}. {it.get('title', '').strip()}",
            f"- source: {it.get('source')} / digest {it['_digest']} / score {it.get('score')}",
            f"- url: {it.get('url')}",
        ]
        body = full.get((it.get("url") or "").rstrip("/"))
        if body:
            fp = ftdir / f"{it.get('id', i)}.txt"
            fp.write_text(body, encoding="utf-8")
            lines.append(f"- fulltext (from the site's RSS feed): {fp.relative_to(ROOT).as_posix()}")
        for u in it.get("related_urls") or []:
            lines.append(f"- related: {u}")
        lines += [f"- summary: {(it.get('summary') or '').strip()[:400]}", ""]
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(picked)} candidates -> {a.out}")


if __name__ == "__main__":
    main()
