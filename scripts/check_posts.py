"""Check posts before publishing. Exit 1 if any post breaks the rules.

    python scripts/check_posts.py              # all posts
    python scripts/check_posts.py FILE [FILE]  # only these
    python scripts/check_posts.py --online FILE  # also open the image / video URLs

--online: the thumbnail must return an image and the YouTube video must exist
(checked through YouTube's oEmbed). A post with neither prints a warning, not an error.
"""
from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import yaml

from regions import REGIONS, outside_heading

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = {"phones", "pc", "gaming", "audio", "home", "weird"}
AVAILABILITY = {"home-only", "import", "global"}
REQUIRED = ["title", "slug", "date", "category", "summary", "origin", "availability", "sources"]
UA = "GadgetTerminalEN-check/1.0 (+https://en.gadgetterminal.com/)"


def fetch_ok(url: str, want: str) -> tuple[bool, str]:
    """Return (ok, reason). want: 'image' or 'json'."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=20) as r:
            ctype = r.headers.get("Content-Type", "")
            if want == "image" and not ctype.startswith("image/"):
                return False, f"not an image ({ctype or 'no content type'})"
            return True, ""
    except Exception as e:  # noqa: BLE001
        return False, str(e)[:80]


def check_online(fm: dict) -> list[str]:
    errs = []
    if fm.get("thumbnail"):
        ok, why = fetch_ok(str(fm["thumbnail"]), "image")
        if not ok:
            errs.append(f"thumbnail does not load: {why}")
    vid = str(fm.get("video") or "")
    if vid:
        q = urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}", safe="")
        ok, why = fetch_ok(f"https://www.youtube.com/oembed?url={q}&format=json", "json")
        if not ok:
            errs.append(f"video {vid} not found on YouTube: {why}")
    return errs


def check(path: Path, online: bool = False) -> list[str]:
    errs: list[str] = []
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        return ["front matter is missing"]
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        return [f"front matter YAML is broken: {e}"]
    body = m.group(2)

    for k in REQUIRED:
        if not fm.get(k):
            errs.append(f"missing {k}")
    if fm.get("category") and fm["category"] not in CATEGORIES:
        errs.append(f"bad category {fm['category']}")
    if fm.get("origin") and str(fm["origin"]).lower() not in REGIONS:
        errs.append(f"bad origin {fm['origin']} (use a code from scripts/regions.py)")
    if fm.get("availability") and fm["availability"] not in AVAILABILITY:
        errs.append(f"bad availability {fm['availability']}")
    slug = str(fm.get("slug", ""))
    if slug and not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", slug):
        errs.append(f"bad slug {slug}")
    if slug and not path.stem.endswith(slug):
        errs.append("file name does not end with the slug")
    for s in fm.get("sources") or []:
        if not (isinstance(s, dict) and str(s.get("url", "")).startswith("http")):
            errs.append(f"bad source {s}")
    if fm.get("thumbnail") and not fm.get("thumbnail_credit"):
        errs.append("thumbnail without thumbnail_credit")
    if fm.get("video"):
        if not re.fullmatch(r"[A-Za-z0-9_-]{11}", str(fm["video"])):
            errs.append(f"bad video id {fm['video']} (use the 11-character YouTube ID)")
        if not fm.get("video_credit"):
            errs.append("video without video_credit")
    if online:
        errs += check_online(fm)

    outside = outside_heading(fm)
    if outside not in body:
        errs.append(f"missing section '{outside}'")
    if "!" in re.sub(r"!\[|<!--|!=", "", body) or "!" in str(fm.get("title", "")):
        errs.append("exclamation mark")
    if re.search(r"[぀-ヿ]", body + str(fm.get("title", ""))):
        errs.append("Japanese kana in an English post")
    words = len(re.findall(r"[A-Za-z]+", body))
    if words < 250:
        errs.append(f"too short ({words} words)")
    if re.search(r"\b(yuan|yen|won|rupees?|baht|dong|ringgit|pesos?)\b", body, re.I) and \
            re.search(r"\(\s*(about|approx\.?|~)\s*\$", body, re.I):
        errs.append("local price converted to dollars")
    return errs


def main() -> int:
    args = sys.argv[1:]
    online = "--online" in args
    files = [Path(a) for a in args if a != "--online"] or sorted((ROOT / "content" / "posts").glob("*.md"))
    bad = 0
    for f in files:
        errs = check(f, online)
        if errs:
            bad += 1
            print(f"NG {f.name}: " + "; ".join(errs))
        else:
            print(f"OK {f.name}")
        text = f.read_text(encoding="utf-8")
        if not re.search(r"^(thumbnail|video):\s*\S", text.split("\n---", 1)[0], re.M):
            print(f"   warning: {f.name} has no photo or video")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
