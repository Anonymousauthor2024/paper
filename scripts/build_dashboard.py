#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_dashboard.py — 把已生成的数据汇总成一个自包含的 HTML 看板(index.html)。

读取:
  data/experts_papers.json          大牛库(fetch_experts.py 产出)
  security/trends/latest.md          安全趋势(fetch_trends.py 产出)
  hci/trends/latest.md               HCI 趋势
输出:
  index.html                         单页看板,可直接用 GitHub Pages 托管

只用标准库。不联网。
"""
import json, os, re, html
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def read(path):
    p = os.path.join(ROOT, path)
    return open(p, encoding="utf-8").read() if os.path.exists(p) else ""

def md_to_html(md):
    """极简 markdown 渲染:## 标题、- 列表、**粗**、_斜_。"""
    out, in_ul = [], False
    for line in md.split("\n"):
        line = line.rstrip()
        if line.startswith("# "):
            continue  # 顶层标题由外层提供
        m = line
        m = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", m)
        m = re.sub(r"^_(.+)_$", r'<p class="muted">\1</p>', m)
        if line.startswith("## "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h3>{m[3:]}</h3>")
        elif line.startswith("- "):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{m[2:]}</li>")
        elif m.startswith("<p"):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(m)
        elif m.strip():
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<p>{m}</p>")
    if in_ul: out.append("</ul>")
    return "\n".join(out)

def paper_url(p):
    ax = (p.get("externalIds") or {}).get("ArXiv")
    if ax:
        return f"https://arxiv.org/abs/{ax}"
    return p.get("url") or "#"

def expert_card(e, tz):
    recent = [p for p in e["papers"]
              if p.get("category") != "other" and (p.get("year") or 0) >= 2025]
    items = []
    for p in recent:
        cat = p.get("category", "other")
        new = ' <span class="new">🆕</span>' if _is_recent(p) else ""
        venue = html.escape((p.get("venue") or "—")[:38])
        title = html.escape(p.get("title") or "")
        zh = html.escape((tz.get(p.get("paperId", "")) or {}).get("zh", ""))
        zh_html = f'<span class="zh">{zh}</span>' if zh else ""
        items.append(
            f'<li><span class="tag {cat}">{cat}</span> '
            f'<span class="yr">{p.get("year") or "?"}</span>{new} '
            f'<a href="{html.escape(paper_url(p))}" target="_blank">{title}</a>'
            f'{zh_html}<span class="venue">{venue}</span></li>')
    return f"""<div class="card">
      <div class="chead"><b>{html.escape(e['name'])}</b>
        <span class="aff">{html.escape(e.get('affiliation') or '')}</span></div>
      <div class="stat">2025 年以来 {len(recent)} 篇</div>
      <ul class="papers">{''.join(items)}</ul>
    </div>"""

RECENT_DAYS = 18 * 31
def _is_recent(p):
    from datetime import date as _d
    pd = p.get("publicationDate")
    d = None
    if pd:
        try: d = _d.fromisoformat(pd)
        except ValueError: d = None
    if not d and p.get("year"):
        d = _d(p["year"], 7, 1)
    return d is not None and (_d.today() - d).days <= RECENT_DAYS

def main():
    data = json.loads(read("data/experts_papers.json") or "{}")
    experts = data.get("experts", [])
    gen = data.get("generated_at", "")
    total_infield = sum(e["in_field_count"] for e in experts)
    tz = json.loads(read("data/title_zh.json") or "{}")
    cards = "\n".join(expert_card(e, tz) for e in experts)
    sec_html = md_to_html(read("security/trends/latest.md"))
    hci_html = md_to_html(read("hci/trends/latest.md"))

    doc = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Usable Security / HCI 论文追踪看板</title>
<style>
:root{{--bg:#fafafa;--fg:#1a1a1a;--mut:#666;--card:#fff;--line:#e5e5e5;--acc:#2563eb;}}
@media(prefers-color-scheme:dark){{:root{{--bg:#15171a;--fg:#e8e8e8;--mut:#9aa0a6;--card:#1e2127;--line:#2c3037;--acc:#6ea8fe;}}}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--fg);
font:15px/1.55 -apple-system,Segoe UI,Roboto,"Microsoft YaHei",sans-serif}}
header{{padding:24px 20px;border-bottom:1px solid var(--line)}}
h1{{margin:0 0 4px;font-size:20px}}.sub{{color:var(--mut);font-size:13px}}
nav{{position:sticky;top:0;background:var(--bg);border-bottom:1px solid var(--line);
padding:10px 20px;display:flex;gap:16px;z-index:5}}
nav a{{color:var(--acc);text-decoration:none;font-size:14px}}
main{{max-width:1100px;margin:0 auto;padding:20px}}
section{{margin-bottom:36px}}h2{{font-size:17px;border-left:3px solid var(--acc);padding-left:10px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px}}
.chead b{{font-size:15px}}.aff{{color:var(--mut);font-size:12px;margin-left:6px}}
.stat{{color:var(--mut);font-size:12px;margin:4px 0 8px}}
ul.papers{{list-style:none;margin:0;padding:0}}
ul.papers li{{padding:5px 0;border-top:1px dashed var(--line);font-size:13px}}
.tag{{font-size:11px;padding:1px 5px;border-radius:4px;background:#e5edff;color:#2050c0}}
.tag.hci{{background:#e9f7ec;color:#1f8a3b}}.tag.preprint{{background:#f3e9ff;color:#7a3ec0}}
@media(prefers-color-scheme:dark){{.tag{{background:#22345e;color:#9dbcff}}
.tag.hci{{background:#1f3a29;color:#8fe0a5}}.tag.preprint{{background:#33234d;color:#c8a6ff}}}}
.yr{{color:var(--mut);font-size:12px}}.new{{font-size:11px}}
ul.papers a{{color:var(--fg);text-decoration:none}}ul.papers a:hover{{color:var(--acc)}}
.zh{{display:block;color:var(--fg);opacity:.72;font-size:12.5px;margin:1px 0}}
.venue{{display:block;color:var(--mut);font-size:11px}}
.trend h3{{font-size:14px;margin:14px 0 6px}}.trend ul{{margin:4px 0;padding-left:20px}}
.trend li{{font-size:13px;margin:2px 0}}.muted{{color:var(--mut);font-size:12px}}
</style></head><body>
<header><h1>Usable Security / HCI 论文追踪看板</h1>
<div class="sub">大牛库 {len(experts)} 人 · 领域内论文 {total_infield} 篇 · 数据更新 {gen}</div></header>
<nav><a href="#experts">大牛库</a><a href="#sec">安全趋势</a><a href="#hci">HCI 趋势</a></nav>
<main>
<section id="experts"><h2>大牛库 · 各学者最近论文</h2>
<div class="grid">{cards}</div></section>
<section id="sec" class="trend"><h2>安全领域 · 新趋势</h2>{sec_html}</section>
<section id="hci" class="trend"><h2>HCI 领域 · 隐私安全新趋势</h2>{hci_html}</section>
</main></body></html>"""
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(doc)
    print(f"看板已生成 index.html（{len(experts)} 位大牛，{total_infield} 篇领域内论文）")

if __name__ == "__main__":
    main()
