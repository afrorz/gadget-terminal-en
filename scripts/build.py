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
    body = body.replace("<table>", '<div class="table"><table>').replace("</table>", "</table></div>")
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

CSS = """
:root{
  --bg:#f6f7f9; --surface:#eff1f3; --raised:#e7eaed;
  --ink:#1a1e24; --ink-2:#5c6570; --ink-3:#8d95a0;
  --rule:#e7e9ec; --rule-2:#dadde1;
  --accent:#ff6b3d; --warn:#b4472b;
  --max:1120px; --measure:40rem;
  --mono:"IBM Plex Mono",ui-monospace,SFMono-Regular,Menlo,monospace;
  --disp:"Space Grotesk",system-ui,sans-serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#0a0d16; --surface:#10141f; --raised:#151a27;
  --ink:#e9edf1; --ink-2:#96a0ac; --ink-3:#5f6975;
  --rule:#1c212e; --rule-2:#272e40; --warn:#e08b6a;
}}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:17px/1.7 var(--sans)}
a{color:inherit}
img{max-width:100%;height:auto;display:block}
.wrap{max-width:var(--max);margin:0 auto;padding:0 16px}
header.site{border-bottom:1px solid var(--rule-2)}
header.site .wrap{display:flex;align-items:center;justify-content:space-between;gap:16px;height:64px}
.logo{font:700 20px/1 var(--disp);text-decoration:none;letter-spacing:-.01em;display:flex;align-items:center;gap:8px}
.logo b{color:var(--accent)}
.logo small{font:500 11px/1 var(--mono);color:var(--ink-3);border:1px solid var(--rule-2);padding:3px 5px;border-radius:3px}
nav.top a{font:500 13px/1 var(--mono);color:var(--ink-2);text-decoration:none;margin-left:18px}
nav.top a:hover{color:var(--accent)}
.hero{padding:56px 0 40px;border-bottom:1px solid var(--rule)}
.hero p.kicker{font:500 12px/1 var(--mono);letter-spacing:.12em;text-transform:uppercase;color:var(--accent);margin:0 0 14px}
.hero h1{font:700 clamp(30px,5vw,48px)/1.1 var(--disp);letter-spacing:-.02em;margin:0;max-width:22ch}
.hero p.lede{color:var(--ink-2);max-width:var(--measure);margin:16px 0 0}
.list{padding:24px 0 64px}
.card{display:grid;grid-template-columns:200px 1fr;gap:24px;padding:24px 0;border-bottom:1px solid var(--rule);text-decoration:none}
.card .thumb{aspect-ratio:4/3;background:var(--surface);border-radius:6px;overflow:hidden}
.card .thumb img{width:100%;height:100%;object-fit:cover}
.card .thumb.empty{display:flex;align-items:center;justify-content:center;font:600 13px/1 var(--mono);color:var(--ink-3)}
.card h2{font:700 22px/1.3 var(--disp);letter-spacing:-.01em;margin:8px 0}
.card:hover h2{color:var(--accent)}
.card p{color:var(--ink-2);margin:0;font-size:15px}
.meta{font:500 12px/1.4 var(--mono);color:var(--ink-3);display:flex;flex-wrap:wrap;gap:10px;align-items:center}
.badge{display:inline-block;font:600 11px/1 var(--mono);text-transform:uppercase;letter-spacing:.06em;padding:4px 7px;border-radius:3px;border:1px solid currentColor}
.badge.china-only{color:var(--warn)}
.badge.import{color:#c68a12}
.badge.global{color:#2f9e6a}
article{max-width:var(--measure);margin:0 auto;padding:40px 0 64px}
article h1{font:700 clamp(28px,4.4vw,40px)/1.15 var(--disp);letter-spacing:-.02em;margin:12px 0 16px}
article .summary{font-size:19px;color:var(--ink-2);margin:0 0 24px}
article figure{margin:0 0 28px}
article figure img{border-radius:8px;background:var(--surface);width:100%}
article figcaption{font:12px/1.4 var(--mono);color:var(--ink-3);margin-top:8px}
article h2{font:700 24px/1.25 var(--disp);margin:40px 0 12px;letter-spacing:-.01em}
.table{overflow-x:auto;margin:16px 0}
table{border-collapse:collapse;width:100%;font-size:15px}
td,th{border-bottom:1px solid var(--rule-2);padding:9px 10px;text-align:left;vertical-align:top}
thead{display:none}
td:first-child{color:var(--ink-2);white-space:nowrap;font:500 13px/1.5 var(--mono)}
.outside{background:var(--surface);border-left:4px solid var(--accent);border-radius:0 8px 8px 0;padding:4px 22px 10px;margin:40px 0}
.outside h2{margin-top:20px}
.outside li{margin:8px 0}
.sources{border-top:1px solid var(--rule-2);margin-top:48px;padding-top:16px;font-size:14px;color:var(--ink-2)}
.sources h3{font:600 12px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);margin:0 0 10px}
.sources ul{padding-left:18px;margin:0}
.page h1{font:700 36px/1.2 var(--disp)}
footer.site{border-top:1px solid var(--rule-2);padding:32px 0 48px;font-size:13px;color:var(--ink-3)}
footer.site a{margin-right:16px}
@media (max-width:640px){
  .card{grid-template-columns:96px 1fr;gap:14px}
  .card h2{font-size:17px}
  .card p{display:none}
  nav.top a{margin-left:12px}
  .logo small{display:none}
}
"""


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
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@500;600&family=Space+Grotesk:wght@500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/style.css">
{ld}
{cf}
</head>
<body>
<header class="site"><div class="wrap">
<a class="logo" href="/">Gadget <b>Terminal</b> <small>EN</small></a>
<nav class="top"><a href="/about/">About</a><a href="/feed.xml">RSS</a></nav>
</div></header>
"""


def footer(site: dict) -> str:
    year = dt.date.today().year
    span = f"{site['copyright_from']}" if year == site["copyright_from"] else f"{site['copyright_from']}–{year}"
    return f"""<footer class="site"><div class="wrap">
<p><a href="/about/">About</a><a href="/privacy/">Privacy</a><a href="{esc(site['ja_url'])}" hreflang="ja">日本語版</a></p>
<p>© {span} {esc(site['author'])}. Prices and availability are as of the date of each article.</p>
</div></footer>
</body></html>
"""


def badge(p: dict) -> str:
    a = p.get("availability")
    if a not in AVAILABILITY:
        return ""
    label, tip = AVAILABILITY[a]
    return f'<span class="badge {a}" title="{esc(tip)}">{esc(label)}</span>'


def card(p: dict) -> str:
    thumb = (f'<div class="thumb"><img src="{esc(p["thumbnail"])}" alt="" loading="lazy" '
             'referrerpolicy="no-referrer"></div>') if p.get("thumbnail") else '<div class="thumb empty">GT</div>'
    cat = CATEGORIES.get(p.get("category"), "")
    return f"""<a class="card" href="{p['url']}">{thumb}<div>
<div class="meta"><time datetime="{p['date']}">{p['date']:%b %d, %Y}</time><span>{esc(cat)}</span>{badge(p)}</div>
<h2>{esc(p['title'])}</h2><p>{esc(p['summary'])}</p></div></a>"""


def render_index(site: dict, posts: list[dict]) -> str:
    cards = "\n".join(card(p) for p in posts)
    return head(site, site["title"], site["description"], "/") + f"""<main>
<section class="hero"><div class="wrap">
<p class="kicker">Gadget Terminal / English edition</p>
<h1>{esc(site['tagline'])}</h1>
<p class="lede">{esc(site['description'])}</p>
</div></section>
<section class="list"><div class="wrap">{cards}</div></section>
</main>""" + footer(site)


def render_post(site: dict, p: dict) -> str:
    fig = ""
    if p.get("thumbnail"):
        credit = f"<figcaption>Image: {esc(p.get('thumbnail_credit'))}</figcaption>" if p.get("thumbnail_credit") else ""
        fig = (f'<figure><img src="{esc(p["thumbnail"])}" alt="{esc(p["title"])}" '
               f'referrerpolicy="no-referrer">{credit}</figure>')
    srcs = ""
    if p.get("sources"):
        items = "".join(
            f'<li><a href="{esc(s["url"])}" rel="nofollow noopener" target="_blank">{esc(s.get("title") or s["url"])}</a>'
            f'{" — " + esc(s["publisher"]) if s.get("publisher") else ""}</li>'
            for s in p["sources"])
        srcs = f'<aside class="sources"><h3>Sources</h3><ul>{items}</ul></aside>'
    ld = {
        "@context": "https://schema.org", "@type": "NewsArticle",
        "headline": p["title"], "description": p["summary"],
        "datePublished": p["date"].isoformat(),
        "dateModified": str(p.get("modified") or p["date"]),
        "inLanguage": "en", "mainEntityOfPage": site["base_url"] + p["url"],
        "author": {"@type": "Organization", "name": site["author"]},
        "publisher": {"@type": "Organization", "name": site["author"]},
    }
    if p.get("thumbnail"):
        ld["image"] = [p["thumbnail"]]
    ld_tag = f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>'
    cat = CATEGORIES.get(p.get("category"), "")
    return head(site, p["title"], p["summary"], p["url"], p.get("thumbnail", ""), ld_tag, "article") + f"""<main><div class="wrap">
<article>
<div class="meta"><time datetime="{p['date']}">{p['date']:%b %d, %Y}</time><span>{esc(cat)}</span>{badge(p)}</div>
<h1>{esc(p['title'])}</h1>
<p class="summary">{esc(p['summary'])}</p>
{fig}
{p['body']}
{srcs}
</article>
</div></main>""" + footer(site)


def render_page(site: dict, path: str, title: str, desc: str, body_md: str) -> str:
    body = markdown.markdown(body_md, extensions=["tables"])
    return head(site, title, desc, path) + f"""<main><div class="wrap"><article class="page">
<h1>{esc(title)}</h1>
{body}
</article></div></main>""" + footer(site)


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
    (PUBLIC / "assets" / "style.css").write_text(CSS.strip() + "\n", encoding="utf-8")

    fill = {"author": site["author"], "ja_url": site["ja_url"], "email": site["contact_email"]}
    write("/", render_index(site, posts))
    for p in posts:
        write(p["url"], render_post(site, p))
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
