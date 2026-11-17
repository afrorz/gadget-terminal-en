"""Gadget Terminal (English edition) static site builder.

content/posts/*.md (front matter + Markdown) -> public/

    python scripts/build.py           # build
    python scripts/build.py --serve   # build and serve on http://localhost:8001
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import shutil
import sys
from email.utils import format_datetime
from pathlib import Path

import markdown
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content" / "posts"
PUBLIC = ROOT / "public"
STATIC = ROOT / "static"

CATEGORIES = {
    "phones": "Phones & Wearables",
    "pc": "PC & Peripherals",
    "gaming": "Gaming",
    "audio": "Audio",
    "home": "Home & Smart Devices",
    "weird": "Weird & Wonderful",
}
AVAILABILITY = {
    "china-only": ("China only", "No official sales outside China yet"),
    "import": ("Import", "Available through import stores"),
    "global": ("Global", "Sold officially outside China"),
}
OUTSIDE_RE = re.compile(r"can you (get|buy) it outside china", re.I)


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def load_site() -> dict:
    return yaml.safe_load((ROOT / "config" / "site.yaml").read_text(encoding="utf-8"))["site"]


def parse_post(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not m:
        print(f"skip (no front matter): {path.name}", file=sys.stderr)
        return None
    meta = yaml.safe_load(m.group(1)) or {}
    for key in ("title", "slug", "date", "summary"):
        if not meta.get(key):
            raise SystemExit(f"{path.name}: missing '{key}' in front matter")
    if meta.get("category") and meta["category"] not in CATEGORIES:
        raise SystemExit(f"{path.name}: unknown category '{meta['category']}'")
    d = meta["date"]
    if isinstance(d, str):
        d = dt.date.fromisoformat(d)
    meta["date"] = d
    md = markdown.Markdown(extensions=["tables", "sane_lists"])
    body = md.convert(m.group(2))
    body = mark_outside_section(body)
    body = body.replace("<table>", '<div class="tbl"><table>').replace("</table>", "</table></div>")
    meta["body"] = body
    meta["url"] = f"/posts/{meta['slug']}/"
    return meta


def mark_outside_section(body: str) -> str:
    """Wrap the 'Can you get it outside China?' section in a highlighted box."""
    parts = re.split(r"(?=<h2>)", body)
    out = []
    for part in parts:
        h = re.match(r"<h2>(.*?)</h2>", part)
        if h and OUTSIDE_RE.search(h.group(1)):
            part = f'<section class="outside" id="outside-china">{part}</section>'
        out.append(part)
    return "".join(out)


# ---------------------------------------------------------------- layout
# The look is the Japanese edition's (airport terminal: departures board, gate codes).
# design/gt-base.css is copied from gadgetterminal.com; EN_CSS adds the English-only parts.

NAV_LABELS = {"phones": "Phones", "pc": "PC", "gaming": "Gaming", "audio": "Audio",
              "home": "Home", "weird": "Weird"}
CAT_CODES = {
    "phones": ("MOB", "#ff6b3d"),
    "pc": ("PCS", "#4fb3c4"),
    "gaming": ("GAM", "#9b8cff"),
    "audio": ("AUD", "#e46aa8"),
    "home": ("HOM", "#5ad19a"),
    "weird": ("ODD", "#d9b45f"),
}
# availability -> (board status, status class, short note)
STATUS = {
    "china-only": ("CHINA ONLY", "st-urgent", "no global sale"),
    "import": ("IMPORT", "st-warn", "via importers"),
    "global": ("GLOBAL", "st-live", "sold worldwide"),
}

EN_CSS = """
:root{--disp:"Space Grotesk",system-ui,sans-serif;--sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif}
""" + "".join(f".cat-{k}{{--cat:{c}}}\n" for k, (_, c) in CAT_CODES.items()) + """
.brand-ed{font:600 9.5px/1 var(--mono);letter-spacing:.12em;color:var(--ink-3);border:1px solid var(--rule-2);
  padding:3px 5px;border-radius:3px;margin-left:10px}
.av{display:inline-block;font:600 10px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;
  padding:4px 6px;border-radius:3px;border:1px solid currentColor;white-space:nowrap}
.av.china-only{color:var(--accent)}
.av.import{color:#c08a1e}
.av.global{color:#2f9e6a}
[data-theme="dark"] .av.import{color:#d9b45f}
[data-theme="dark"] .av.global{color:#5ad19a}
.card{position:relative}
.card-thumb{position:relative}
.card-thumb .av{position:absolute;top:10px;left:10px;background:var(--bg);z-index:1}
.card-thumb.empty{display:flex;flex-direction:column;justify-content:space-between;height:124px;padding:14px 16px;
  background:#14172e;color:#e9edf1;font-family:var(--mono)}
.card-thumb.empty .av{position:static;align-self:flex-start;background:transparent}
.card-thumb.empty b{font:600 clamp(18px,2.2vw,26px)/1.2 var(--disp);letter-spacing:.01em}
.card-thumb.empty small{font-size:10px;letter-spacing:.2em;color:#96a0ac}
.grid-duo .card-thumb.empty{height:230px}
@media (min-width:1101px){.hero-title,.hero-sub{max-width:calc(100% - 340px)}}
.article-meta .av{margin-left:4px}
.article-hero iframe{display:block;width:100%;aspect-ratio:16/9;border:0;background:#000}
.prose .tbl{overflow-x:auto;margin:18px 0}
.prose thead{display:none}
.prose td:first-child{white-space:nowrap}
.outside{background:var(--surface);border-left:3px solid var(--accent);border-radius:0 6px 6px 0;
  padding:2px 22px 8px;margin:38px 0 0}
.outside h2{margin-top:20px}
.outside li{margin:8px 0}
.page-body{padding-bottom:64px}
"""


def css_bundle() -> str:
    return (ROOT / "design" / "gt-base.css").read_text(encoding="utf-8").strip() + "\n" + EN_CSS.strip() + "\n"


THEME_BOOT = ('<script>(function(){try{if(localStorage.getItem("gt-theme")==="dark"){document.documentElement'
              '.setAttribute("data-theme","dark");}}catch(e){}})();</script>')

HEAD_JS = """<script>(function(){
var h=document.currentScript.previousElementSibling;
var mb=h.querySelector("[data-menu-toggle]");
mb.addEventListener("click",function(){var o=h.classList.toggle("menu-open");
  mb.setAttribute("aria-expanded",o?"true":"false");mb.setAttribute("aria-label",o?"Close menu":"Open menu");});
h.querySelector("[data-theme-toggle]").addEventListener("click",function(){
  var dark=document.documentElement.getAttribute("data-theme")==="dark";var next=dark?"light":"dark";
  if(next==="dark")document.documentElement.setAttribute("data-theme","dark");
  else document.documentElement.removeAttribute("data-theme");
  try{localStorage.setItem("gt-theme",next);}catch(e){}});
function tick(){var t=new Date(Date.now()+28800000);
  var hh=String(t.getUTCHours()).padStart(2,"0"),mm=String(t.getUTCMinutes()).padStart(2,"0");
  h.querySelectorAll('[data-clk="h"]').forEach(function(e){e.textContent=hh;});
  h.querySelectorAll('[data-clk="m"]').forEach(function(e){e.textContent=mm;});}
tick();setInterval(tick,20000);
})();</script>"""


def nav_html() -> str:
    items = "".join(
        f'<a href="/category/{k}/" class="nav-item cat-{k}"><span class="nav-code">{code}</span>'
        f'<span class="nav-label">{esc(NAV_LABELS[k])}</span></a>'
        for k, (code, _) in CAT_CODES.items())
    return (items + '<a href="/about/" class="nav-item nav-about"><span class="nav-code">INF</span>'
            '<span class="nav-label">About</span></a>')


def head(site: dict, title: str, desc: str, path: str, image: str = "", ld: str = "",
         og_type: str = "website") -> str:
    url = site["base_url"] + path
    full = title if title == site["title"] else f"{title} | {site['title']}"
    img = f'<meta property="og:image" content="{esc(image)}">' if image else ""
    cf = ""
    if site.get("cf_analytics_token"):
        cf = ('<script defer src="https://static.cloudflareinsights.com/beacon.min.js" '
              f"data-cf-beacon='{{\"token\": \"{esc(site['cf_analytics_token'])}\"}}'></script>")
    return f"""<!doctype html>
<html lang="{site['lang']}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(full)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(url)}">
<link rel="alternate" type="application/rss+xml" title="{esc(site['title'])}" href="/feed.xml">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<meta property="og:site_name" content="{esc(site['title'])}">
<meta property="og:type" content="{og_type}">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(url)}">
<meta property="og:locale" content="{site['locale']}">
{img}
<meta name="twitter:card" content="{'summary_large_image' if image else 'summary'}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=Space+Grotesk:wght@500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
{THEME_BOOT}
{ld}
{cf}
</head>
<body>
<header class="site-head">
<div class="wrap head-inner">
<a class="brand" href="/"><span class="brand-name">Gadget Terminal</span><span class="caret" aria-hidden="true"></span><span class="brand-ed">EN</span></a>
<nav class="nav">{nav_html()}</nav>
<button type="button" class="theme-toggle" data-theme-toggle aria-label="Switch dark or light mode"><span class="tt-ic tt-ic-moon" aria-hidden="true">☾</span><span class="tt-ic tt-ic-sun" aria-hidden="true">☀</span></button>
<span class="head-clock" aria-hidden="true" title="Beijing time"><small>CST</small><b data-clk="h">--</b><i>:</i><b data-clk="m">--</b></span>
<button type="button" class="menu-btn" data-menu-toggle aria-label="Open menu" aria-expanded="false"><span></span><span></span><span></span></button>
</div>
</header>
{HEAD_JS}
"""


def footer(site: dict) -> str:
    year = dt.date.today().year
    span = f"{site['copyright_from']}" if year == site["copyright_from"] else f"{site['copyright_from']}–{year}"
    return f"""<footer class="site-foot"><div class="wrap">
<div class="foot-board"><span class="foot-code">SYS</span><span class="foot-status">ONLINE</span>
<span class="foot-social"><a href="/feed.xml">RSS</a></span>
<span class="foot-tag">{esc(site['tagline'])}</span></div>
<div class="foot-cols">
<p class="foot-meta"><span class="foot-social-pc"><a href="/feed.xml">RSS</a></span><a href="/about/">About</a><a href="/privacy/">Privacy</a><a href="{esc(site['ja_url'])}" hreflang="ja">日本語版</a><a href="mailto:{esc(site['contact_email'])}">Contact</a></p>
<p class="foot-copy">© {span} Gadget Terminal — {esc(site['author'])}. Prices and availability are as of the date of each article.</p>
</div></div></footer>
</body></html>
"""


def badge(p: dict) -> str:
    a = p.get("availability")
    if a not in AVAILABILITY:
        return ""
    label, tip = AVAILABILITY[a]
    return f'<span class="av {a}" title="{esc(tip)}">{esc(label)}</span>'


def video_id(p: dict) -> str:
    v = str(p.get("video") or "").strip()
    return v if re.fullmatch(r"[A-Za-z0-9_-]{11}", v) else ""


def card_image(p: dict) -> str:
    """カードと OGP に使う画像。公式写真が無ければ YouTube 動画のサムネイル。"""
    if p.get("thumbnail"):
        return p["thumbnail"]
    vid = video_id(p)
    return f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg" if vid else ""


def read_min(p: dict) -> int:
    return max(1, round(len(re.findall(r"[A-Za-z]+", re.sub(r"<[^>]+>", " ", p["body"]))) / 220))


def product_name(p: dict) -> str:
    """Board KEY column. front matter `product`, else the first words of the title."""
    if p.get("product"):
        return str(p["product"])
    return " ".join(re.sub(r"[\"“”]", "", p["title"]).split()[:4])


def card(p: dict) -> str:
    img = card_image(p)
    k = p.get("category") or ""
    code = CAT_CODES.get(k, ("GT", ""))[0]
    thumb = (f'<a class="card-thumb card-thumb-real" href="{p["url"]}" aria-hidden="true" tabindex="-1">{badge(p)}'
             f'<img src="{esc(img)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer"></a>'
             if img else
             f'<a class="card-thumb empty" href="{p["url"]}" aria-hidden="true" tabindex="-1">{badge(p)}'
             f'<b>{esc(product_name(p))}</b><small>GT · {code} · NO PHOTO YET</small></a>')
    return f"""<article class="card cat-{k}">{thumb}
<p class="card-meta"><a class="card-code" href="/category/{k}/">{code}</a><span class="card-cat">{esc(CATEGORIES.get(k, ''))}</span>
<time datetime="{p['date']}">{p['date']:%Y.%m.%d}</time><span class="card-read">{read_min(p)}MIN</span></p>
<h2 class="card-title"><a href="{p['url']}">{esc(p['title'])}</a></h2>
<p class="card-excerpt">{esc(p['summary'])}</p>
</article>"""


def board_row(p: dict, n: int) -> str:
    k = p.get("category") or ""
    code = CAT_CODES.get(k, ("GT", ""))[0]
    frm_code, _, frm_city = str(p.get("from") or "CN China").partition(" ")
    st, cls, note = STATUS.get(p.get("availability"), ("TBC", "st-plain", ""))
    img = card_image(p)
    thumb = (f'<img src="{esc(img)}" alt="" loading="lazy" decoding="async" referrerpolicy="no-referrer" '
             'width="96" height="96">' if img else "")
    return f"""<a class="board-row cat-{k}" href="{p['url']}">
<span class="b-thumb" aria-hidden="true">{thumb}</span>
<span class="b-flt">GT {n:04d}</span>
<span class="b-from"><b>{esc(frm_code)}</b><span>{esc(frm_city)}</span></span>
<span class="b-code">{code}</span>
<span class="b-key"><b>{esc(product_name(p))}</b><small class="b-what">{esc(p['summary'])}</small></span>
<span class="b-title">{esc(p['title'])}</span>
<span class="st {cls}">{st}<em>{esc(note)}</em></span>
<span class="b-arrow" aria-hidden="true">→</span>
</a>"""


PLANE = ('<svg class="pict-arr" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><g transform="rotate(-22 12 11)">'
         '<path d="M21 11 L14.5 11.8 L10 17 L7.5 17 L9.8 11.9 L4.5 12 L3 14 L1.5 14 L2.6 11 L1.5 8 L3 8 L4.5 10 '
         'L9.8 10.1 L7.5 5 L10 5 L14.5 10.2 Z"></path></g><rect x="2.5" y="20" width="19" height="1.5" rx=".75"></rect></svg>')


def board(posts: list[dict], total: int) -> str:
    rows = "\n".join(board_row(p, total - i) for i, p in enumerate(posts))
    return f"""<section class="board">
<h2 class="visually-hidden">Departures</h2>
<div class="board-title"><span class="board-tab" aria-selected="true">{PLANE}<span class="board-title-en">DEPARTURES</span><span class="board-tab-ja">Latest from China</span></span></div>
<div class="board-head"><span>FLIGHT</span><span>FROM</span><span>CAT</span><span>KEY</span><span>ENTRY</span><span>OUTSIDE CHINA</span><span></span></div>
{rows}
</section>"""


def grid(posts: list[dict]) -> str:
    if not posts:
        return '<p class="empty">No articles yet.</p>'
    duo, rest = posts[:2], posts[2:]
    out = '<div class="grid grid-duo">' + "".join(card(p) for p in duo) + "</div>"
    if rest:
        out += '<div class="grid">' + "".join(card(p) for p in rest) + "</div>"
    return out


def render_index(site: dict, posts: list[dict]) -> str:
    return head(site, site["title"], site["description"], "/") + f"""<main class="wrap home">
<section class="hero">
<p class="eyebrow">CHINA ONLY / ENGLISH EDITION</p>
<h1 class="hero-title">{esc(site['tagline'])}</h1>
<p class="hero-sub">{esc(site['description'])}</p>
<img class="hero-route" src="/assets/hero-plane.png" alt="" aria-hidden="true">
</section>
{board(posts[:6], len(posts))}
{grid(posts)}
</main>""" + footer(site)


def render_category(site: dict, key: str, posts: list[dict]) -> str:
    code = CAT_CODES[key][0]
    name = CATEGORIES[key]
    path = f"/category/{key}/"
    count = f"{len(posts)} article{'s' if len(posts) != 1 else ''}"
    return head(site, name, f"{name}: China-only gadgets explained in English.", path) + f"""<main class="wrap home cat-{key}">
<section class="hero hero-sm">
<p class="eyebrow">GATE {code} / {esc(name)}</p>
<h1 class="hero-title">{esc(name)}</h1>
<p class="hero-sub">{count}. China-only gadgets, and whether you can get one outside China.</p>
</section>
{grid(posts)}
</main>""" + footer(site)


def render_post(site: dict, p: dict) -> str:
    k = p.get("category") or ""
    code = CAT_CODES.get(k, ("GT", ""))[0]
    fig = ""
    if p.get("thumbnail"):
        credit = (f'<figcaption class="hero-credit">Image: {esc(p.get("thumbnail_credit"))}</figcaption>'
                  if p.get("thumbnail_credit") else "")
        fig = (f'<figure class="article-hero article-hero-real"><img src="{esc(p["thumbnail"])}" alt="{esc(p["title"])}" '
               f'decoding="async" referrerpolicy="no-referrer">{credit}</figure>')
    vid = video_id(p)
    if vid:
        vcredit = (f'<figcaption class="hero-credit">Video: {esc(p.get("video_credit"))}</figcaption>'
                   if p.get("video_credit") else "")
        fig += (f'<figure class="article-hero video"><iframe src="https://www.youtube-nocookie.com/embed/{vid}" '
                f'title="{esc(p["title"])}" loading="lazy" allowfullscreen '
                'allow="accelerometer; encrypted-media; gyroscope; picture-in-picture"></iframe>'
                f'{vcredit}</figure>')
    srcs = ""
    if p.get("sources"):
        items = "".join(
            f'<li><a href="{esc(s["url"])}" rel="nofollow noopener" target="_blank">{esc(s.get("title") or s["url"])}</a>'
            + (f'<span class="src-pub">{esc(s["publisher"])}</span>' if s.get("publisher") else "") + "</li>"
            for s in p["sources"])
        srcs = (f'<section class="sources"><h2>Sources</h2><ol>{items}</ol>'
                '<p class="sources-note">We wrote this article from the sources above. Prices and availability are '
                'as of the date of the article. Check the official pages before you buy.</p></section>')
    ld = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": p["title"], "description": p["summary"],
        "datePublished": p["date"].isoformat(),
        "dateModified": str(p.get("modified") or p["date"]),
        "inLanguage": "en", "mainEntityOfPage": site["base_url"] + p["url"],
        "author": {"@type": "Organization", "name": site["author"]},
        "publisher": {"@type": "Organization", "name": site["author"]},
    }
    if card_image(p):
        ld["image"] = [card_image(p)]
    ld_tag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    return head(site, p["title"], p["summary"], p["url"], card_image(p), ld_tag, "article") + f"""<main class="wrap article-wrap">
<article class="article cat-{k}">
<p class="eyebrow"><a href="/category/{k}/"><span class="eyebrow-code">{code}</span>{esc(CATEGORIES.get(k, ''))}</a></p>
<h1 class="article-title">{esc(p['title'])}</h1>
<p class="article-lede">{esc(p['summary'])}</p>
<p class="article-meta"><time datetime="{p['date']}">{p['date']:%Y.%m.%d}</time><span class="dot"></span>{read_min(p)} MIN READ<span class="dot"></span>{badge(p)}</p>
{fig}
<div class="prose">{p['body']}</div>
{srcs}
</article>
</main>""" + footer(site)


def render_page(site: dict, path: str, title: str, desc: str, body_md: str) -> str:
    body = markdown.markdown(body_md, extensions=["tables"])
    return head(site, title, desc, path) + f"""<main class="wrap article-wrap page-body">
<article class="article">
<p class="eyebrow">INF / Gadget Terminal</p>
<h1 class="article-title">{esc(title)}</h1>
<div class="prose">{body}</div>
</article>
</main>""" + footer(site)


ABOUT = """Gadget Terminal covers new gadgets that launch **only in China**: on Xiaomi Youpin, JD.com, Tmall and Chinese crowdfunding platforms.

English tech sites often report the specs and the price in yuan. We add the part that matters if you live outside China: **can you actually get one?**

Every article ends with a section called *Can you get it outside China?* It covers:

- where you can buy it today (official global store, import shops, or buying agents)
- whether a global version has been announced
- whether we could confirm FCC (US) or CE (EU) certification
- what works and what does not outside China (apps, cloud services, language)
- alternatives you can buy locally

## Our rules

- We only use numbers that appear in official pages or in the reports we cite. If something is not confirmed, we say so.
- Prices and availability are as of the date of each article.
- We list our sources at the end of every article, including Chinese-language sources.
- We do not accept payment for coverage.

## Who we are

Gadget Terminal is run by {author}, the publisher of the [Japanese edition]({ja_url}). Contact: {email}
"""

PRIVACY = """This site is operated by {author}.

## Analytics

We may use Cloudflare Web Analytics to count visits. It does not use cookies and does not track you across sites.

## Advertising and affiliate links

Some pages may contain advertising or affiliate links in the future. If we add them, we will update this page, and affiliate links will be marked.

## Links to other sites

Articles link to official product pages and news sources. Those sites have their own privacy policies.

## Contact

{email}
"""


def render_sitemap(site: dict, posts: list[dict]) -> str:
    urls = [("/", posts[0]["date"] if posts else dt.date.today())]
    urls += [(p["url"], p.get("modified") or p["date"]) for p in posts]
    urls += [(f"/category/{k}/", None) for k in CATEGORIES]
    urls += [("/about/", None), ("/privacy/", None)]
    rows = "".join(
        f"<url><loc>{site['base_url']}{u}</loc>{f'<lastmod>{d}</lastmod>' if d else ''}</url>" for u, d in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{rows}</urlset>\n'


def render_feed(site: dict, posts: list[dict]) -> str:
    items = ""
    for p in posts[:30]:
        when = dt.datetime.combine(p["date"], dt.time(6, 0), tzinfo=dt.timezone.utc)
        link = site["base_url"] + p["url"]
        items += (f"<item><title>{esc(p['title'])}</title><link>{link}</link><guid>{link}</guid>"
                  f"<pubDate>{format_datetime(when)}</pubDate><description>{esc(p['summary'])}</description></item>")
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<rss version="2.0"><channel>'
            f"<title>{esc(site['title'])}</title><link>{site['base_url']}/</link>"
            f"<description>{esc(site['description'])}</description><language>en</language>{items}</channel></rss>\n")


def write(path: str, text: str) -> None:
    out = PUBLIC / path.lstrip("/")
    if path.endswith("/"):
        out = out / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")


def build() -> int:
    site = load_site()
    posts = [p for p in (parse_post(f) for f in sorted(CONTENT.glob("*.md"))) if p]
    slugs = [p["slug"] for p in posts]
    dup = {s for s in slugs if slugs.count(s) > 1}
    if dup:
        raise SystemExit(f"duplicate slug: {', '.join(sorted(dup))}")
    posts.sort(key=lambda p: p["date"], reverse=True)

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir()
    (PUBLIC / "assets").mkdir()
    for f in STATIC.glob("*"):
        shutil.copy(f, PUBLIC / "assets" / f.name)
    (PUBLIC / "assets" / "style.css").write_text(css_bundle(), encoding="utf-8")

    fill = {"author": site["author"], "ja_url": site["ja_url"], "email": site["contact_email"]}
    write("/", render_index(site, posts))
    for p in posts:
        write(p["url"], render_post(site, p))
    for key in CATEGORIES:
        write(f"/category/{key}/", render_category(site, key, [p for p in posts if p.get("category") == key]))
    write("/about/", render_page(site, "/about/", "About Gadget Terminal",
                                 "What Gadget Terminal covers and how we write.", ABOUT.format(**fill)))
    write("/privacy/", render_page(site, "/privacy/", "Privacy Policy",
                                   "Privacy policy of Gadget Terminal (English edition).", PRIVACY.format(**fill)))
    write("/404.html", render_page(site, "/404.html", "Page not found", "Page not found.",
                                   "The page you are looking for does not exist. [Go to the front page](/)."))
    write("/sitemap.xml", render_sitemap(site, posts))
    write("/feed.xml", render_feed(site, posts))
    write("/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {site['base_url']}/sitemap.xml\n")
    write("/CNAME", site["domain"] + "\n")
    print(f"built {len(posts)} posts -> {PUBLIC}")
    return len(posts)


if __name__ == "__main__":
    build()
    if "--serve" in sys.argv:
        import functools
        import http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(PUBLIC))
        print("http://localhost:8001")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8001), handler).serve_forever()
