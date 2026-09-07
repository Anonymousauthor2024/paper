#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_experts.py — 拉取大牛库(people/experts.json)中每位学者的论文,
跨 profile 去重、按 venue 归类(security / hci / preprint / other),
并为 2026+ 新工作模块补充 focus_area(security / hci / other),
直接呈现每位大牛的最近论文(方向从标题一目了然,不做机器关键词提炼)。

只用标准库,方便在 GitHub Actions 上跑。
可选环境变量 S2_API_KEY 提高 Semantic Scholar 限额。

输出:
  data/experts_papers.json      全量结构化数据(去重后)
  people/latest_by_expert.md    按大牛分组的最近论文(看各自在做什么方向)
  security/experts/latest.md    所有大牛在安全会议的近期论文
  hci/experts/latest.md         所有大牛在 CHI/CSCW 的近期论文
"""
import json, os, re, time, urllib.request, urllib.error
from datetime import datetime, timezone, date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXPERTS_FILE = os.path.join(ROOT, "people", "experts.json")
PAPERS_URL = "https://api.semanticscholar.org/graph/v1/author/{}/papers"
FIELDS = "paperId,title,year,venue,publicationDate,externalIds,url,abstract"
RECENT_MONTHS = 18     # 最近动向窗口(usable security 出版周期长,放宽到 18 个月)
LOOKBACK_YEARS = 4     # 清单显示的年份下限
API_KEY = os.environ.get("S2_API_KEY")

# ---------- venue 分类 ----------
SEC_PATTERNS = [
    "usenix security", "computer and communications security",
    "network and distributed system", "ndss",
    "ieee symposium on security", "symposium on security and privacy",
    "usable privacy and security", "soups",
    "privacy enhancing technologies", "proceedings on privacy",
    "popets", "euro s&p", "european symposium on security",
]
HCI_PATTERNS = [
    "human factors in computing", "chi conference", "chi extended",
    "computer-supported cooperative", "cscw",
    "acm on human-computer interaction",
    "ubicomp", "interactive, mobile, wearable", "imwut",
    "designing interactive systems",
]

# 只用于给 arXiv 预印本做领域相关判断(挡掉 SS 混入的无关同名论文)。
# 刻意只留高特异词,不放 tracking/data/online 这类会误命中 CV/系统论文的宽词。
DOMAIN_WORDS = set("""privacy security secure surveillance phishing scam scams fraud
authentication password encryption biometric deepfake consent usable iot llm chatbot
misinformation disinformation warning warnings harassment sextortion cyberbullying
trafficking gambling deaf disability disabilities accessibility children child elder
senior anonymity anonymous""".split())

SECURITY_WORDS = set("""privacy security secure surveillance phishing scam scams fraud
authentication password encryption biometric deepfake consent misinformation disinformation
warning warnings harassment sextortion cyberbullying trafficking gambling anonymity anonymous
malware vulnerability vulnerabilities threat threats risk risks safety online abuse abuse
policy policies""".split())

HCI_WORDS = set("""hci human computer interaction interactions user users usability usable
accessibility accessible disability disabilities deaf elder senior child children chatbot
llm ai agent agents vr ar mobile wearable embodied social community communities moderation
human-ai interface interfaces design study interview survey qualitative experiment""".split())

def classify(venue, ext, title):
    v = " " + (venue or "").lower() + " "
    for p in SEC_PATTERNS:
        if p in v:
            return "security"
    for p in HCI_PATTERNS:
        if p in v:
            return "hci"
    if ext and ext.get("ArXiv"):
        toks = set(re.findall(r"[a-z]+", (title or "").lower()))
        return "preprint" if toks & DOMAIN_WORDS else "other"
    return "other"

def focus_area(category, title):
    if category == "security":
        return "security"
    if category == "hci":
        return "hci"
    if category != "preprint":
        return "other"
    toks = set(re.findall(r"[a-z]+", (title or "").lower()))
    sec_score = len(toks & SECURITY_WORDS)
    hci_score = len(toks & HCI_WORDS)
    if sec_score == 0 and hci_score == 0:
        return "other"
    return "security" if sec_score > hci_score else "hci"

# ---------- 时间 ----------
TODAY = datetime.now(timezone.utc).date()

def paper_date(p):
    pd = p.get("publicationDate")
    if pd:
        try:
            return date.fromisoformat(pd)
        except ValueError:
            pass
    y = p.get("year")
    return date(y, 7, 1) if y else None

def is_recent(p):
    d = paper_date(p)
    return d is not None and (TODAY - d).days <= RECENT_MONTHS * 31

# ---------- 抓取 ----------
def fetch(url):
    req = urllib.request.Request(url)
    if API_KEY:
        req.add_header("x-api-key", API_KEY)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=40) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            time.sleep(5 * (attempt + 1) if e.code == 429 else 3)
        except Exception:
            time.sleep(3)
    return {}

def fetch_author_papers(aid):
    out, offset = [], 0
    while True:
        url = f"{PAPERS_URL.format(aid)}?fields={FIELDS}&limit=1000&offset={offset}"
        d = fetch(url)
        batch = d.get("data") or []
        out.extend(batch)
        if len(batch) < 1000 or "next" not in d:
            break
        offset = d["next"]
    return out

# ---------- 主流程 ----------
def main():
    experts = json.load(open(EXPERTS_FILE, encoding="utf-8"))["experts"]
    results = []
    for e in experts:
        by_id = {}
        for aid in e["ss_author_ids"]:
            for p in fetch_author_papers(aid):
                if p.get("paperId"):
                    by_id[p["paperId"]] = p     # 跨 profile 去重
            time.sleep(1.0 if not API_KEY else 0.2)
        papers = list(by_id.values())
        for p in papers:
            p["category"] = classify(p.get("venue"), p.get("externalIds"), p.get("title"))
            p["focus_area"] = focus_area(p["category"], p.get("title"))
        papers.sort(key=lambda x: (paper_date(x) or date(1900, 1, 1)), reverse=True)

        in_field = [p for p in papers if p["category"] != "other"]
        recent = [p for p in in_field if is_recent(p)]
        results.append({
            "name": e["name"], "affiliation": e.get("affiliation"),
            "paper_count": len(papers), "in_field_count": len(in_field),
            "recent_count": len(recent), "papers": papers,
        })
        latest = in_field[0]["title"][:56] if in_field else "-"
        print(f"  {e['name']:<20} {len(in_field):3d} in-field | 近{RECENT_MONTHS}月 {len(recent):2d} | 最近: {latest}")

    write_outputs(results)

TAG = {"security": "[SEC]", "hci": "[HCI]", "preprint": "[arXiv]", "other": "[oth]"}

def paper_line(p, who=None):
    yr = p.get("year") or "?"
    flag = " 🆕" if is_recent(p) else ""
    venue = (p.get("venue") or "").strip() or "—"
    ax = p.get("externalIds", {}).get("ArXiv")
    link = f" (arXiv:{ax})" if ax else ""
    prefix = f"{who} | " if who else ""
    return f"- {yr}{flag} | {TAG[p['category']]} {prefix}{venue[:40]} — **{p.get('title')}**{link}"

def write_outputs(results):
    gen = f"_生成于 {TODAY.isoformat()}；🆕 = 最近 {RECENT_MONTHS} 个月_\n\n"

    # 1) 按大牛分组(只列领域内论文,方向从标题看)
    lines = ["# 大牛库 · 各学者的最近论文\n", gen]
    for r in results:
        lines.append(f"## {r['name']} ({r['affiliation']}) — "
                     f"领域内 {r['in_field_count']} 篇，近 {RECENT_MONTHS} 月 {r['recent_count']} 篇")
        shown = [p for p in r["papers"]
                 if p["category"] != "other" and (p.get("year") or 0) >= TODAY.year - LOOKBACK_YEARS]
        lines += [paper_line(p) for p in shown] or ["_(近年无领域内论文)_"]
        lines.append("")
    open(os.path.join(ROOT, "people", "latest_by_expert.md"), "w",
         encoding="utf-8").write("\n".join(lines))

    # 2) 按领域(security / hci)汇总,合著论文合并成一行列出所有大牛
    for cat, path, title in [
        ("security", os.path.join(ROOT, "security", "experts", "latest.md"),
         "# 大牛 · 安全会议(四大会 + SOUPS/PETS)近期论文"),
        ("hci", os.path.join(ROOT, "hci", "experts", "latest.md"),
         "# 大牛 · HCI(CHI / CSCW)近期论文"),
    ]:
        agg = {}
        for r in results:
            for p in r["papers"]:
                if p["category"] == cat and (p.get("year") or 0) >= TODAY.year - LOOKBACK_YEARS:
                    agg.setdefault(p["paperId"], {"p": p, "who": []})["who"].append(r["name"])
        rows = sorted(agg.values(), key=lambda x: x["p"].get("year") or 0, reverse=True)
        body = "\n".join(paper_line(x["p"], who=", ".join(x["who"])) for x in rows)
        open(path, "w", encoding="utf-8").write(title + "\n\n" + gen + body + "\n")

    # 3) 全量数据
    json.dump({"generated_at": TODAY.isoformat(), "experts": results},
              open(os.path.join(ROOT, "data", "experts_papers.json"), "w",
                   encoding="utf-8"), ensure_ascii=False, indent=2)
    print("输出已写入 people/ · security/experts/ · hci/experts/ · data/")

if __name__ == "__main__":
    print("拉取大牛论文中...")
    main()
