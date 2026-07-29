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
FIELDS = "paperId,title,year,venue,citationCount,abstract,url,externalIds"

# SOUPS/PETS 全收（usable/privacy 专会）；四大会先做宽检索，再用摘要方法证据二次筛选。
SEC_FULL_VENUES = ["Symposium On Usable Privacy and Security",
                   "Proceedings on Privacy Enhancing Technologies"]
SEC_BIG4_VENUES = {
    "USENIX Security": [
        "USENIX Security Symposium",
    ],
    "IEEE S&P": [
        "IEEE Symposium on Security and Privacy",
        "Symposium on Security and Privacy",
    ],
    "ACM CCS": [
        "Conference on Computer and Communications Security",
        "ACM Conference on Computer and Communications Security",
    ],
    "NDSS": [
        "Network and Distributed System Security Symposium",
        "Network and Distributed Systems Security Symposium",
        "NDSS Symposium",
    ],
}
BIG4_QUERIES = (
    "interview | survey | questionnaire",
    "usable | usability",
    '"user study" | "user studies" | "human-centered"',
)
USER_STUDY_METHOD_TERMS = (
    "interview", "interviews", "interviewed", "survey", "surveys", "surveyed",
    "questionnaire", "questionnaires", "user study", "user studies",
    "participant", "participants", "human subject", "human subjects",
    "focus group", "focus groups", "field study", "field studies",
    "qualitative study", "mixed-method", "mixed method", "controlled study",
    "usability study", "usability evaluation", "human-centered",
)
USABLE_SCOPE_TERMS = (
    "usable", "usability", "user", "users", "human", "people", "participant",
    "developer", "developers", "operator", "operators", "practitioner",
    "practitioners", "clinician", "analyst", "awareness", "advice",
    "warning", "warnings", "perception", "perceptions", "behavior",
    "behaviour", "practice", "practices", "experience", "experiences",
)
HCI_VENUE = "International Conference on Human Factors in Computing Systems"
# 全用单词 OR;多词短语(如 data protection)会被 SS 当成 AND,不要放进来
HCI_QUERY = "privacy | security | surveillance | consent | confidentiality | anonymity"
TOPIC_RULES_FILE = os.path.join(ROOT, "data", "topic_rules.json")

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

def norm_text(s):
    return (s or "").lower()

def load_topic_rules():
    try:
        rules = json.load(open(TOPIC_RULES_FILE, encoding="utf-8"))
        return rules.get("topics") or []
    except Exception:
        return [{"key": "other_review", "label": "Other / needs review", "keywords": []}]

def topic_for_title(title, venue, topics):
    text = f"{title or ''} {venue or ''}".lower()
    for topic in topics:
        if topic.get("key") == "other_review":
            continue
        for kw in topic.get("keywords", []):
            kw = kw.lower()
            if " " in kw or "-" in kw:
                hit = kw in text
            else:
                hit = re.search(rf"\b{re.escape(kw)}\b", text) is not None
            if hit:
                return topic["key"]
    return "other_review"

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

def is_big4_usable_user_study(p):
    """Keep papers with both a human/usability scope signal and a user-study method signal."""
    text = f"{p.get('title') or ''} {p.get('abstract') or ''}".lower()
    method_hit = any(term in text for term in USER_STUDY_METHOD_TERMS)
    scope_hit = any(term in text for term in USABLE_SCOPE_TERMS)
    return method_hit and scope_hit

def bulk_big4(query=None):
    rows = []
    for canonical, aliases in SEC_BIG4_VENUES.items():
        for venue in aliases:
            for p in bulk(venue, query):
                p["_big4_venue"] = canonical
                rows.append(p)
    return dedup(rows)

def bulk_big4_usable():
    candidates = []
    for query in BIG4_QUERIES:
        candidates.extend(bulk_big4(query))
    return [p for p in dedup(candidates) if is_big4_usable_user_study(p)]

def venue_year_counts(papers):
    counts = {}
    for p in papers:
        venue = p.get("_big4_venue") or p.get("venue") or "Unknown"
        year = str(p.get("year") or "unknown")
        counts.setdefault(venue, {})
        counts[venue][year] = counts[venue].get(year, 0) + 1
    return counts

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
            rows.append({
                "paperId": p.get("paperId"),
                "title": p.get("title") or "",
                "year": y,
                "venue": p.get("venue") or "-",
                "citations": c,
                "citations_per_year": round(c / (CUR_YEAR - y + 1), 1),
                "abstract": p.get("abstract"),
                "url": p.get("url"),
                "externalIds": p.get("externalIds") or {},
            })
    return sorted(rows, key=lambda x: -x["citations_per_year"])[:top]

def block_data(key, label, papers):
    emerging, hottest, bn, rn = emerging_terms(papers)
    return {
        "key": key,
        "label": label,
        "sample": {
            "total": len(papers),
            "baseline": bn,
            "recent": rn,
            "baseline_years": f"2020-{SPLIT_YEAR-1}",
            "recent_years": f"{SPLIT_YEAR}-{CUR_YEAR}",
        },
        "emerging": [
            {"term": t, "recent": rc, "baseline": bc, "growth": g}
            for t, rc, bc, g in emerging
        ],
        "hottest": [
            {"term": t, "recent": rc}
            for t, rc, _, _ in hottest
        ],
        "papers": citation_velocity(papers),
    }

def yearly_topic_counts(groups, topics):
    labels = {t["key"]: t["label"] for t in topics}
    out = {}
    for group, papers in groups.items():
        yearly = {}
        totals = Counter()
        for p in papers:
            y = p.get("year")
            if not y:
                continue
            topic = topic_for_title(p.get("title"), p.get("venue"), topics)
            yearly.setdefault(str(y), Counter())[topic] += 1
            totals[str(y)] += 1
        out[group] = {
            "totals": dict(totals),
            "topics": {
                y: {
                    k: {"label": labels.get(k, k), "count": c}
                    for k, c in counts.items()
                }
                for y, counts in yearly.items()
            }
        }
    return out

def popular_topics(yearly, group, year):
    y = str(year)
    g = yearly.get(group, {})
    total = (g.get("totals") or {}).get(y, 0)
    topics = (g.get("topics") or {}).get(y, {})
    if not total or not topics:
        return {}
    threshold = max(2, int(round(total * 0.03)))
    return {
        key: data
        for key, data in topics.items()
        if data["count"] >= threshold and key != "other_review"
    }

def lag_migration(yearly):
    labels = {}
    for g in yearly.values():
        for topics in (g.get("topics") or {}).values():
            for key, data in topics.items():
                labels[key] = data.get("label", key)
    sources = [
        ("soups_pets", "SOUPS/PETS"),
        ("hci_privacy_security", "HCI privacy/security"),
    ]
    rows = []
    seen = set()
    for source_key, source_label in sources:
        for source_year in range(2020, CUR_YEAR):
            src = popular_topics(yearly, source_key, source_year)
            if not src:
                continue
            for lag in (1, 2):
                target_year = source_year + lag
                if target_year > CUR_YEAR:
                    continue
                tgt = popular_topics(yearly, "security_big4_all", target_year)
                for topic, src_data in src.items():
                    if topic not in tgt:
                        continue
                    key = (source_key, source_year, target_year, topic)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append({
                        "topic": topic,
                        "label": labels.get(topic, topic),
                        "source_group": source_key,
                        "source_label": source_label,
                        "source_year": source_year,
                        "source_count": src_data["count"],
                        "target_group": "security_big4_all",
                        "target_label": "安全四大",
                        "target_year": target_year,
                        "target_count": tgt[topic]["count"],
                        "lag_years": lag,
                        "signal": "strong" if lag == 1 else "medium",
                    })
    rows.sort(key=lambda r: (r["lag_years"], -r["target_count"], -r["source_count"], r["label"]))
    source_only = []
    for source_key, source_label in sources:
        for source_year in (2024, 2025):
            src = popular_topics(yearly, source_key, source_year)
            for topic, src_data in src.items():
                future_hit = any(
                    topic in popular_topics(yearly, "security_big4_all", y)
                    for y in range(source_year + 1, CUR_YEAR + 1)
                )
                if not future_hit:
                    source_only.append({
                        "topic": topic,
                        "label": labels.get(topic, topic),
                        "source_group": source_key,
                        "source_label": source_label,
                        "source_year": source_year,
                        "source_count": src_data["count"],
                        "signal": "watch",
                    })
    return {"migrations": rows[:20], "source_only_watchlist": source_only[:20]}

def first_popular_topic(yearly, group, topic):
    """Return the first year where topic is popular in a group."""
    for year in range(2020, CUR_YEAR + 1):
        popular = popular_topics(yearly, group, year)
        if topic in popular:
            data = popular[topic]
            return {"year": year, "count": data["count"], "label": data.get("label", topic)}
    return None

def topic_count(yearly, group, year, topic):
    return (((yearly.get(group) or {}).get("topics") or {}).get(str(year)) or {}).get(topic, {}).get("count", 0)

def first_big4_usable_appearance(yearly, topic):
    """Return first Big4 usable/user-study year where topic appears at least once."""
    for year in range(2020, CUR_YEAR + 1):
        count = topic_count(yearly, "security_big4_usable", year, topic)
        if count > 0:
            return {"year": year, "count": count}
    return None

def first_hot_migration(yearly):
    """Detect topic transfer when source first-hot precedes Big4 user-study zero-to-one entry."""
    labels = {}
    for g in yearly.values():
        for topics in (g.get("topics") or {}).values():
            for key, data in topics.items():
                labels[key] = data.get("label", key)

    sources = [
        ("soups_pets", "SOUPS/PETS"),
        ("hci_privacy_security", "HCI privacy/security"),
    ]
    all_topics = sorted(k for k in labels if k != "other_review")
    verified = []
    watchlist = []
    mainstream = []

    for topic in all_topics:
        big4_first = first_big4_usable_appearance(yearly, topic)
        source_hits = []
        for source_key, source_label in sources:
            hit = first_popular_topic(yearly, source_key, topic)
            if hit:
                source_hits.append((source_key, source_label, hit))

        if not source_hits:
            if big4_first:
                mainstream.append({
                    "topic": topic,
                    "label": labels.get(topic, topic),
                    "target_group": "security_big4_usable",
                    "target_label": "安全四大用户研究",
                    "target_year": big4_first["year"],
                    "target_count": big4_first["count"],
                    "reason": "big4_only_or_first",
                })
            continue

        if not big4_first:
            for source_key, source_label, hit in source_hits:
                watchlist.append({
                    "topic": topic,
                    "label": labels.get(topic, topic),
                    "source_group": source_key,
                    "source_label": source_label,
                    "source_year": hit["year"],
                    "source_count": hit["count"],
                    "signal": "watch",
                    "judgment": "source_hot_big4_not_yet",
                })
            continue

        verified_any = False
        for source_key, source_label, hit in source_hits:
            lag = big4_first["year"] - hit["year"]
            if 1 <= lag <= 2:
                verified_any = True
                verified.append({
                    "topic": topic,
                    "label": labels.get(topic, topic),
                    "source_group": source_key,
                    "source_label": source_label,
                    "source_year": hit["year"],
                    "source_count": hit["count"],
                    "target_group": "security_big4_usable",
                    "target_label": "安全四大用户研究",
                    "target_year": big4_first["year"],
                    "target_count": big4_first["count"],
                    "lag_years": lag,
                    "signal": "strong" if lag == 1 else "medium",
                    "judgment": "source_first_then_big4_breakthrough",
                })

        if not verified_any:
            earliest_source = min(source_hits, key=lambda x: x[2]["year"])
            source_key, source_label, hit = earliest_source
            mainstream.append({
                "topic": topic,
                "label": labels.get(topic, topic),
                "source_group": source_key,
                "source_label": source_label,
                "source_year": hit["year"],
                "source_count": hit["count"],
                "target_group": "security_big4_usable",
                "target_label": "安全四大用户研究",
                "target_year": big4_first["year"],
                "target_count": big4_first["count"],
                "lag_years": big4_first["year"] - hit["year"],
                "reason": "big4_first_or_lag_too_long",
            })

    verified.sort(key=lambda r: (r["lag_years"], -r["target_count"], -r["source_count"], r["label"]))
    watchlist.sort(key=lambda r: (-r["source_year"], -r["source_count"], r["label"]))
    mainstream.sort(key=lambda r: (r.get("target_year") or 9999, r["label"]))
    return {
        "migrations": verified[:20],
        "verified_transmissions": verified[:20],
        "source_only_watchlist": watchlist[:20],
        "big4_first_or_mainstream": mainstream[:20],
        "method": "source first-hot + Big4 user-study zero-to-one: source first-hot must be earlier than the first Big4 usable/user-study appearance, with a 1-2 year lag.",
    }

# ---------- 输出 ----------
def paper_url(p):
    arxiv = (p.get("externalIds") or {}).get("ArXiv")
    return f"https://arxiv.org/abs/{arxiv}" if arxiv else (p.get("url") or "")

def render_block(block, curated):
    sample = block["sample"]
    themes = curated.get("blocks", {}).get(block["key"], {}).get("themes", [])
    summaries = curated.get("papers", {})
    L = [f"## {block['label']}",
         f"_样本 {sample['total']} 篇（基线 {sample['baseline']} 篇 {sample['baseline_years']} / "
         f"近期 {sample['recent']} 篇 {sample['recent_years']}）_", "",
         "### 趋势解读"]
    for theme in themes:
        L.append(f"- **{theme['title']}**：{theme['summary']}")
    L += ["", "### 引用增速最快的代表论文（Top 5）"]
    for p in block["papers"][:5]:
        curated_paper = summaries.get(p.get("paperId") or "", {})
        summary = curated_paper.get("summary")
        if not summary:
            summary = "暂无人工核对的中文简介；请查看原始摘要。"
        url = curated_paper.get("source_url") or paper_url(p)
        title = f"[{p['title']}]({url})" if url else p["title"]
        L.append(
            f"- **{title}**（{p['year']}，年均 {p['citations_per_year']}，共 {p['citations']}）"
            f"——{summary}"
        )
    L += ["", "### 其余高增速论文（6–15）"]
    for p in block["papers"][5:15]:
        url = paper_url(p)
        title = f"[{p['title']}]({url})" if url else p["title"]
        L.append(f"- {p['year']} | 年均 {p['citations_per_year']} — **{title}**")
    L += ["", "### 数据依据：新兴关键词"]
    for row in block["emerging"]:
        L.append(
            f"- **{row['term']}** — 近期 {row['recent']} 篇 / "
            f"基线 {row['baseline']} 篇，增长 ×{row['growth']}"
        )
    L += ["", "### 数据依据：近期高频词"]
    L.append("　".join(f"{row['term']}({row['recent']})" for row in block["hottest"]))
    return "\n".join(L) + "\n"

def main():
    print("安全·SOUPS/PETS ...")
    soups_pets = dedup(sum((bulk(v) for v in SEC_FULL_VENUES), []))
    print("安全·四大会 usable/user-study 宽检索 + 方法证据筛选 ...")
    big4_usable = bulk_big4_usable()
    print("安全·子领域: SOUPS+PETS + 四大会 usable/user-study ...")
    sec_sub = dedup(soups_pets + big4_usable)
    print("安全·整体: 四大会全部 ...")
    sec_all = bulk_big4()
    print("HCI·子领域: CHI 隐私安全 ...")
    hci_sub = dedup(bulk(HCI_VENUE, HCI_QUERY))
    print("HCI·整体: 全 CHI ...")
    hci_all = dedup(bulk(HCI_VENUE))
    print(f"  样本 安全 子{len(sec_sub)}/整体{len(sec_all)} · HCI 子{len(hci_sub)}/整体{len(hci_all)}")

    blocks = [
        block_data("security_sub", "子领域 · usable security（SOUPS + PETS + 四大会 usable/user study）", sec_sub),
        block_data("security_all", "整体 · 安全四大会全部（USENIX / S&P / CCS / NDSS）", sec_all),
        block_data("hci_sub", "子领域 · 隐私安全（CHI + privacy/security 过滤）", hci_sub),
        block_data("hci_all", "整体 · 全 CHI", hci_all),
    ]
    topics = load_topic_rules()
    yearly = yearly_topic_counts({
        "security_big4_all": sec_all,
        "security_big4_usable": big4_usable,
        "soups_pets": soups_pets,
        "hci_privacy_security": hci_sub,
    }, topics)
    migration = first_hot_migration(yearly)
    curated_path = os.path.join(ROOT, "data", "trend_summaries_zh.json")
    with open(curated_path, encoding="utf-8") as f:
        curated = json.load(f)
    sec_md = ("# 安全领域 · 新趋势\n\n"
              + render_block(blocks[0], curated)
              + "\n" + render_block(blocks[1], curated))
    hci_md = ("# HCI 领域 · 新趋势\n\n"
              + render_block(blocks[2], curated)
              + "\n" + render_block(blocks[3], curated))
    open(os.path.join(ROOT, "security", "trends", "latest.md"), "w", encoding="utf-8").write(sec_md)
    open(os.path.join(ROOT, "hci", "trends", "latest.md"), "w", encoding="utf-8").write(hci_md)
    with open(os.path.join(ROOT, "data", "trends.json"), "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%d"),
            "method": "2024–2026 相对 2020–2023 的标题词频增长；引用增速为总引用数除以论文年龄；四大会 usable 子集先用 interview/survey/questionnaire/usable/user study/human-centered 宽检索，再要求摘要同时出现人本范围和用户研究方法证据。",
            "big4_definition": {
                "venues": list(SEC_BIG4_VENUES.keys()),
                "venue_aliases": SEC_BIG4_VENUES,
                "queries": list(BIG4_QUERIES),
                "filter": "human/usability scope term AND user-study method term",
                "counts_by_venue_year": venue_year_counts(big4_usable),
            },
            "blocks": blocks,
            "yearly_topics": yearly,
            "migration_method": "source first-hot + Big4 user-study zero-to-one: first popular year in SOUPS/PETS or HCI privacy/security must be earlier than the first year where the topic appears at least once in the security Big4 usable/user-study subset, and the lag must be 1-2 years.",
            "topic_migration": migration,
        }, f, ensure_ascii=False, indent=2)
    print("输出已写入 security/trends/ · hci/trends/ · data/")

if __name__ == "__main__":
    main()
