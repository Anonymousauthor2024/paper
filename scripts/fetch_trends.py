#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch_trends.py — 领域"新趋势"分析(区别于大牛库的"最新工作")。

样本(高信噪源,避免四大会系统安全论文的噪声):
  security 领域: SOUPS + PETS 全部论文(usable security/privacy 专会)
  hci 领域    : CHI 中 privacy/security 相关论文(venue + query 过滤)

两个趋势信号:
  1. 新兴关键词: 近 2 年(2024-2026)相对基线(2020-2023)文档频率增长最快的主题词
  2. 引用增速  : 近年论文按年均被引(citationCount / 论文年龄)排序的高影响工作

只用标准库。可选 S2_API_KEY。
输出: security/trends/latest.md, hci/trends/latest.md, data/trends.json
"""
import json, os, re, time, urllib.request, urllib.parse, urllib.error
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"
API_KEY = os.environ.get("S2_API_KEY")
YEARS = "2020-2026"
CUR_YEAR = 2026
SPLIT_YEAR = 2024          # >= 为 recent, < 为 baseline
FIELDS = "title,year,venue,citationCount"

SEC_VENUES = ["Symposium On Usable Privacy and Security",
              "Proceedings on Privacy Enhancing Technologies"]
HCI_VENUE = "International Conference on Human Factors in Computing Systems"
# 全用单词 OR;多词短语(如 data protection)会被 SS 当成 AND,不要放进来
HCI_QUERY = "privacy | security | surveillance | consent | confidentiality | anonymity"

STOP = set("""a an the of to in on for and or with without via using use uses used
understanding toward towards how what when why do does did are is be being been am
study studies design designing evaluate evaluating evaluation analysis empirical
experience experiences practice practices case between across their its it can we our
this that from into more less new understand people paper approach method methods
mixed qualitative quantitative based among within role support effect way help making
make first through about over under against user users human factors computing systems
exploring examining investigating characterizing understanding towards insights lessons
not beyond navigating challenges perspectives implications rethinking sok
""".split())

def terms(title):
    ws = re.findall(r"[a-z][a-z0-9-]+", (title or "").lower())
    ws = [w for w in ws if len(w) > 2 and w not in STOP]
    out = set(ws)
    for a, b in zip(ws, ws[1:]):
        out.add(a + " " + b)
    return out

def req(params):
    # 用 %20 编码空格(默认的 + 会被 SS query 当成 AND 操作符)
    url = BULK_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
    headers = {"x-api-key": API_KEY} if API_KEY else {}
    r = urllib.request.Request(url, headers=headers)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            time.sleep(5 * (attempt + 1) if e.code == 429 else 3)
        except Exception:
            time.sleep(3)
    return {}

def bulk(venue, query=None):
    out, token = [], None
    while True:
        p = {"venue": venue, "year": YEARS, "fields": FIELDS}
        if query:
            p["query"] = query
        if token:
            p["token"] = token
        d = req(p)
        out.extend(d.get("data") or [])
        token = d.get("token")
        if not token or len(out) >= 6000:
            break
        time.sleep(0.3 if API_KEY else 1.0)
    return out

def dedup(papers):
    seen = {}
    for p in papers:
        if p.get("paperId") or p.get("title"):
            seen[p.get("paperId") or p.get("title")] = p
    return list(seen.values())

# ---------- 趋势计算 ----------
def emerging_terms(papers):
    base_df, rec_df = Counter(), Counter()
    base_n = rec_n = 0
    for p in papers:
        y = p.get("year") or 0
        recent = y >= SPLIT_YEAR
        if recent:
            rec_n += 1
        elif y:
            base_n += 1
        else:
            continue
        for t in terms(p.get("title")):
            (rec_df if recent else base_df)[t] += 1
    base_n = base_n or 1
    scored = []
    for t, rc in rec_df.items():
        if rc < 5:                       # 近期至少 5 篇提到,过滤偶发
            continue
        base_rate = base_df[t] / base_n
        rec_rate = rc / (rec_n or 1)
        growth = rec_rate / (base_rate + 1.0 / base_n)   # 平滑
        scored.append((t, rc, base_df[t], round(growth, 1)))
    emerging = sorted(scored, key=lambda x: -x[3])[:15]           # 增长最快
    hottest = sorted(scored, key=lambda x: -x[1])[:15]            # 近期最高频
    return emerging, hottest, base_n, rec_n

def citation_velocity(papers, top=15):
    rows = []
    for p in papers:
        y = p.get("year") or 0
        c = p.get("citationCount") or 0
        if y >= 2022 and c > 0:
            rows.append((round(c / (CUR_YEAR - y + 1), 1), c, y,
                         (p.get("venue") or "-")[:26], p.get("title") or ""))
    return sorted(rows, key=lambda x: -x[0])[:top]

# ---------- 输出 ----------
def render(title, papers):
    emerging, hottest, bn, rn = emerging_terms(papers)
    vel = citation_velocity(papers)
    L = [title, "",
         f"_样本 {len(papers)} 篇（基线 {bn} 篇 2020-{SPLIT_YEAR-1} / 近期 {rn} 篇 {SPLIT_YEAR}-{CUR_YEAR}）_", ""]
    L.append("## 新兴关键词（近 2 年文档频率增长最快）")
    for t, rc, bc, g in emerging:
        L.append(f"- **{t}** — 近期 {rc} 篇 / 基线 {bc} 篇，增长 ×{g}")
    L += ["", "## 近期最热主题词"]
    L.append("　".join(f"{t}({rc})" for t, rc, _, _ in hottest))
    L += ["", "## 引用增速最快（近年高影响工作，按年均被引）"]
    for cy, c, y, v, t in vel:
        L.append(f"- {y} | {v} | 年均 {cy}（共 {c}）— **{t}**")
    return "\n".join(L) + "\n"

def main():
    print("拉取 SOUPS + PETS ...")
    sec = dedup(sum((bulk(v) for v in SEC_VENUES), []))
    print(f"  security 样本 {len(sec)} 篇")
    print("拉取 CHI(privacy/security) ...")
    hci = dedup(bulk(HCI_VENUE, HCI_QUERY))
    print(f"  hci 样本 {len(hci)} 篇")

    open(os.path.join(ROOT, "security", "trends", "latest.md"), "w", encoding="utf-8"
         ).write(render("# 安全领域 · 新趋势（SOUPS + PETS）", sec))
    open(os.path.join(ROOT, "hci", "trends", "latest.md"), "w", encoding="utf-8"
         ).write(render("# HCI 领域 · 隐私安全新趋势（CHI）", hci))
    json.dump({"security_n": len(sec), "hci_n": len(hci)},
              open(os.path.join(ROOT, "data", "trends.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print("输出已写入 security/trends/ · hci/trends/ · data/")

if __name__ == "__main__":
    main()
