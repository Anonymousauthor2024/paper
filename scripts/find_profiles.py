#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
find_profiles.py — 对 experts.json 里每位大牛,扫描所有同名 Semantic Scholar profile,
按 usable security / HCI 会议论文认领,报告"疑似漏绑"的 profile id 供人工确认。

背景:SS 作者消歧不可靠,一个大牛常被拆成多个 profile(如 Jingjie Li 被拆成 2 个)。
只绑一个 id 会漏掉一半论文。本脚本自动查漏,补齐 experts.json。

只用标准库。可选 S2_API_KEY 提速。
输出:people/profile_audit.md
"""
import json, os, time, urllib.request, urllib.parse, urllib.error
from fetch_experts import SEC_PATTERNS, HCI_PATTERNS   # 复用 venue 分类规则

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERTS_FILE = os.path.join(ROOT, "people", "experts.json")
SEARCH_URL = "https://api.semanticscholar.org/graph/v1/author/search"
BATCH_URL = "https://api.semanticscholar.org/graph/v1/author/batch"
API_KEY = os.environ.get("S2_API_KEY")
MAX_CANDIDATES = 80
PC_MIN, PC_MAX = 2, 150     # 候选 paperCount 过滤:排除单篇噪声与超大(医学/系统)号

def field_hit(venue):
    v = " " + (venue or "").lower() + " "
    return any(p in v for p in SEC_PATTERNS + HCI_PATTERNS)

def req(url, data=None):
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data).encode()
    r = urllib.request.Request(url, data=data, headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            time.sleep(5 * (attempt + 1) if e.code == 429 else 3)
        except Exception:
            time.sleep(3)
    return None

def search_candidates(name):
    url = SEARCH_URL + "?" + urllib.parse.urlencode(
        {"query": name, "fields": "name,paperCount", "limit": 100})
    d = req(url) or {}
    cands = [a for a in d.get("data", [])
             if PC_MIN <= (a.get("paperCount") or 0) <= PC_MAX]
    return cands[:MAX_CANDIDATES]

def batch_papers(ids):
    out = {}
    for i in range(0, len(ids), 100):
        url = BATCH_URL + "?fields=name,affiliations,paperCount,papers.venue,papers.year,papers.title"
        res = req(url, data={"ids": ids[i:i + 100]}) or []
        for a in res:
            if a:
                out[a["authorId"]] = a
        time.sleep(0.3 if API_KEY else 1.0)
    return out

def main():
    experts = json.load(open(EXPERTS_FILE, encoding="utf-8"))["experts"]
    lines = ["# 大牛库 · Profile 查漏报告\n",
             "_⚠️ = 有 usable security/HCI 会议论文但尚未绑定,疑似漏绑;请人工确认后加入 experts.json_",
             "_局限:仅按会议 venue 认领;只发 arXiv 的新 profile 可能漏检_\n"]
    for e in experts:
        name, bound = e["name"], set(e["ss_author_ids"])
        cands = search_candidates(name)
        info = batch_papers([a["authorId"] for a in cands])
        rows = []
        for aid, a in info.items():
            hits = [p for p in (a.get("papers") or []) if field_hit(p.get("venue"))]
            if not hits:
                continue
            years = [p.get("year") for p in hits if p.get("year")]
            sample = sorted(hits, key=lambda x: x.get("year") or 0, reverse=True)[0]
            rows.append({
                "aid": aid, "n": len(hits), "recent": max(years) if years else "?",
                "bound": aid in bound, "aff": ";".join(a.get("affiliations") or [])[:24],
                "title": (sample.get("title") or "")[:60],
            })
        rows.sort(key=lambda r: (r["bound"], -r["n"]))   # 未绑在前,命中多在前
        missing = [r for r in rows if not r["bound"]]
        lines.append(f"## {name} — 已绑 {len(bound)}，扫到 {len(rows)} 个含领域论文的 profile"
                     + (f"，⚠️ {len(missing)} 个疑似漏绑" if missing else "，无漏绑"))
        for r in rows:
            mark = "✅已绑" if r["bound"] else "⚠️疑似漏绑"
            lines.append(f"- {mark} id={r['aid']} | 领域论文 {r['n']} | 最近 {r['recent']}"
                         f" | {r['aff']} | 例:{r['title']}")
        lines.append("")
        print(f"  {name:<20} 已绑{len(bound)} 扫到{len(rows)} 漏绑{len(missing)}")
    open(os.path.join(ROOT, "people", "profile_audit.md"), "w",
         encoding="utf-8").write("\n".join(lines))
    print("报告已写入 people/profile_audit.md")

if __name__ == "__main__":
    print("扫描同名 profile 查漏中...")
    main()
