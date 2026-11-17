"""Check posts before publishing. Exit 1 if any post breaks the rules.

    python scripts/check_posts.py              # all posts
    python scripts/check_posts.py FILE [FILE]  # only these
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CATEGORIES = {"phones", "pc", "gaming", "audio", "home", "weird"}
AVAILABILITY = {"china-only", "import", "global"}
REQUIRED = ["title", "slug", "date", "category", "summary", "availability", "sources"]
OUTSIDE = "## Can you get it outside China?"


def check(path: Path) -> list[str]:
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

    if OUTSIDE not in body:
        errs.append(f"missing section '{OUTSIDE}'")
    if "!" in re.sub(r"!\[|<!--|!=", "", body) or "!" in str(fm.get("title", "")):
        errs.append("exclamation mark")
    if re.search(r"[぀-ヿ]", body + str(fm.get("title", ""))):
        errs.append("Japanese kana in an English post")
    words = len(re.findall(r"[A-Za-z]+", body))
    if words < 250:
        errs.append(f"too short ({words} words)")
    if re.search(r"\byuan\b", body, re.I) and re.search(r"\(\s*(about|approx\.?|~)\s*\$", body, re.I):
        errs.append("yuan converted to dollars")
    return errs


def main() -> int:
    files = [Path(a) for a in sys.argv[1:]] or sorted((ROOT / "content" / "posts").glob("*.md"))
    bad = 0
    for f in files:
        errs = check(f)
        if errs:
            bad += 1
            print(f"NG {f.name}: " + "; ".join(errs))
        else:
            print(f"OK {f.name}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
