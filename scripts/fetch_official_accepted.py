#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch official 2026 accepted-paper lists for the security Big4.

This is a source-audit layer, not the usable-security classifier. It keeps the
official title/author/cycle evidence in data/official_accepted_2026_raw.json.
The hand-verified usable subset lives in data/usable_security_2026.json.
"""
import html
import json
import os
import re
import time
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "official_accepted_2026_raw.json")

SOURCES = {
    "USENIX Security": {
        "cycle1": "https://www.usenix.org/conference/usenixsecurity26/cycle1-accepted-papers",
        "cycle2": "https://www.usenix.org/conference/usenixsecurity26/cycle2-accepted-papers",
    },
    "IEEE S&P": {
        "all": "https://sp2026.ieee-security.org/accepted-papers.html",
    },
    "NDSS": {
        "all": "https://www.ndss-symposium.org/ndss2026/accepted-papers/",
    },
    "ACM CCS": {
        "all": "https://www.sigsac.org/ccs/CCS2026/accepted-papers.html",
    },
}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "paper-dashboard/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception:
        return 0, ""


def clean(value):
    value = re.sub(r"(?is)<[^>]+>", " ", value or "")
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def parse_usenix(page):
    rows = []
    pattern = re.compile(r"(?is)<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|$)")
    for match in pattern.finditer(page):
        title = clean(match.group(1))
        if not title:
            continue
        body = match.group(2)
        author_match = re.search(
            r'(?is)<div[^>]+field-name-field-person[^>]*>(.*?)</div>\s*</div>',
            body,
        )
        authors = clean(author_match.group(1)) if author_match else ""
        rows.append({"title": title, "authors_text": authors})
    return rows


def parse_sp(page):
    rows = []
    positions = [
        ("cycle1", page.find('id="cycle1"')),
        ("cycle2", page.find('id="cycle2"')),
    ]
    positions = [(name, pos) for name, pos in positions if pos >= 0]
    for index, (cycle, start) in enumerate(positions):
        end = positions[index + 1][1] if index + 1 < len(positions) else len(page)
        section = page[start:end]
        pattern = re.compile(
            r'(?is)<b><a[^>]*>(.*?)<span.*?</a></b><br\s*/?>\s*'
            r'<div[^>]*class="[^"]*authorlist[^"]*"[^>]*>(.*?)</div>'
        )
        for match in pattern.finditer(section):
            rows.append({
                "title": clean(match.group(1)),
                "authors_text": clean(match.group(2)),
                "cycle": cycle,
            })
    return rows


def parse_ndss(page):
    rows = []
    pattern = re.compile(
        r'(?is)<h2[^>]*class="[^"]*pt-cv-title[^"]*"[^>]*>'
        r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a></h2>\s*'
        r'<div[^>]*class="[^"]*pt-cv-ctf-list[^"]*"[^>]*>.*?<p>(.*?)</p>'
    )
    for match in pattern.finditer(page):
        rows.append({
            "title": clean(match.group(2)),
            "authors_text": clean(match.group(3)),
            "paper_url": html.unescape(match.group(1)),
            "cycle": "summer/fall not exposed per paper",
        })
    return rows


def main():
    result = {
        "generated_at": time.strftime("%Y-%m-%d"),
        "note": "Official-list audit. A missing page means not publicly available, not zero accepted papers.",
        "venues": {},
    }
    for venue, endpoints in SOURCES.items():
        venue_rows = []
        endpoint_status = {}
        for cycle, url in endpoints.items():
            status, page = fetch(url)
            endpoint_status[cycle] = {"url": url, "http_status": status}
            if status != 200:
                continue
            if venue == "USENIX Security":
                rows = parse_usenix(page)
                for row in rows:
                    row["cycle"] = cycle
            elif venue == "IEEE S&P":
                rows = parse_sp(page)
            elif venue == "NDSS":
                rows = parse_ndss(page)
            else:
                rows = []
            venue_rows.extend(rows)
        result["venues"][venue] = {
            "endpoints": endpoint_status,
            "paper_count": len(venue_rows),
            "papers": venue_rows,
        }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT}")
    for venue, data in result["venues"].items():
        print(f"  {venue}: {data['paper_count']} official records")


if __name__ == "__main__":
    main()
