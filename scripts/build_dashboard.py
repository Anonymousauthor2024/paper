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
from collections import Counter
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
        if line.startswith("### "):
            if in_ul: out.append("</ul>"); in_ul = False
            out.append(f"<h4>{m[4:]}</h4>")
        elif line.startswith("## "):
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

def trend_paper_url(p, curated_paper):
    if curated_paper.get("source_url"):
        return curated_paper["source_url"]
    ax = (p.get("externalIds") or {}).get("ArXiv")
    if ax:
        return f"https://arxiv.org/abs/{ax}"
    return p.get("url") or "#"

def trend_block_html(block, curated):
    sample = block["sample"]
    block_notes = (curated.get("blocks") or {}).get(block["key"], {})
    paper_notes = curated.get("papers") or {}

    themes = "".join(
        f'<li><strong>{html.escape(t["title"])}</strong>'
        f'<span>{html.escape(t["summary"])}</span></li>'
        for t in block_notes.get("themes", [])
    )
    top_papers = []
    for p in block["papers"][:5]:
        note = paper_notes.get(p.get("paperId") or "", {})
        summary = note.get("summary") or "暂无人工核对的中文简介；请查看原始摘要。"
        url = trend_paper_url(p, note)
        top_papers.append(
            '<article class="trend-paper">'
            f'<div class="paper-meta">{p["year"]} · 年均被引 {p["citations_per_year"]}'
            f' · 总引用 {p["citations"]}</div>'
            f'<a href="{html.escape(url)}" target="_blank">{html.escape(p["title"])}</a>'
            f'<p>{html.escape(summary)}</p></article>'
        )
    rest = "".join(
        f'<li><span>{p["year"]} · 年均 {p["citations_per_year"]}</span> '
        f'<a href="{html.escape(trend_paper_url(p, {}))}" target="_blank">'
        f'{html.escape(p["title"])}</a></li>'
        for p in block["papers"][5:15]
    )
    emerging = "　".join(
        f'{html.escape(row["term"])}（近期 {row["recent"]} / 基线 {row["baseline"]}'
        f'，×{row["growth"]}）'
        for row in block["emerging"]
    )
    hottest = "　".join(
        f'{html.escape(row["term"])}（{row["recent"]}）'
        for row in block["hottest"]
    )
    return f"""
<div class="trend-block">
  <h3>{html.escape(block["label"])}</h3>
  <p class="muted">样本 {sample["total"]} 篇（基线 {sample["baseline"]} 篇
  {sample["baseline_years"]} / 近期 {sample["recent"]} 篇 {sample["recent_years"]}）</p>
  <h4>趋势解读</h4>
  <ul class="theme-list">{themes}</ul>
  <h4>引用增速最快的代表论文</h4>
  <div class="trend-papers">{''.join(top_papers)}</div>
  <details><summary>查看其余高增速论文（6–15）</summary><ul class="rest-papers">{rest}</ul></details>
  <details class="evidence"><summary>查看关键词数据依据</summary>
    <p><b>增长最快：</b>{emerging}</p>
    <p><b>近期高频：</b>{hottest}</p>
  </details>
</div>"""

def security_migration_html(trends):
    mig = (trends.get("topic_migration") or {}).get("migrations") or []
    watch = (trends.get("topic_migration") or {}).get("source_only_watchlist") or []
    yearly = trends.get("yearly_topics") or {}
    if not mig and not watch:
        return ""

    def topic_count(group, year, topic):
        return (((yearly.get(group) or {}).get("topics") or {}).get(str(year)) or {}).get(topic, {}).get("count", 0)

    def bars(group, topic):
        vals = [(y, topic_count(group, y, topic)) for y in range(2020, 2027)]
        max_v = max([v for _, v in vals] or [1]) or 1
        cells = []
        for y, v in vals:
            h = max(3, round((v / max_v) * 30)) if v else 2
            cells.append(
                f'<span class="mini-bar" title="{y}: {v} 篇">'
                f'<i style="height:{h}px"></i><em>{str(y)[2:]}</em></span>'
            )
        return "".join(cells)

    cards = []
    for r in mig[:12]:
        signal = "强信号" if r.get("signal") == "strong" else "中等信号"
        topic = r.get("topic") or ""
        cards.append(
            '<article class="migration-card">'
            f'<div class="migration-card-head"><strong>{html.escape(r.get("label") or "")}</strong>'
            f'<span class="signal {html.escape(r.get("signal") or "")}">+{r.get("lag_years")} 年 · {signal}</span></div>'
            '<div class="migration-flow">'
            f'<span>{html.escape(r.get("source_label") or "")} {r.get("source_year")}<b>{r.get("source_count")}</b></span>'
            '<span class="arrow">→</span>'
            f'<span>安全四大 {r.get("target_year")}<b>{r.get("target_count")}</b></span>'
            '</div>'
            '<div class="bar-rows">'
            f'<div><label>{html.escape(r.get("source_label") or "")}</label><p>{bars(r.get("source_group"), topic)}</p></div>'
            f'<div><label>安全四大</label><p>{bars("security_big4_all", topic)}</p></div>'
            '</div></article>'
        )
    watch_items = "".join(
        '<li>'
        f'<span><strong>{html.escape(r.get("label") or "")}</strong>'
        f'<em>{html.escape(r.get("source_label") or "")} {r.get("source_year")} 热，暂未见四大跟进</em></span>'
        f'<b style="width:{min(100, (r.get("source_count") or 0) * 8)}%"></b>'
        f'<i>{r.get("source_count")} 篇</i>'
        '</li>'
        for r in watch[:8]
    )
    watch_html = ""
    if watch_items:
        watch_html = (
            '<details class="migration-watch"><summary>只在 SOUPS/PETS 或 HCI 先热的观察名单</summary>'
            f'<ul>{watch_items}</ul></details>'
        )
    cards_html = f'<div class="migration-cards">{"".join(cards)}</div>' if cards else ""
    return (
        '<div class="migration-block">'
        '<h3>安全四大 vs SOUPS/PETS · 话题迁移</h3>'
        '<p class="muted">判定口径：某话题先在 SOUPS/PETS 或 HCI privacy/security 的某一年变热，'
        '随后 1–2 年内在安全四大变热，记为滞后迁移信号。</p>'
        f'{cards_html}{watch_html}</div>'
    )

def paper_url(p):
    ax = (p.get("externalIds") or {}).get("ArXiv")
    if ax:
        return f"https://arxiv.org/abs/{ax}"
    return p.get("url") or "#"

def security_migration_html(trends):
    migration = trends.get("topic_migration") or {}
    verified = migration.get("verified_transmissions") or migration.get("migrations") or []
    watch = migration.get("source_only_watchlist") or []
    mainstream = migration.get("big4_first_or_mainstream") or []
    if not verified and not watch and not mainstream:
        return ""

    def evidence_arrow(r):
        source = r.get("source_label") or "源领域"
        source_year = r.get("source_year")
        source_count = r.get("source_count")
        target_year = r.get("target_year")
        target_count = r.get("target_count")
        if source_year and target_year:
            return (
                f'{html.escape(source)} {source_year} 热（{source_count} 篇）'
                f' → 安全四大用户研究 {target_year} 首次出现（{target_count} 篇）'
            )
        if source_year:
            return f'{html.escape(source)} {source_year} 热（{source_count} 篇），安全四大用户研究尚未出现'
        if target_year:
            return f'安全四大用户研究 {target_year} 已经出现（{target_count} 篇），未观察到更早的源领域 first-hot'
        return "证据不足"

    def card(r, judgment, badge):
        label = html.escape(r.get("label") or "")
        lag = r.get("lag_years")
        lag_html = ""
        if lag is not None:
            if lag > 0:
                lag_text = f"间隔 {lag} 年"
            elif lag == 0:
                lag_text = "同年出现"
            else:
                lag_text = f"Big4 早 {abs(lag)} 年"
            lag_html = f'<span class="migration-badge">{lag_text}</span>'
        return (
            '<article class="migration-card readable">'
            f'<div class="migration-card-head"><strong>{label}</strong>{lag_html}</div>'
            f'<p class="judgment">判断：{html.escape(judgment)}</p>'
            f'<p class="evidence-line">证据：{evidence_arrow(r)}</p>'
            f'<p class="badge-note">{html.escape(badge)}</p>'
            '</article>'
        )

    verified_html = "".join(
        card(
            r,
            "源领域先热，随后 1–2 年在安全四大用户研究子集从 0 到 ≥1；这是可参考的突破路径",
            "优先看它为何能被 Big4 接收：威胁模型、系统证据、可复现性、伦理边界。",
        )
        for r in verified[:8]
    )
    if not verified_html:
        verified_html = (
            '<p class="muted boxed">当前按“源领域先热 + Big4 用户研究从 0 到 ≥1”的口径，仍未发现'
            '“SOUPS/PETS 或 HCI in S&P 先热、1–2 年后安全四大用户研究首次出现”的明确突破信号。</p>'
        )

    watch_html = "".join(
        card(
            r,
            "源领域已热，但安全四大用户研究尚未出现；这是潜在选题池",
            "适合进一步查具体论文：如果能补足系统/攻击面/大规模实证，可能有 Big4 化空间。",
        )
        for r in watch[:10]
    ) or '<p class="muted boxed">当前没有源领域已热但 Big4 用户研究未出现的候选话题。</p>'

    mainstream_html = "".join(
        card(
            r,
            "安全四大用户研究已经先出现，或源领域领先超过 2 年；不按短期突破机会处理",
            "这类更适合作为背景或基准，不应被误判成从 SOUPS/PETS/HCI 进入 Big4 的新机会。",
        )
        for r in mainstream[:10]
    ) or '<p class="muted boxed">当前没有已主流/非短期传导项。</p>'

    return (
        '<div class="migration-block">'
        '<h3>安全四大投稿导向 · 话题传导判断</h3>'
        '<p class="muted">判定口径：先算每个话题在 SOUPS/PETS、HCI privacy/security、'
        '安全四大用户研究子集里的时间顺序。源领域仍用 first-hot；安全四大目标端只看 interview/survey/questionnaire 子集，且只要求从 0 到 ≥1 篇。'
        '只有源领域先热，且安全四大用户研究在 1–2 年内首次出现，才算“可能以用户研究方式突破进入 Big4”。</p>'
        '<div class="migration-section"><h4>1. 已验证突破：可参考四大吸收路径</h4>'
        f'<div class="migration-cards">{verified_html}</div></div>'
        '<div class="migration-section"><h4>2. 潜在机会：源领域已热，安全四大用户研究仍为 0</h4>'
        f'<div class="migration-cards">{watch_html}</div></div>'
        '<details class="migration-section"><summary>3. 已有 Big4 用户研究论文 / 非短期突破：不算机会</summary>'
        f'<div class="migration-cards">{mainstream_html}</div></details>'
        '</div>'
    )

def collect_new_work(experts, since=2026):
    by_id = {}
    for e in experts:
        for p in e.get("papers", []):
            if (p.get("year") or 0) < since:
                continue
            if p.get("category") == "other":
                continue
            area = p.get("focus_area")
            if not area:
                area = "security" if p.get("category") == "security" else "hci"
            if area not in {"security", "hci"}:
                continue
            kind = "preprint" if p.get("category") == "preprint" else "published"
            pid = p.get("paperId") or p.get("title") or ""
            row = by_id.setdefault(pid, {"paper": p, "people": set(), "area": area, "kind": kind})
            row["people"].add(e["name"])
    rows = list(by_id.values())
    rows.sort(key=lambda r: ((r["paper"].get("publicationDate") or ""), r["paper"].get("year") or 0), reverse=True)
    return rows

def _norm_title(t):
    return re.sub(r"[^a-z0-9]+", "", (t or "").lower())

def merge_homepage(rows):
    """把 data/homepage_publications.json 的主页补充论文并进 2026 新工作(按标题去重)。
    S2 已有的合并作者;S2 没有的(主页更新更快)追加。不改抓取逻辑,只在看板层补全。"""
    hp = json.loads(read("data/homepage_publications.json") or "{}")
    index = {}
    for r in rows:
        index.setdefault(_norm_title(r["paper"].get("title")), r)
    for e in hp.get("entries", []):
        key = _norm_title(e.get("title"))
        if key in index:
            index[key]["people"].add(e["author"])
            continue
        venue = e.get("venue") or ""
        kind = "preprint" if "preprint" in venue.lower() else "published"
        area = e.get("focus_area") if e.get("focus_area") in {"security", "hci"} else "hci"
        row = {
            "paper": {"title": e.get("title"), "year": e.get("year"), "venue": venue,
                      "paperId": None, "externalIds": {}, "url": e.get("url"),
                      "publicationDate": f'{e.get("year")}-01-01', "category": area},
            "people": {e["author"]}, "area": area, "kind": kind,
        }
        rows.append(row)
        index[key] = row
    rows.sort(key=lambda r: ((r["paper"].get("publicationDate") or ""),
                             r["paper"].get("year") or 0), reverse=True)
    return rows

def load_topic_rules():
    rules = json.loads(read("data/topic_rules.json") or "{}")
    topics = rules.get("topics") or []
    if topics:
        return topics
    return [{"key": "other_review", "label": "Other / needs review", "keywords": []}]

def classify_topic(row, topics):
    p = row["paper"]
    text = " ".join([
        p.get("title") or "",
        p.get("venue") or "",
        row.get("area") or "",
        " ".join(sorted(row.get("people") or [])),
    ]).lower()
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

def new_work_item(row, tz):
    p = row["paper"]
    kind = row["kind"]
    title = html.escape(p.get("title") or "")
    venue = html.escape((p.get("venue") or ("arXiv" if kind == "preprint" else "—"))[:70])
    people = html.escape(", ".join(sorted(row["people"])))
    zh = html.escape((tz.get(p.get("paperId", "")) or {}).get("zh", ""))
    zh_html = f'<span class="zh">{zh}</span>' if zh else ""
    return (
        f'<li><span class="yr">{p.get("year") or "?"}</span> '
        f'<a href="{html.escape(paper_url(p))}" target="_blank">{title}</a>'
        f'{zh_html}<span class="venue">{venue} · 涉及：{people}</span></li>'
    )

def new_work_topic_html(topic, items, tz, visible=5):
    shown = "".join(new_work_item(r, tz) for r in items[:visible])
    hidden = "".join(new_work_item(r, tz) for r in items[visible:])
    more = ""
    if hidden:
        more = f'<details><summary>展开其余 {len(items) - visible} 篇</summary><ul class="new-work-list">{hidden}</ul></details>'
    return (
        f'<div class="topic-block"><h4>{html.escape(topic["label"])}'
        f'<span>{len(items)} 篇</span></h4><ul class="new-work-list">{shown}</ul>{more}</div>'
    )

def new_work_list(rows, area, kind, tz, topics):
    filtered = [r for r in rows if r["area"] == area and r["kind"] == kind]
    if not filtered:
        return '<p class="muted">暂无 2026 年以来可归类的新工作。</p>'
    grouped = {t["key"]: [] for t in topics}
    for r in filtered:
        grouped.setdefault(classify_topic(r, topics), []).append(r)
    blocks = []
    for topic in topics:
        items = grouped.get(topic["key"]) or []
        if items:
            blocks.append(new_work_topic_html(topic, items, tz))
    return "".join(blocks)

def new_work_html(rows, tz):
    topics = load_topic_rules()
    labels = {
        ("security", "published"): "安全 · 已发表工作",
        ("security", "preprint"): "安全 · 预印本",
        ("hci", "published"): "HCI · 已发表工作",
        ("hci", "preprint"): "HCI · 预印本",
    }
    panels = []
    for area, kind in [("security", "published"), ("security", "preprint"),
                       ("hci", "published"), ("hci", "preprint")]:
        count = sum(1 for r in rows if r["area"] == area and r["kind"] == kind)
        panels.append(
            f'<div class="new-work-panel"><h3>{labels[(area, kind)]}'
            f'<span>{count} 篇</span></h3>{new_work_list(rows, area, kind, tz, topics)}</div>'
        )
    return "".join(panels)

GENAI_THEMES = [
    {
        "key": "chatbot_advice_trust",
        "title": "1. LLM / Chatbot 作为安全与隐私建议来源",
        "summary": "已有工作在看用户是否相信 AI 建议、何时过度信任、AI 在敏感情境中能否给出可靠支持。",
        "big4": "Big4 化时要把“信任”落到错误建议、风险校准、真实决策后果和可审计证据，而不是泛泛讨论体验。",
        "keywords": ["chatbot", "chatbots", "advice", "warning", "warnings", "trust", "trustworthiness", "confidence", "mental health", "survivors"],
    },
    {
        "key": "privacy_inference_control",
        "title": "2. LLM 推断、隐私暴露与用户控制",
        "summary": "已有工作关注模型推断个人信息、对话自我披露、隐私保护数据使用、智能眼镜/家庭场景的细粒度隐私控制。",
        "big4": "Big4 化空间在于把个人信息推断建成威胁模型，并量化用户能否理解、发现和纠正模型推断。",
        "keywords": ["inference", "inferred", "self-disclosure", "privacy", "private information", "privacy-protected", "visual privacy", "smart glass", "elicitation"],
    },
    {
        "key": "synthetic_harms_fraud",
        "title": "3. GenAI 风险、合成媒体、诈骗与滥用",
        "summary": "已有工作包括 deepfake 识别、AI 生成性内容、退款诈骗、青少年 GenAI 风险、AI 生成媒体来源线索。",
        "big4": "Big4 化时要从“用户担忧”推进到攻击链、平台责任、干预效果、跨人群风险差异。",
        "keywords": ["deepfake", "synthetic", "ai-generated", "generated media", "provenance", "refund fraud", "scam", "sexual content", "youth", "risks", "safety"],
    },
    {
        "key": "agent_developer_workflows",
        "title": "4. AI Agent / LLM 工作流中的安全实践",
        "summary": "已有工作看开发者、研究者或安全人员如何在 LLM/agent 工作流中理解、忽视、验证或修复安全问题。",
        "big4": "Big4 化关键是把 workflow artifact 说清楚：谁在什么时间点做什么安全判断，AI 建议如何改变错误率、校准和责任边界。",
        "keywords": ["agent", "agentic", "developer", "developers", "workflow", "workflows", "copilot", "playbook", "auditing", "threat modeling", "vulnerability", "vulnerabilities"],
    },
    {
        "key": "governance_creative_policy",
        "title": "5. GenAI 治理、创作者权益与安全边界",
        "summary": "已有工作讨论创作者 consent / credit / compensation、AI Act 风险监管、企业安全话语和公众理解。",
        "big4": "Big4 化通常需要从规范讨论转为可验证机制：风险分类、平台干预、政策执行漏洞或可测量 harm。",
        "keywords": ["governance", "consent", "credit", "compensation", "ai act", "regulation", "corporate discourse", "artists", "creative", "policy"],
    },
]

GENAI_AI_TERMS = [
    "llm", "large language", "chatbot", "chatgpt", "generative ai", "genai",
    "ai agent", "agentic", "deepfake", "synthetic", "text-to-image",
    "ai-generated", "generated ai", "copilot", "prompt injection",
]
GENAI_USABLE_SECURITY_TERMS = [
    "security", "privacy", "risk", "risks", "safety", "trust", "advice",
    "warning", "warnings", "user", "users", "developer", "developers",
    "participant", "participants", "interview", "survey", "perception",
    "perceptions", "control", "consent", "fraud", "scam", "threat",
    "vulnerability", "audit", "auditing", "provenance", "disclosure",
]

def _paper_year(p):
    return p.get("year") or 0

def _venue_family(venue):
    v = (venue or "").lower()
    if any(x in v for x in ["usenix security", "ieee symposium on security", "computer and communications security", "network and distributed system security"]):
        return "Big4"
    if any(x in v for x in ["usable privacy", "privacy enhancing technologies", "popets", "soups"]):
        return "SOUPS/PETS"
    if any(x in v for x in ["human factors in computing", "chi", "cscw", "designing interactive", "dis"]):
        return "HCI"
    if "arxiv" in v or "preprint" in v:
        return "Preprint"
    if any(x in v for x in ["fairness", "accountability", "facct", "aaai", "acl"]):
        return "AI/FAccT/ML"
    return "Other"

def _method_tag(text):
    if any(k in text for k in ["interview", "qualitative", "participant", "participants", "survey", "perception", "perceptions", "user study"]):
        return "用户研究"
    if any(k in text for k in ["taxonomy", "sok", "framework"]):
        return "分类/框架"
    if any(k in text for k in ["benchmark", "evaluating", "evaluation", "fuzzing", "audit", "auditing", "attack", "jailbreak"]):
        return "系统/评测"
    return "概念/设计"

def _genai_theme(text):
    hits = []
    for theme in GENAI_THEMES:
        score = sum(1 for kw in theme["keywords"] if kw in text)
        if score:
            hits.append((score, theme["key"]))
    if hits:
        hits.sort(reverse=True)
        return hits[0][1]
    return "agent_developer_workflows"

def _is_genai_usable_security(text):
    return (
        any(k in text for k in GENAI_AI_TERMS)
        and any(k in text for k in GENAI_USABLE_SECURITY_TERMS)
    )

def collect_genai_rows(experts, trends):
    rows = {}

    def add(p, people=None, source=None):
        title = p.get("title") or ""
        venue = p.get("venue") or ""
        abstract = p.get("abstract") or ""
        text = f"{title} {venue} {abstract} {' '.join(people or [])}".lower()
        if not _is_genai_usable_security(text):
            return
        key = _norm_title(title)
        if not key:
            return
        row = rows.setdefault(key, {
            "paper": p,
            "people": set(),
            "sources": set(),
            "theme": _genai_theme(text),
            "venue_family": _venue_family(venue),
            "method": _method_tag(text),
        })
        row["people"].update(people or [])
        if source:
            row["sources"].add(source)
        if _paper_year(p) > _paper_year(row["paper"]):
            row["paper"] = p
            row["venue_family"] = _venue_family(venue)
            row["method"] = _method_tag(text)

    for e in experts:
        for p in e.get("papers", []):
            if (p.get("year") or 0) >= 2020:
                add(p, [e.get("name") or ""], "expert")
    hp = json.loads(read("data/homepage_publications.json") or "{}")
    for e in hp.get("entries", []):
        p = {
            "title": e.get("title"),
            "year": e.get("year"),
            "venue": e.get("venue"),
            "url": e.get("url"),
            "externalIds": {},
            "paperId": None,
            "abstract": "",
        }
        add(p, [e.get("author") or ""], "homepage")
    for block in trends.get("blocks", []):
        for p in block.get("papers", []):
            add(p, [], block.get("key"))

    out = list(rows.values())
    out.sort(key=lambda r: (_paper_year(r["paper"]), r["venue_family"] == "Big4", r["paper"].get("citationCount") or 0), reverse=True)
    return out

def genai_paper_item(row, tz):
    p = row["paper"]
    title = html.escape(p.get("title") or "")
    venue = html.escape((p.get("venue") or "-")[:78])
    people = ", ".join(sorted(x for x in row.get("people", set()) if x))
    people_html = f' · 涉及：{html.escape(people)}' if people else ""
    zh = html.escape((tz.get(p.get("paperId", "")) or {}).get("zh", ""))
    zh_html = f'<span class="zh">{zh}</span>' if zh else ""
    url = html.escape(paper_url(p))
    return (
        '<li>'
        f'<span class="tag">{html.escape(row["venue_family"])}</span> '
        f'<span class="tag preprint">{html.escape(row["method"])}</span> '
        f'<span class="yr">{p.get("year") or "?"}</span> '
        f'<a href="{url}" target="_blank">{title}</a>'
        f'{zh_html}<span class="venue">{venue}{people_html}</span>'
        '</li>'
    )

def genai_topic_html(experts, trends, tz):
    rows = collect_genai_rows(experts, trends)
    grouped = {theme["key"]: [] for theme in GENAI_THEMES}
    for row in rows:
        grouped.setdefault(row["theme"], []).append(row)
    venue_counts = Counter(row["venue_family"] for row in rows)
    method_counts = Counter(row["method"] for row in rows)
    venue_line = " · ".join(f"{html.escape(k)} {v}" for k, v in venue_counts.most_common())
    method_line = " · ".join(f"{html.escape(k)} {v}" for k, v in method_counts.most_common())

    blocks = []
    for theme in GENAI_THEMES:
        items = grouped.get(theme["key"]) or []
        paper_html = "".join(genai_paper_item(row, tz) for row in items[:6])
        if not paper_html:
            paper_html = '<p class="muted">本地库暂未命中代表论文。</p>'
        blocks.append(
            '<article class="genai-card">'
            f'<h3>{html.escape(theme["title"])}<span>{len(items)} 篇</span></h3>'
            f'<p>{html.escape(theme["summary"])}</p>'
            f'<p class="big4-hint">Big4 提示：{html.escape(theme["big4"])}</p>'
            f'<ul class="genai-list">{paper_html}</ul>'
            '</article>'
        )
    return (
        '<div class="genai-overview">'
        '<p>这个专题只收 GenAI / LLM / chatbot / AI agent 与 usable security 交叉的工作；'
        '纯模型攻击或纯 NLP 能力论文只有在涉及用户、开发者、安全决策、隐私风险或工作流时才纳入。</p>'
        f'<p class="muted">本地命中 {len(rows)} 篇 · 来源分布：{venue_line or "-"} · 方法分布：{method_line or "-"}</p>'
        '</div>'
        '<div class="genai-grid">' + "".join(blocks) + '</div>'
    )

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
    new_work_rows = collect_new_work(experts, since=2026)
    new_work_rows = merge_homepage(new_work_rows)
    new_work = new_work_html(new_work_rows, tz)
    trends = json.loads(read("data/trends.json") or "{}")
    curated_trends = json.loads(read("data/trend_summaries_zh.json") or "{}")
    trend_blocks = trends.get("blocks", [])
    sec_html = "".join(trend_block_html(b, curated_trends) for b in trend_blocks[:2])
    sec_migration_html = security_migration_html(trends)
    genai_html = genai_topic_html(experts, trends, tz)
    hci_html = "".join(trend_block_html(b, curated_trends) for b in trend_blocks[2:4])

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
.trend h3{{font-size:15px;margin:18px 0 4px;padding:4px 8px;background:var(--card);border:1px solid var(--line);border-radius:6px}}
.trend h4{{font-size:13px;margin:10px 0 4px;color:var(--acc)}}.trend ul{{margin:4px 0;padding-left:20px}}
.trend li{{font-size:13px;margin:2px 0}}.muted{{color:var(--mut);font-size:12px}}
.trend-block{{margin-bottom:28px}}.theme-list{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:9px;list-style:none;padding:0!important}}
.theme-list li{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:10px!important}}
.theme-list strong,.theme-list span{{display:block}}.theme-list span{{margin-top:3px;color:var(--mut)}}
.trend-papers{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:10px}}
.trend-paper{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:11px}}
.trend-paper a{{color:var(--fg);font-weight:600;text-decoration:none}}.trend-paper a:hover{{color:var(--acc)}}
.trend-paper p{{font-size:13px;margin:6px 0 0;color:var(--mut)}}.paper-meta{{font-size:11px;color:var(--mut);margin-bottom:3px}}
details{{margin-top:10px;border:1px solid var(--line);border-radius:7px;padding:7px 10px}}
summary{{cursor:pointer;color:var(--acc);font-size:13px}}.rest-papers a{{color:var(--fg);text-decoration:none}}
.rest-papers span{{color:var(--mut)}}.evidence p{{font-size:12px;color:var(--mut)}}
.new-work{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}}
.new-work-panel{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px}}
.new-work-panel h3{{display:flex;justify-content:space-between;gap:10px;margin:0 0 8px;font-size:14px;color:var(--acc)}}
.new-work-panel h3 span{{color:var(--mut);font-weight:400;font-size:12px}}
.topic-block{{margin-top:10px;padding-top:8px;border-top:1px solid var(--line)}}
.topic-block:first-of-type{{border-top:0;padding-top:0}}
.topic-block h4{{display:flex;justify-content:space-between;gap:10px;margin:0 0 5px;font-size:13px;color:var(--fg)}}
.topic-block h4 span{{color:var(--mut);font-weight:400;font-size:12px}}
.new-work-list{{list-style:none;margin:0;padding:0}}
.new-work-list li{{padding:7px 0;border-top:1px dashed var(--line);font-size:13px}}
.topic-block .new-work-list li:first-child{{border-top:0}}
.new-work-list a{{color:var(--fg);text-decoration:none}}.new-work-list a:hover{{color:var(--acc)}}
.migration-block{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin:12px 0 18px}}
.migration-block h3{{margin:0 0 6px;font-size:15px;color:var(--acc)}}
.migration-section{{margin-top:14px}}.migration-section h4{{margin:0 0 7px;font-size:13px;color:var(--fg)}}
.migration-cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(310px,1fr));gap:10px;margin-top:10px}}
.migration-card{{border:1px solid var(--line);border-radius:8px;padding:10px;background:var(--bg)}}
.migration-card.readable p{{margin:7px 0 0;font-size:12.5px}}.judgment{{color:var(--fg)}}.evidence-line{{color:var(--mut)}}
.badge-note{{color:var(--mut);border-top:1px dashed var(--line);padding-top:7px}}
.migration-badge{{white-space:nowrap;font-size:11px;border-radius:999px;padding:2px 7px;background:#e7f5ed;color:#137333}}
.boxed{{border:1px dashed var(--line);border-radius:8px;padding:10px;background:var(--bg)}}
.migration-card-head{{display:flex;justify-content:space-between;gap:10px;align-items:flex-start}}
.migration-card-head strong{{font-size:13px;line-height:1.3}}.signal{{white-space:nowrap;font-size:11px;border-radius:999px;padding:2px 7px;background:#e7f5ed;color:#137333}}
.signal.medium{{background:#fff4df;color:#9a5b00}}@media(prefers-color-scheme:dark){{.signal{{background:#193a25;color:#8fe0a5}}.signal.medium{{background:#3d2d12;color:#f1c27d}}}}
.migration-flow{{display:grid;grid-template-columns:1fr 24px 1fr;align-items:center;gap:6px;margin:9px 0;color:var(--mut);font-size:12px}}
.migration-flow span:not(.arrow){{border:1px solid var(--line);border-radius:6px;padding:5px 7px;background:var(--card)}}
.migration-flow b{{display:block;color:var(--fg);font-size:15px}}.arrow{{text-align:center;color:var(--acc);font-weight:700}}
.bar-rows{{display:grid;gap:5px}}.bar-rows label{{display:block;color:var(--mut);font-size:11px;margin-bottom:2px}}
.bar-rows p{{display:flex;align-items:end;gap:4px;margin:0;height:45px}}
.mini-bar{{display:inline-flex;flex-direction:column;align-items:center;justify-content:flex-end;width:18px;height:43px}}
.mini-bar i{{display:block;width:10px;background:var(--acc);border-radius:3px 3px 1px 1px;opacity:.75}}
.mini-bar em{{font-style:normal;color:var(--mut);font-size:10px;line-height:1.1;margin-top:2px}}
.migration-watch ul{{list-style:none;margin:8px 0 0;padding:0;display:grid;gap:7px}}
.migration-watch li{{position:relative;border:1px solid var(--line);border-radius:7px;padding:7px 44px 7px 8px;overflow:hidden;background:var(--bg)}}
.migration-watch li b{{position:absolute;left:0;bottom:0;height:3px;background:var(--acc);opacity:.55}}.migration-watch li i{{position:absolute;right:8px;top:8px;font-style:normal;color:var(--mut);font-size:12px}}
.migration-watch li span{{position:relative;display:block}}.migration-watch li em{{display:block;font-style:normal;color:var(--mut);font-size:11px}}
.genai-overview{{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px;margin-bottom:12px}}
.genai-overview p{{margin:0 0 6px}}.genai-overview p:last-child{{margin-bottom:0}}
.genai-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}}
.genai-card{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px}}
.genai-card h3{{display:flex;justify-content:space-between;gap:10px;margin:0 0 7px;font-size:14px;color:var(--acc)}}
.genai-card h3 span{{font-size:12px;color:var(--mut);font-weight:400;white-space:nowrap}}
.genai-card p{{font-size:13px;margin:6px 0;color:var(--mut)}}.big4-hint{{border-left:3px solid var(--acc);padding-left:8px;color:var(--fg)!important}}
.genai-list{{list-style:none;margin:8px 0 0;padding:0}}.genai-list li{{padding:7px 0;border-top:1px dashed var(--line);font-size:13px}}
.genai-list a{{color:var(--fg);text-decoration:none}}.genai-list a:hover{{color:var(--acc)}}
</style></head><body>
<header><h1>Usable Security / HCI 论文追踪看板</h1>
<div class="sub">大牛库 {len(experts)} 人 · 领域内论文 {total_infield} 篇 · 数据更新 {gen}</div></header>
<nav><a href="#experts">大牛库</a><a href="#new">2026 新工作</a><a href="#sec">安全趋势</a><a href="#genai">GenAI 专题</a><a href="#hci">HCI 趋势</a></nav>
<main>
<section id="experts"><h2>大牛库 · 各学者最近论文</h2>
<div class="grid">{cards}</div></section>
<section id="new"><h2>大牛库 · 2026 年以来新工作</h2>
<div class="new-work">{new_work}</div></section>
<section id="sec" class="trend"><h2>安全领域 · 新趋势</h2>{sec_migration_html}{sec_html}</section>
<section id="genai"><h2>GenAI / LLM / Chatbot × Usable Security 专题</h2>{genai_html}</section>
<section id="hci" class="trend"><h2>HCI 领域 · 隐私安全新趋势</h2>{hci_html}</section>
</main></body></html>"""
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(doc)
    print(f"看板已生成 index.html（{len(experts)} 位大牛，{total_infield} 篇领域内论文）")

if __name__ == "__main__":
    main()
