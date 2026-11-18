"""Collect candidates for the writer: gadgets that launch in one country or region.

1. China: the Japanese edition (afrorz/gadget-terminal, public) collects ~30 items
   every morning into data/digest/YYYY-MM-DD.json. We read the latest two days and
   keep items about Chinese brands or from Chinese sources.
2. Japan, South Korea, the rest of Asia and Europe: we read local news feeds
   (REGION_FEEDS) directly, newest first, a few per feed.

Items already covered by an English post are dropped. Output: data/candidates.md.

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


# Local-language feeds for launches outside China. (region, name, url[, must])
# must: a regex the title has to match (for general news feeds, keep only launches).
KR_LAUNCH = r"(출시|공개|선보|신제품|사전\s?예약|판매\s?시작)"
REGION_FEEDS = [
    ("jp", "Kaden Watch", "https://kaden.watch.impress.co.jp/data/rss/1.0/kdw/feed.rdf"),
    ("jp", "PC Watch", "https://pc.watch.impress.co.jp/data/rss/1.0/pcw/feed.rdf"),
    ("jp", "AV Watch", "https://av.watch.impress.co.jp/data/rss/1.0/avw/feed.rdf"),
    ("jp", "k-tai Watch", "https://k-tai.watch.impress.co.jp/data/rss/1.0/ktw/feed.rdf"),
    ("jp", "ITmedia (products)", "https://rss.itmedia.co.jp/rss/2.0/news_products.xml"),
    ("kr", "Samsung Newsroom Korea", "https://news.samsung.com/kr/feed"),
    ("kr", "ZDNet Korea", "https://feeds.feedburner.com/zdkorea", KR_LAUNCH),
    ("kr", "ETNews", "https://www.etnews.com/rss/Section901.xml", KR_LAUNCH),
    ("kr", "IT Chosun", "https://it.chosun.com/rss/allArticle.xml", KR_LAUNCH),
    ("in", "Fone Arena", "https://www.fonearena.com/blog/feed"),
    ("eu", "golem.de", "https://www.golem.de/rss.php?feed=RSS2.0"),
    ("eu", "ComputerBase", "https://www.computerbase.de/rss/news.xml"),
    ("eu", "Frandroid", "https://www.frandroid.com/feed"),
    ("eu", "Les Numeriques", "https://www.lesnumeriques.com/rss.xml"),
    ("eu", "Tweakers", "https://tweakers.net/feeds/mixed.xml"),
]
PER_FEED = 8
REGION_NAMES = {"cn": "China", "jp": "Japan", "kr": "South Korea", "in": "India / rest of Asia", "eu": "Europe"}
LOCAL_SKIP = re.compile(
    r"(セール|お買い得|円引き|円オフ|オフに|ランキング|割引|値下げ|クーポン|ポイント還元|特価|할인|특가|Angebot|Deal|Rabatt|promo|soldes|"
    r"bon plan|Black Friday|Cyber Monday|aanbieding)", re.I)


def _text(el, *names: str) -> str:
    for n in names:
        found = el.find(n)
        if found is not None and (found.text or "").strip():
            return found.text.strip()
        if found is not None and found.get("href"):
            return found.get("href")
    return ""


def _when(s: str) -> dt.datetime | None:
    from email.utils import parsedate_to_datetime
    if not s:
        return None
    try:
        d = parsedate_to_datetime(s)
    except (TypeError, ValueError):
        try:
            d = dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except ValueError:
            return None
    return d if d.tzinfo else d.replace(tzinfo=dt.timezone.utc)


def region_items(now: dt.datetime) -> list[dict]:
    """Newest items from REGION_FEEDS (RSS 1.0, RSS 2.0 or Atom), last 2 days."""
    import html
    import xml.etree.ElementTree as ET

    out: list[dict] = []
    for region, name, url, *must in REGION_FEEDS:
        must_re = re.compile(must[0]) if must else None
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "GadgetTerminalEN-feedreader/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                root = ET.fromstring(r.read())
        except Exception as e:  # noqa: BLE001
            print(f"feed {name}: {e}", file=sys.stderr)
            continue
        for el in root.iter():  # strip namespaces so one parser reads all three formats
            if "}" in el.tag:
                el.tag = el.tag.split("}", 1)[1]
        n = 0
        for it in [*root.iter("item"), *root.iter("entry")]:
            title = html.unescape(_text(it, "title"))
            link = _text(it, "link")
            when = _when(_text(it, "pubDate", "date", "updated", "published"))
            if not title or not link or LOCAL_SKIP.search(title) or (must_re and not must_re.search(title)):
                continue
            if when and now - when > dt.timedelta(days=2):
                continue
            summary = html.unescape(re.sub(r"<[^>]+>", " ", _text(it, "description", "summary", "encoded")))
            out.append({"title": title, "url": link, "source": name, "region": region,
                        "summary": re.sub(r"\s+", " ", summary).strip(),
                        "_digest": (when or now).astimezone(JST).date().isoformat()})
            n += 1
            if n >= PER_FEED:
                break
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
        it["region"] = "cn"
        picked.append(it)
    picked.sort(key=lambda x: (x["_digest"], x.get("score", 0)), reverse=True)
    for it in region_items(dt.datetime.now(JST)):
        key = it["url"].rstrip("/")
        if key in done or key in seen:
            continue
        seen.add(key)
        picked.append(it)
    order = list(REGION_NAMES)
    picked.sort(key=lambda x: order.index(x["region"]) if x["region"] in order else 99)

    full = feed_fulltext()
    ftdir = a.out.parent / "fulltext"
    ftdir.mkdir(parents=True, exist_ok=True)

    counts = ", ".join(f"{REGION_NAMES[r]} {sum(1 for x in picked if x['region'] == r)}" for r in REGION_NAMES)
    lines = [f"# Candidates {today.isoformat()} ({len(picked)} items: {counts})", ""]
    current = None
    for i, it in enumerate(picked, 1):
        if it["region"] != current:
            current = it["region"]
            lines += [f"# {REGION_NAMES.get(current, current)}", ""]
        lines += [
            f"## {i}. {it.get('title', '').strip()}",
            f"- region: {it['region']}",
            f"- source: {it.get('source')} / {it['_digest']}" + (f" / score {it['score']}" if it.get("score") else ""),
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
