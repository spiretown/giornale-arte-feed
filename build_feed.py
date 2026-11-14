#!/usr/bin/env python3
"""Genera un feed RSS per Il Giornale dell'Arte.

Il feed contiene solo titolo, link, data ed estratto: il testo completo lo
scarica Feeder sul telefono (opzione "Recupera articolo intero").

Uso:
    python build_feed.py            # scrive docs/feed.xml e docs/state.json
    python build_feed.py --dry      # stampa cosa trova, senza scrivere nulla
"""
import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit
from xml.sax.saxutils import escape

import requests
from bs4 import BeautifulSoup

BASE = "https://www.ilgiornaledellarte.com"
SOURCES = [BASE + "/UltimiArticoli", BASE + "/"]
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
MAX_ITEMS = 80    # articoli tenuti nel feed
MAX_NEW = 30      # articoli nuovi scaricati per ogni esecuzione
DELAY = 1.5       # secondi tra una richiesta e l'altra
TITLE_SUFFIX = re.compile(r"\s*[\|\-–]\s*Il Giornale dell.Arte.*$", re.I)


def get(url):
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "it"}, timeout=30)
    r.raise_for_status()
    r.encoding = r.apparent_encoding if r.encoding in (None, "ISO-8859-1") else r.encoding
    return r.text


def article_links(html):
    """Link /Articolo/... nell'ordine in cui compaiono nella pagina."""
    soup = BeautifulSoup(html, "html.parser")
    seen, out = set(), []
    for a in soup.find_all("a", href=True):
        href = urldefrag(urljoin(BASE + "/", a["href"]))[0]
        parts = urlsplit(href)
        if parts.netloc in ("www.ilgiornaledellarte.com", "ilgiornaledellarte.com") and parts.path.startswith("/Articolo/"):
            clean = BASE + parts.path
            if clean not in seen:
                seen.add(clean)
                out.append(clean)
    return out


def parse_date(value):
    if not value:
        return None
    value = value.strip().replace("Z", "+00:00")
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def parse_article(html):
    soup = BeautifulSoup(html, "html.parser")

    def meta(*names):
        for n in names:
            for attr in ("property", "name", "itemprop"):
                tag = soup.find("meta", attrs={attr: n})
                if tag and tag.get("content"):
                    return tag["content"].strip()
        return None

    title = meta("og:title", "twitter:title")
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    title = TITLE_SUFFIX.sub("", title or "").strip()
    desc = meta("og:description", "description", "twitter:description") or ""

    date = parse_date(meta("article:published_time", "datePublished", "date"))
    if not date:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', html)
        date = parse_date(m.group(1)) if m else None
    if not date:
        t = soup.find("time", attrs={"datetime": True})
        date = parse_date(t["datetime"]) if t else None
    return title, desc, date


def build_xml(items):
    now = format_datetime(datetime.now(timezone.utc))
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<rss version="2.0"><channel>',
        "<title>Il Giornale dell'Arte (feed personale)</title>",
        f"<link>{BASE}/</link>",
        "<description>Ultimi articoli de Il Giornale dell'Arte</description>",
        "<language>it</language>",
        f"<lastBuildDate>{now}</lastBuildDate>",
    ]
    for it in items:
        parts.append(
            "<item>"
            f"<title>{escape(it['title'])}</title>"
            f"<link>{escape(it['url'])}</link>"
            f'<guid isPermaLink="true">{escape(it["url"])}</guid>'
            f"<pubDate>{format_datetime(it['sort'])}</pubDate>"
            f"<description>{escape(it['desc'])}</description>"
            "</item>"
        )
    parts.append("</channel></rss>")
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="non scrive file")
    ap.add_argument("--out", default="docs")
    args = ap.parse_args()

    out = Path(args.out)
    state_file = out / "state.json"
    state = json.loads(state_file.read_text("utf-8")) if state_file.exists() else {}

    links = []
    for src in SOURCES:
        try:
            for link in article_links(get(src)):
                if link not in links:
                    links.append(link)
        except Exception as e:  # una sorgente che fallisce non blocca l'altra
            print(f"! Impossibile leggere {src}: {e}", file=sys.stderr)
        time.sleep(DELAY)

    if not links:
        print("ERRORE: nessun link /Articolo/ trovato. Sito cambiato o accesso bloccato.", file=sys.stderr)
        sys.exit(1)
    print(f"Link trovati: {len(links)}")

    now = datetime.now(timezone.utc)
    fetched = 0
    for idx, url in enumerate(links):
        if url in state or fetched >= MAX_NEW:
            continue
        try:
            title, desc, date = parse_article(get(url))
        except Exception as e:
            print(f"! Salto {url}: {e}", file=sys.stderr)
            continue
        fetched += 1
        # data di primo avvistamento: l'ordine della pagina (0 = più recente) viene rispettato
        first_seen = now - timedelta(seconds=idx)
        state[url] = {
            "title": title or url.rsplit("/", 1)[-1].replace("-", " "),
            "desc": desc,
            "published": date.isoformat() if date else None,
            "first_seen": first_seen.isoformat(),
        }
        print(f"+ {state[url]['published'] or 'senza data'}  {state[url]['title']}")
        time.sleep(DELAY)

    items = []
    for url, v in state.items():
        sort = parse_date(v["published"]) or parse_date(v["first_seen"])
        items.append({"url": url, "title": v["title"], "desc": v["desc"], "sort": sort})
    items.sort(key=lambda i: i["sort"], reverse=True)
    items = items[:MAX_ITEMS]
    keep = {i["url"] for i in items}
    state = {u: v for u, v in state.items() if u in keep}

    print(f"Articoli nel feed: {len(items)} (nuovi in questa esecuzione: {fetched})")
    if args.dry:
        return
    out.mkdir(parents=True, exist_ok=True)
    (out / "feed.xml").write_text(build_xml(items), "utf-8")
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main()
