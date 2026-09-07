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
        '安全四大用户研究子集里的时间顺序。源领域仍用 first-hot；安全四大目标端使用 interview/survey/questionnaire/usable/user study/human-centered 宽检索，'
        '再要求摘要同时出现人本范围与用户研究方法证据，且只要求从 0 到 ≥1 篇。'
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

def merge_seed_experts(experts):
    """Keep tracked authors visible before their Semantic Scholar profiles are resolved."""
    seeds = json.loads(read("people/experts.json") or "{}").get("experts", [])
    by_name = {e.get("name"): e for e in experts}
    for seed in seeds:
        name = seed.get("name")
        if not name:
            continue
        if name not in by_name:
            row = {
                "name": name,
                "affiliation": seed.get("affiliation"),
                "paper_count": 0,
                "in_field_count": 0,
                "recent_count": 0,
                "papers": [],
            }
            experts.append(row)
            by_name[name] = row
        by_name[name]["known_for"] = seed.get("known_for")
        by_name[name]["tracking_role"] = seed.get("tracking_role") or []
        by_name[name]["profile_pending"] = not bool(seed.get("ss_author_ids"))
    return experts


def official_usable_html(data):
    availability = data.get("availability") or {}
    availability_html = "".join(
        f"<li><strong>{html.escape(venue)}</strong><span>{html.escape(status)}</span></li>"
        for venue, status in availability.items()
    )
    grouped = {}
    for paper in data.get("papers", []):
        grouped.setdefault((paper.get("venue"), paper.get("cycle")), []).append(paper)
    sections = []
    for (venue, cycle), papers in grouped.items():
        cards = []
        for p in papers:
            first = p.get("first_author") or "待核验"
            corresponding = "、".join(p.get("corresponding_authors") or []) or "官方未标注"
            advice = '<span class="topic-chip">与建议/学习直接相关</span>' if p.get("advice_learning_relevant") else ""
            cards.append(
                '<article class="official-paper">'
                f'<div class="paper-meta">{html.escape(venue or "")} · {html.escape(cycle or "")} · '
                f'{html.escape(p.get("status") or "")}</div>'
                f'<h4><a href="{html.escape(p.get("url") or p.get("source_url") or "#")}" target="_blank">'
                f'{html.escape(p.get("title") or "")}</a></h4>'
                f'<p>{html.escape(p.get("summary_zh") or "")}</p>'
                f'<div class="author-line">一作：{html.escape(first)} · 通讯作者：{html.escape(corresponding)}</div>'
                f'<div class="method-line">{html.escape(p.get("method") or "")} {advice}</div>'
                '</article>'
            )
        sections.append(
            f'<section class="official-group"><h3>{html.escape(venue or "")} · {html.escape(cycle or "")}'
            f'<span>{len(papers)} 篇</span></h3><div class="official-grid">{"".join(cards)}</div></section>'
        )
    return (
        '<div class="coverage-note"><strong>公开状态与覆盖边界</strong>'
        f'<ul>{availability_html}</ul></div>{"".join(sections)}'
    )


def advice_learning_html(data):
    grouped = {}
    for paper in data.get("papers", []):
        grouped.setdefault((paper.get("year"), paper.get("tier")), []).append(paper)
    tier_labels = {
        "core_big4": "安全四大 · 核心证据",
        "core_soups": "SOUPS · 核心证据",
        "adjacent_hci": "HCI · 相邻证据",
    }
    sections = []
    for (year, tier), papers in sorted(grouped.items(), key=lambda x: (-int(x[0][0]), x[0][1])):
        rows = []
        for p in papers:
            rows.append(
                '<article class="advice-paper">'
                f'<div class="paper-meta">{year} · {html.escape(p.get("venue") or "")} · '
                f'{html.escape(p.get("method") or "")}</div>'
                f'<h4><a href="{html.escape(p.get("url") or "#")}" target="_blank">'
                f'{html.escape(p.get("title") or "")}</a></h4>'
                f'<span class="topic-chip">{html.escape(p.get("topic") or "")}</span>'
                f'<p>{html.escape(p.get("summary_zh") or "")}</p>'
                '</article>'
            )
        sections.append(
            f'<section class="advice-group"><h3>{year} · {tier_labels.get(tier, tier)}'
            f'<span>{len(papers)} 篇</span></h3><div class="advice-grid">{"".join(rows)}</div></section>'
        )
    return (
        '<div class="coverage-note"><strong>专题口径</strong><p>'
        '核心范围为 2025–2026 SOUPS 与安全四大中直接研究终端用户安全建议、知识获得、'
        '安全意识、教育干预或警告理解的论文；相邻 HCI 证据单独显示，不与核心会议混算。'
        f'</p></div>{"".join(sections)}'
    )


def normalize_paper_title(title):
    return re.sub(r"\W+", "", (title or "").lower())


def collect_automatic_experiment_candidates(raw_data, curated_data):
    curated_titles = {
        normalize_paper_title(p.get("title"))
        for p in curated_data.get("papers", [])
    }
    seen = set()
    candidates = []
    for venue, venue_data in (raw_data.get("venues") or {}).items():
        for paper in venue_data.get("user_experiment_candidates") or []:
            key = normalize_paper_title(paper.get("title"))
            if not key or key in curated_titles or key in seen:
                continue
            seen.add(key)
            text = f"{paper.get('title') or ''} {paper.get('abstract') or ''}".lower()
            design = next((x for x in (
                "between-subjects", "within-subjects", "field experiment",
                "online experiment", "controlled experiment", "experiment",
            ) if x in text), "experiment")
            human = next((x for x in (
                "human participants", "participants", "user study", "end users", "users",
            ) if x in text), "human-study evidence")
            outcome = next((x for x in (
                "click-through", "click", "decision", "performance", "trust",
                "usability", "knowledge", "awareness",
            ) if x in text), "user-facing outcome")
            candidates.append({
                **paper,
                "venue": venue,
                "matched_evidence": [design, human, outcome],
            })
    return candidates


def user_experiments_html(data, automatic_candidates=None):
    strength_labels = {
        "strong_experiment": "强实验",
        "controlled_comparison": "受控比较",
        "exploratory_comparison": "探索性比较",
    }
    tier_labels = {
        "core_big4": "安全四大主会",
        "soups_showcase": "SOUPS Published Work",
        "adjacent_workshop": "相邻可用安全 Workshop",
        "adjacent_hci": "相邻 HCI",
    }
    grouped = {}
    for paper in data.get("papers", []):
        grouped.setdefault((paper.get("year"), paper.get("tier")), []).append(paper)
    for paper in automatic_candidates or []:
        details = paper.get("experiment_details") or {}
        design = details.get("design") or "摘要未说明"
        strength = (
            "strong_experiment"
            if any(term in design for term in ("现场实验", "组间实验", "组内实验", "行为实验", "欺骗性在线实验", "受控实验"))
            else "controlled_comparison"
        )
        grouped.setdefault((2026, "core_big4"), []).append({
            "year": 2026,
            "venue": paper.get("venue"),
            "tier": "core_big4",
            "cycle": paper.get("cycle"),
            "title": paper.get("title"),
            "topic": details.get("topic") or "用户实验",
            "strength": strength,
            "design": design,
            "sample": details.get("sample") or "摘要未说明",
            "intervention": details.get("intervention") or "摘要未说明",
            "comparison": details.get("comparison") or "摘要未说明",
            "outcomes": details.get("outcomes") or "摘要未说明",
            "takeaway_zh": details.get("result") or "摘要未说明",
            "url": paper.get("paper_url"),
        })
    sections = []
    tier_order = {"core_big4": 0, "soups_showcase": 1, "adjacent_workshop": 2, "adjacent_hci": 3}
    for (year, tier), papers in sorted(
        grouped.items(), key=lambda x: (-int(x[0][0]), tier_order.get(x[0][1], 9))
    ):
        cards = []
        for p in papers:
            strength = strength_labels.get(p.get("strength"), p.get("strength") or "")
            cycle = f' · {html.escape(p.get("cycle"))}' if p.get("cycle") else ""
            cards.append(
                '<article class="experiment-paper">'
                f'<div class="paper-meta">{year} · {html.escape(p.get("venue") or "")}{cycle}</div>'
                f'<h4><a href="{html.escape(p.get("url") or p.get("source_url") or "#")}" target="_blank">'
                f'{html.escape(p.get("title") or "")}</a></h4>'
                f'<div><span class="experiment-badge {html.escape(p.get("strength") or "")}">'
                f'{html.escape(strength)}</span><span class="topic-chip">{html.escape(p.get("topic") or "")}</span></div>'
                f'<p><strong>设计：</strong>{html.escape(p.get("design") or "")} · '
                f'{html.escape(p.get("sample") or "")}</p>'
                f'<p><strong>操纵：</strong>{html.escape(p.get("intervention") or "")}</p>'
                f'<p><strong>比较：</strong>{html.escape(p.get("comparison") or "")}</p>'
                f'<p><strong>结果指标：</strong>{html.escape(p.get("outcomes") or "")}</p>'
                f'<p class="experiment-takeaway">{html.escape(p.get("takeaway_zh") or "")}</p>'
                '</article>'
            )
        sections.append(
            f'<section class="experiment-group"><h3>{year} · {tier_labels.get(tier, tier)}'
            f'<span>{len(papers)} 篇</span></h3><div class="experiment-grid">{"".join(cards)}</div></section>'
        )
    return (
        '<div class="coverage-note"><strong>纳入口径</strong><p>'
        '必须同时存在用户侧操纵或干预、比较条件、真实参与者，以及安全行为、判断、知识、'
        '信任、理解或可用性结果。强实验、受控比较和探索性比较分开标注，避免把任务访谈误当作 A/B 因果证据。'
        '当前结果结合人工核验与官方 abstract 的结构化抽取，不等同于系统综述或完整论文数据库。'
        f'</p></div>{"".join(sections)}'
    )


BIG4_VENUE_TERMS = (
    "ieee symposium on security and privacy",
    "ieee s&p",
    "usenix security",
    "computer and communications security",
    "acm ccs",
    "network and distributed system security",
    "ndss",
)

OTHER_SECURITY_VENUE_TERMS = (
    "symposium on usable privacy and security",
    "usable privacy and security",
    "soups",
    "privacy enhancing technologies",
    "popets",
    "pets",
    "usec",
    "usable security and privacy",
)


def is_allowed_hci_venue(venue):
    """Only the HCI sources explicitly selected for this dashboard."""
    v = (venue or "").strip().lower()
    if not v:
        return False
    # IJHCI / International Journal of Human-Computer Interaction is excluded.
    if "human-computer interaction" in v and "human-computer studies" not in v:
        return False
    return any(term in v for term in (
        "international conference on human factors in computing systems",
        "chi conference on human factors",
        "acm chi",
        "computer supported cooperative work",
        "computer-supported cooperative work",
        "cscw",
        "proc. acm hum. comput. interact",
        "proceedings of the acm on human-computer interaction",
        "acm transactions on computer-human interaction",
        "acm trans. comput. hum. interact",
        "tochi",
        "ubiquitous computing",
        "ubicomp",
        "interactive mobile wearable and ubiquitous technologies",
        "imwut",
        "international journal of human-computer studies",
        "ijhcs",
    ))


def usable_source_family(venue):
    v = (venue or "").lower()
    if any(term in v for term in BIG4_VENUE_TERMS):
        return "big4"
    if any(term in v for term in OTHER_SECURITY_VENUE_TERMS):
        return "other_security"
    if is_allowed_hci_venue(venue):
        return "hci"
    return None


USABLE_SECURITY_SCOPE_TERMS = (
    "security", "privacy", "scam", "scams", "fraud", "phishing", "warning",
    "authentication", "password", "abuse", "harassment", "cybercrime", "safety",
)

USABLE_HUMAN_EVIDENCE_TERMS = (
    "participants", "interview", "survey", "questionnaire", "focus group",
    "user study", "human-centered", "human centred", "thematic analysis",
    "qualitative analysis", "mixed-method", "mixed method", "field study",
    "reddit posts", "social media posts", "user perceptions", "user behavior",
    "user behaviour", "people often", "community-centered", "community centred",
)

ADVICE_LEARNING_RECALL_TERMS = (
    "security advice", "privacy advice", "seek advice", "seeking advice", "obtain advice",
    "advice on", "informational support", "emotional support", "reassurance", "coping",
    "help-seeking", "knowledge-sharing", "knowledge sharing", "awareness", "literacy",
    "security education", "privacy education", "security learning", "warning", "warnings",
)

USER_EXPERIMENT_RECALL_TERMS = (
    "between-subjects", "within-subjects", "field experiment", "online experiment",
    "controlled experiment", "randomized", "randomised", "a/b test", "ab test",
)


def rule_based_usable_tags(paper):
    """Classify candidate papers from content; venue/author only defines the pool."""
    text = " ".join(str(paper.get(k) or "") for k in (
        "title", "abstract", "topic", "summary_zh", "takeaway_zh", "method",
    )).lower()
    if not any(term in text for term in USABLE_SECURITY_SCOPE_TERMS):
        return set()
    has_human_evidence = any(term in text for term in USABLE_HUMAN_EVIDENCE_TERMS)
    title = (paper.get("title") or "").lower()
    # Some newly indexed journal records have no abstract. In that narrow case,
    # let an explicit usable/usability title signal stand in for missing method
    # metadata; generic privacy/security titles still require human evidence.
    explicit_usable_title = not paper.get("abstract") and any(
        term in title for term in (
            "usable", "usability", "awareness", "training", "attitudes",
            "strategies", "attempts to protect", "user-centred", "user-centered",
        )
    )
    if not has_human_evidence and not explicit_usable_title:
        return set()
    tags = {"Usable Security"}
    if any(term in text for term in ADVICE_LEARNING_RECALL_TERMS):
        tags.add("安全建议与学习")
    if any(term in text for term in USER_EXPERIMENT_RECALL_TERMS):
        tags.add("用户实验")
    return tags


def collect_rule_based_usable_rows(experts, trends):
    """Build a complete expert+venue candidate pool, then classify by abstract evidence."""
    rows = {}

    def add(paper, source):
        if (paper.get("year") or 0) not in {2025, 2026}:
            return
        if not usable_source_family(paper.get("venue")):
            return
        key = _norm_title(paper.get("title"))
        if not key:
            return
        tags = rule_based_usable_tags(paper)
        if not tags:
            return
        row = rows.setdefault(key, {"paper": paper, "tags": set(), "sources": set()})
        row["tags"].update(tags)
        row["sources"].add(source)
        if len(paper.get("abstract") or "") > len(row["paper"].get("abstract") or ""):
            row["paper"] = paper

    for expert in experts:
        for paper in expert.get("papers", []):
            add(paper, "expert")
    for block in trends.get("blocks", []):
        for paper in block.get("papers", []):
            add(paper, block.get("key") or "trend")
    # The trend blocks only retain citation-velocity Top 15 papers. Keep the
    # complete recent HCI privacy/security slice available for paper-level
    # usable-security recall instead of silently dropping lower-cited work.
    for paper in trends.get("recent_hci_privacy_security", []):
        add(paper, "hci_recent")
    return list(rows.values())


def paper_default_topic_tags(paper, forced=None):
    tags = set(forced or [])
    text = " ".join(str(paper.get(k) or "") for k in (
        "title", "topic", "summary_zh", "abstract", "method",
        "design", "intervention", "comparison", "outcomes", "takeaway_zh",
    )).lower()
    if any(term in text for term in GENAI_AI_TERMS + ["xai", "explainable ai"]):
        tags.add("GenAI")
    if any(term in text for term in (
        "security advice", "privacy advice", "advice", "warning", "warnings",
        "awareness", "literacy", "learning", "education", "training",
        "安全建议", "知识", "学习", "警告", "意识", "教育",
    )):
        tags.add("安全建议与学习")
    return tags


def collect_usable_hub_papers(official, advice, experiments, automatic, genai_rows, rule_based_rows=None):
    """Merge the curated usable-security datasets without altering their source files."""
    rows = {}
    summary_data = json.loads(read("data/paper_summaries_zh.json") or "{}")
    summary_by_title = {
        _norm_title(entry.get("title")): entry
        for entry in summary_data.get("papers", [])
        if _norm_title(entry.get("title"))
    }

    def add(paper, forced_tags=None):
        title = paper.get("title") or ""
        key = _norm_title(title)
        family = usable_source_family(paper.get("venue"))
        if not key or not family:
            return
        tags = paper_default_topic_tags(paper, {"Usable Security", *(forced_tags or [])})
        themes = usable_theme_labels(paper, tags)
        supplemental_summary = summary_by_title.get(key) or {}
        row = rows.setdefault(key, {
            "id": key,
            "title": title,
            "year": paper.get("year") or 0,
            "venue": paper.get("venue") or "",
            "url": paper.get("url") or paper.get("source_url") or "#",
            "topic": paper.get("topic") or "",
            "summary": paper.get("summary_zh") or paper.get("takeaway_zh") or supplemental_summary.get("summary_zh") or "",
            "summary_source_url": supplemental_summary.get("abstract_source_url") or "",
            "summary_verified_at": supplemental_summary.get("verified_at") or "",
            "abstract": paper.get("abstract") or "",
            "method": paper.get("method") or paper.get("design") or "",
            "source_family": family,
            "tags": set(),
            "themes": set(),
        })
        row["tags"].update(tags)
        row["themes"].update(themes)
        if (paper.get("year") or 0) > row["year"]:
            row["year"] = paper.get("year") or 0
        for field, candidates in (
            ("url", [paper.get("url"), paper.get("source_url")]),
            ("topic", [paper.get("topic")]),
            ("summary", [paper.get("summary_zh"), paper.get("takeaway_zh")]),
            ("method", [paper.get("method"), paper.get("design")]),
            ("abstract", [paper.get("abstract")]),
        ):
            if not row.get(field):
                row[field] = next((value for value in candidates if value), row.get(field) or "")
        if not row.get("summary") and supplemental_summary.get("summary_zh"):
            row["summary"] = supplemental_summary["summary_zh"]
        if not row.get("summary_source_url") and supplemental_summary.get("abstract_source_url"):
            row["summary_source_url"] = supplemental_summary["abstract_source_url"]
            row["summary_verified_at"] = supplemental_summary.get("verified_at") or ""

    for paper in official.get("papers", []):
        tags = {"安全建议与学习"} if paper.get("advice_learning_relevant") else set()
        add(paper, tags)
    for paper in advice.get("papers", []):
        add(paper, {"安全建议与学习"})
    for paper in experiments.get("papers", []):
        add(paper, {"用户实验"})
    for paper in automatic or []:
        details = paper.get("experiment_details") or {}
        add({
            **paper,
            "url": paper.get("paper_url"),
            "topic": details.get("topic"),
            "method": details.get("design"),
            "summary_zh": details.get("result"),
        }, {"用户实验"})
    for row in genai_rows:
        paper = row.get("paper") or {}
        if (paper.get("year") or 0) >= 2025:
            add(paper, {"GenAI"})
    for row in rule_based_rows or []:
        add(row.get("paper") or {}, row.get("tags") or set())

    result = list(rows.values())
    for row in result:
        if not row.get("summary") and row.get("abstract"):
            sentences = re.split(r"(?<=[.!?])\s+", row["abstract"].strip())
            row["summary"] = " ".join(sentence for sentence in sentences[:3] if sentence).strip()
        if len(row["themes"]) > 1:
            row["themes"].discard("其他新方向")
    result.sort(key=lambda row: (row["year"], row["title"]), reverse=True)
    return result


def tag_attr(tags):
    return html.escape(json.dumps(sorted(tags), ensure_ascii=False), quote=True)


def compact_venue(venue):
    v = (venue or "").lower()
    labels = (
        (("computer and communications security", "acm ccs"), "ACM CCS"),
        (("ieee symposium on security and privacy", "ieee s&p"), "IEEE S&P"),
        (("usenix security",), "USENIX Security"),
        (("network and distributed system security", "ndss"), "NDSS"),
        (("symposium on usable privacy and security", "soups"), "SOUPS"),
        (("proceedings on privacy enhancing technologies", "privacy enhancing technologies", "popets", "pets"), "PoPETS/PETS"),
        (("international conference on human factors in computing systems", "acm chi", "chi conference"), "CHI"),
        (("computer supported cooperative work", "computer-supported cooperative work", "cscw"), "CSCW"),
    )
    for terms, label in labels:
        if any(term in v for term in terms):
            return label
    return venue or "来源待核验"


def usable_paper_card(row):
    visible_tags = set(row["themes"])
    if "用户实验" in row["tags"]:
        visible_tags.add("用户实验")
    tags = "".join(f'<span class="topic-chip">{html.escape(tag)}</span>' for tag in sorted(visible_tags))
    summary = f'<p>{html.escape(row["summary"])}</p>' if row.get("summary") else ""
    summary_source = ""
    if row.get("summary_source_url"):
        verified = f' · 核验 {html.escape(row.get("summary_verified_at") or "")}' if row.get("summary_verified_at") else ""
        summary_source = (
            f'<div class="summary-source"><a href="{html.escape(row["summary_source_url"])}" '
            f'target="_blank">简介依据</a>{verified}</div>'
        )
    method = f'<div class="method-line">{html.escape(row["method"])}</div>' if row.get("method") else ""
    default_tags = set(row["tags"]) | set(row["themes"])
    publication_source = f'{row["year"] or "?"} · {compact_venue(row.get("venue") or "")}'
    return (
        f'<article class="usable-paper paper-entry" data-paper-id="{html.escape(row["id"])}" '
        f'data-publication-source="{html.escape(publication_source, quote=True)}" '
        f'data-default-tags="{tag_attr(default_tags)}">'
        f'<div class="paper-meta">{row["year"] or "?"} · {html.escape(row["venue"])}</div>'
        f'<h4><a href="{html.escape(row["url"])}" target="_blank">{html.escape(row["title"])}</a></h4>'
        f'<div class="default-topic-tags">{tags}</div>{method}{summary}{summary_source}</article>'
    )


def usable_security_hub_html(rows):
    sources = [
        ("big4", "安全四大", "IEEE S&P、USENIX Security、ACM CCS、NDSS"),
        ("other_security", "其他安全会议", "SOUPS、PETS/PoPETS、USEC 等"),
        ("hci", "HCI 来源", "CHI、CSCW、TOCHI、UbiComp/IMWUT、IJHCS；不含 IJHCI"),
    ]
    themes = [label for label, _ in EXPERT_THEME_RULES] + ["其他新方向"]
    source_sections = []
    for source_key, source_label, source_note in sources:
        source_rows = [row for row in rows if row["source_family"] == source_key]
        theme_sections = []
        for theme_label in themes:
            items = [row for row in source_rows if theme_label in row["themes"]]
            if not items:
                continue
            theme_sections.append(
                f'<section class="usable-theme"><h4>{html.escape(theme_label)}'
                f'<span>{len(items)} 篇</span></h4><div class="usable-grid">'
                f'{"".join(usable_paper_card(row) for row in items)}</div></section>'
            )
        source_sections.append(
            f'<section class="usable-source"><h3>{html.escape(source_label)}'
            f'<span>{len(source_rows)} 篇去重论文</span></h3>'
            f'<p class="source-note">{html.escape(source_note)}</p>{"".join(theme_sections)}</section>'
        )
    return (
        '<div class="coverage-note"><strong>阅读顺序：先看来源，再看主题</strong><p>'
        '主题分类复用网络安全专题的口径；同一论文可以同时进入多个研究主题。'
        '“用户实验”等方法标签继续显示，但不作为互斥主题。</p></div>' + "".join(source_sections)
    )


EXPERT_THEME_RULES = [
    ("GenAI / LLM 与人机协作", ("llm", "large language", "generative ai", "chatbot", "agent", "deepfake", "xai", "artificial intelligence")),
    ("安全建议、警告与知识学习", ("advice", "warning", "awareness", "literacy", "learning", "training", "education", "rationale")),
    ("诈骗、钓鱼与在线伤害", ("phishing", "scam", "fraud", "abuse", "harassment", "harm", "deception")),
    ("隐私、同意与数据控制", ("privacy", "consent", "disclosure", "tracking", "data control", "anonym")),
    ("认证、账户与访问控制", ("authentication", "password", "passkey", "account", "permission", "access control", "mfa")),
    ("开发者、组织与安全工作流", ("developer", "organization", "workplace", "workflow", "security operations", "security operations center", "security operations centre", "vulnerability")),
    ("可访问性与包容性安全", ("accessible", "accessibility", "deaf", "blind", "disability", "older adult", "inclusive")),
]


def usable_theme_labels(paper, existing_tags=None):
    text = " ".join(str(paper.get(k) or "") for k in (
        "title", "topic", "summary_zh", "abstract", "method",
        "design", "intervention", "comparison", "outcomes", "takeaway_zh",
    )).lower()
    labels = {
        label for label, keywords in EXPERT_THEME_RULES
        if any(keyword in text for keyword in keywords)
    }
    existing_tags = set(existing_tags or [])
    if "GenAI" in existing_tags:
        labels.add("GenAI / LLM 与人机协作")
    if "安全建议与学习" in existing_tags:
        labels.add("安全建议、警告与知识学习")
    return labels or {"其他新方向"}


def expert_topic_labels(title):
    text = (title or "").lower()
    labels = [label for label, keywords in EXPERT_THEME_RULES if any(keyword in text for keyword in keywords)]
    return labels or ["其他新方向"]


def collect_expert_theme_rows(experts, area):
    rows = {}
    for expert in experts:
        for paper in expert.get("papers", []):
            if paper.get("year") not in {2025, 2026}:
                continue
            venue = paper.get("venue") or ""
            if area == "hci":
                if not is_allowed_hci_venue(venue):
                    continue
            elif usable_source_family(venue) == "hci":
                continue
            elif not (
                paper.get("focus_area") == "security"
                or paper.get("category") == "security"
                or usable_source_family(venue) in {"big4", "other_security"}
            ):
                continue
            key = _norm_title(paper.get("title"))
            if not key:
                continue
            row = rows.setdefault(key, {
                "paper": paper,
                "people": set(),
                "themes": set(expert_topic_labels(paper.get("title"))),
            })
            row["people"].add(expert.get("name") or "")
    return list(rows.values())


def expert_themes_html(experts, area, tz):
    rows = collect_expert_theme_rows(experts, area)
    grouped = {}
    for row in rows:
        for theme in row["themes"]:
            grouped.setdefault(theme, []).append(row)
    blocks = []
    for theme, items in sorted(grouped.items(), key=lambda pair: (-len(pair[1]), pair[0])):
        year_counts = Counter((row["paper"].get("year") or 0) for row in items)
        paper_items = []
        for row in sorted(items, key=lambda item: (item["paper"].get("year") or 0, item["paper"].get("title") or ""), reverse=True)[:8]:
            paper = row["paper"]
            zh = html.escape((tz.get(paper.get("paperId", "")) or {}).get("zh", ""))
            zh_html = f'<span class="zh">{zh}</span>' if zh else ""
            default_tags = {"大牛 2025–2026"}
            default_tags.update(paper_default_topic_tags(paper))
            paper_items.append(
                f'<li class="paper-entry" data-default-tags="{tag_attr(default_tags)}">'
                f'<span class="yr">{paper.get("year") or "?"}</span> '
                f'<a href="{html.escape(paper_url(paper))}" target="_blank">{html.escape(paper.get("title") or "")}</a>'
                f'{zh_html}<span class="venue">{html.escape(paper.get("venue") or "")} · '
                f'{html.escape("、".join(sorted(x for x in row["people"] if x)))}</span></li>'
            )
        blocks.append(
            '<article class="expert-theme-card">'
            f'<h4>{html.escape(theme)}<span>{len(items)} 篇</span></h4>'
            f'<p class="year-split">2025：{year_counts.get(2025, 0)} 篇 · 2026：{year_counts.get(2026, 0)} 篇</p>'
            f'<ul class="expert-theme-list">{"".join(paper_items)}</ul></article>'
        )
    scope = (
        "安全会议与安全领域论文"
        if area == "security"
        else "CHI、CSCW、TOCHI、UbiComp/IMWUT、IJHCS（不含 IJHCI）"
    )
    return (
        f'<div class="coverage-note"><strong>大牛库 2025–2026 主题切片</strong>'
        f'<p>按论文题名做多标签主题聚合；范围为{scope}。这是导航性归类，不替代摘要级人工综述。</p></div>'
        f'<div class="expert-theme-grid">{"".join(blocks)}</div>'
    )


def tag_interaction_assets(seed):
    seed_json = json.dumps(seed or {}, ensure_ascii=False).replace("</", "<\\/")
    return """
<style>
.workspace-intro{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:22px}
.workspace-intro a{display:block;background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px;color:var(--fg);text-decoration:none}
.workspace-intro b,.workspace-intro span{display:block}.workspace-intro span{color:var(--mut);font-size:12px;margin-top:3px}
.usable-source{border-top:2px solid var(--line);padding-top:12px}.usable-source>h3,.usable-theme>h4,.expert-theme-card h4{display:flex;justify-content:space-between;gap:10px}
.usable-source>h3 span,.usable-theme>h4 span,.expert-theme-card h4 span{color:var(--mut);font-size:12px;font-weight:400}
.source-note,.year-split{color:var(--mut);font-size:12px}.usable-theme{margin:14px 0 24px}.usable-theme>h4{font-size:14px;color:var(--acc)}
.usable-grid,.expert-theme-grid,.ongoing-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:12px}
.usable-paper,.expert-theme-card,.ongoing-paper{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px}
.usable-paper h4,.ongoing-paper h4{margin:4px 0 7px;font-size:14px}.usable-paper h4 a,.ongoing-paper a{color:var(--fg);text-decoration:none}
.usable-paper p{font-size:12.5px;color:var(--mut)}.default-topic-tags{display:flex;gap:5px;flex-wrap:wrap;margin:5px 0}
.summary-source{font-size:11px;color:var(--mut);margin-top:6px}.summary-source a{color:var(--acc);text-decoration:none}
.publication-source{font-size:10px;font-weight:600;color:var(--acc);margin-left:7px;vertical-align:super;white-space:nowrap}
.expert-theme-card h4{font-size:14px;margin:0}.expert-theme-list{list-style:none;margin:8px 0 0;padding:0}
.expert-theme-list li{padding:7px 0;border-top:1px dashed var(--line);font-size:13px}.expert-theme-list a{color:var(--fg);text-decoration:none}
.tag-toolbar{position:sticky;top:42px;z-index:4;background:var(--card);border:1px solid var(--line);border-radius:9px;padding:9px;margin:0 0 18px;display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.tag-toolbar button,.tag-add{border:1px solid var(--line);background:var(--bg);color:var(--fg);border-radius:999px;padding:3px 9px;cursor:pointer;font-size:11px}
.tag-toolbar button.active{border-color:var(--acc);color:var(--acc)}.tag-toolbar .spacer{flex:1}
.paper-tag-editor{display:flex;gap:5px;flex-wrap:wrap;align-items:center;margin-top:8px;padding-top:7px;border-top:1px dashed var(--line)}
.paper-user-tag{border:0;border-radius:999px;padding:2px 7px;font-size:11px;background:#eef2ff;color:#3849a3}
button.paper-user-tag.custom{cursor:pointer}.tag-help{font-size:11px;color:var(--mut)}
@media(max-width:760px){.workspace-intro{grid-template-columns:1fr 1fr}.tag-toolbar{top:62px}}
</style>
<script>
window.PAPER_TAG_SEED = __SEED__;
(function(){
  const storageKey = "paper-dashboard-tags-v1";
  const seed = window.PAPER_TAG_SEED || {};
  const preset = seed.preset_tags || ["安全建议与学习","GenAI","用户实验","Usable Security","重点阅读","待读"];
  let saved = {};
  try { saved = JSON.parse(localStorage.getItem(storageKey) || "{}"); } catch (_) { saved = {}; }
  const normalize = s => (s || "").toLowerCase().normalize("NFKC").replace(/[^\\p{L}\\p{N}]+/gu, "");
  const selectors = [
    ".paper-entry", "article.trend-paper", "article.official-paper", "article.advice-paper",
    "article.experiment-paper", ".new-work-list li", ".genai-list li", ".rest-papers li", "ul.papers li"
  ].join(",");
  const entries = [];
  document.querySelectorAll(selectors).forEach(node => {
    if (node.closest("#ongoing-dynamic")) return;
    const link = node.querySelector('a[target="_blank"]');
    if (!link) return;
    node.classList.add("paper-entry");
    const title = link.textContent.trim();
    const id = node.dataset.paperId || normalize(title);
    if (!id) return;
    node.dataset.paperId = id;
    let defaults = [];
    try { defaults = JSON.parse(node.dataset.defaultTags || "[]"); } catch (_) {}
    entries.push({node, link, title, id, defaults});
  });
  const defaultsById = {};
  entries.forEach(entry => {
    defaultsById[entry.id] = [...new Set([...(defaultsById[entry.id] || []), ...(entry.defaults || [])])];
  });
  const combined = entry => new Set([...(defaultsById[entry.id] || []), ...((saved[entry.id] || []))]);
  const persist = () => localStorage.setItem(storageKey, JSON.stringify(saved));
  function renderEditor(entry) {
    let box = entry.node.querySelector(":scope > .paper-tag-editor");
    if (!box) { box = document.createElement("div"); box.className = "paper-tag-editor"; entry.node.appendChild(box); }
    box.innerHTML = "";
    combined(entry).forEach(tag => {
      const custom = (saved[entry.id] || []).includes(tag);
      const chip = document.createElement("button");
      chip.type = "button"; chip.className = "paper-user-tag" + (custom ? " custom" : "");
      chip.textContent = tag + (custom ? " ×" : "");
      chip.title = custom ? "点击删除自定义标签" : "数据自带标签";
      if (custom) chip.onclick = () => {
        saved[entry.id] = (saved[entry.id] || []).filter(value => value !== tag);
        if (!saved[entry.id].length) delete saved[entry.id];
        persist(); renderAll();
      };
      box.appendChild(chip);
    });
    const add = document.createElement("button");
    add.type = "button"; add.className = "tag-add"; add.textContent = "＋标签";
    add.onclick = () => {
      const value = prompt("输入标签，例如：安全建议与学习、GenAI、重点阅读");
      const tag = (value || "").trim();
      if (!tag) return;
      saved[entry.id] = [...new Set([...(saved[entry.id] || []), tag])];
      persist(); renderAll();
    };
    box.appendChild(add);
  }
  function renderOngoing() {
    const target = document.getElementById("ongoing-dynamic");
    if (!target) return;
    const unique = new Map();
    entries.forEach(entry => {
      if (combined(entry).has("安全建议与学习") && !unique.has(entry.id)) unique.set(entry.id, entry);
    });
    target.innerHTML = "";
    [...unique.values()].forEach(entry => {
      const card = document.createElement("article"); card.className = "ongoing-paper";
      const h = document.createElement("h4"); const a = document.createElement("a");
      a.href = entry.link.href; a.target = "_blank"; a.textContent = entry.title; h.appendChild(a); card.appendChild(h);
      const source = entry.node.dataset.publicationSource ||
        (entry.node.querySelector(".paper-meta")?.textContent || entry.node.querySelector(".venue")?.textContent || "").trim();
      if (source) { const sup=document.createElement("sup"); sup.className="publication-source"; sup.textContent=source; h.appendChild(sup); }
      const tags = document.createElement("div"); tags.className = "default-topic-tags";
      combined(entry).forEach(tag => { const s=document.createElement("span"); s.className="topic-chip"; s.textContent=tag; tags.appendChild(s); });
      card.appendChild(tags); target.appendChild(card);
    });
  }
  let activeTag = "";
  function applyFilter() {
    entries.forEach(entry => { entry.node.hidden = !!activeTag && !combined(entry).has(activeTag); });
  }
  function renderToolbar() {
    const bar = document.getElementById("tag-toolbar"); if (!bar) return;
    const allTags = new Set(preset); entries.forEach(entry => combined(entry).forEach(tag => allTags.add(tag)));
    bar.innerHTML = '<span class="tag-help">标签筛选</span>';
    ["", ...allTags].forEach(tag => {
      const b=document.createElement("button"); b.type="button"; b.textContent=tag || "全部";
      b.className=(activeTag===tag ? "active" : ""); b.onclick=()=>{activeTag=tag; renderToolbar(); applyFilter();}; bar.appendChild(b);
    });
    const spacer=document.createElement("span"); spacer.className="spacer"; bar.appendChild(spacer);
    const exp=document.createElement("button"); exp.type="button"; exp.textContent="导出标签";
    exp.onclick=()=>{const blob=new Blob([JSON.stringify(saved,null,2)],{type:"application/json"});const a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download="paper-tags.json";a.click();URL.revokeObjectURL(a.href);};bar.appendChild(exp);
    const imp=document.createElement("button"); imp.type="button"; imp.textContent="导入标签";
    imp.onclick=()=>document.getElementById("tag-import").click();bar.appendChild(imp);
  }
  function renderAll(){ entries.forEach(renderEditor); renderToolbar(); renderOngoing(); applyFilter(); }
  const input=document.getElementById("tag-import");
  if(input) input.onchange=async()=>{const file=input.files[0];if(!file)return;try{saved=JSON.parse(await file.text());persist();renderAll();}catch(_){alert("标签 JSON 无法读取");}input.value="";};
  renderAll();
})();
</script>
""".replace("__SEED__", seed_json)


def expert_card(e, tz):
    recent = [p for p in e.get("papers", [])
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
    tracking = " · ".join(e.get("tracking_role") or [])
    pending = " · S2 profile 待核验" if e.get("profile_pending") else ""
    tracking_html = f'<div class="tracking">{html.escape(tracking + pending)}</div>' if tracking or pending else ""
    return f"""<div class="card">
      <div class="chead"><b>{html.escape(e['name'])}</b>
        <span class="aff">{html.escape(e.get('affiliation') or '')}</span></div>
{tracking_html}
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
    experts = merge_seed_experts(data.get("experts", []))
    gen = data.get("generated_at", "")
    total_infield = sum(e["in_field_count"] for e in experts)
    tz = json.loads(read("data/title_zh.json") or "{}")
    cards = "\n".join(expert_card(e, tz) for e in experts)
    tracked_cards = "\n".join(expert_card(e, tz) for e in experts if e.get("tracking_role"))
    new_work_rows = collect_new_work(experts, since=2026)
    new_work_rows = merge_homepage(new_work_rows)
    new_work = new_work_html(new_work_rows, tz)
    trends = json.loads(read("data/trends.json") or "{}")
    curated_trends = json.loads(read("data/trend_summaries_zh.json") or "{}")
    trend_blocks = trends.get("blocks", [])
    sec_html = "".join(trend_block_html(b, curated_trends) for b in trend_blocks[:2])
    trend_sample_status = (trends.get("big4_definition") or {}).get("sample_status", "")
    if trend_sample_status:
        sec_html = (
            f'<div class="coverage-note"><strong>趋势样本状态：</strong>'
            f'{html.escape(trend_sample_status)}</div>' + sec_html
        )
    sec_migration_html = security_migration_html(trends)
    genai_html = genai_topic_html(experts, trends, tz)
    genai_rows = collect_genai_rows(experts, trends)
    rule_based_usable_rows = collect_rule_based_usable_rows(experts, trends)
    hci_html = "".join(trend_block_html(b, curated_trends) for b in trend_blocks[2:4])
    official_usable = json.loads(read("data/usable_security_2026.json") or "{}")
    official_usable_section = official_usable_html(official_usable)
    advice_learning = json.loads(read("data/end_user_advice_learning_2025_2026.json") or "{}")
    advice_learning_section = advice_learning_html(advice_learning)
    user_experiments = json.loads(read("data/usable_security_experiments_2025_2026.json") or "{}")
    official_raw = json.loads(read("data/official_accepted_2026_raw.json") or "{}")
    automatic_experiments = collect_automatic_experiment_candidates(official_raw, user_experiments)
    user_experiments_section = user_experiments_html(user_experiments, automatic_experiments)
    usable_rows = collect_usable_hub_papers(
        official_usable, advice_learning, user_experiments, automatic_experiments, genai_rows,
        rule_based_usable_rows,
    )
    usable_hub_section = usable_security_hub_html(usable_rows)
    expert_security_themes = expert_themes_html(experts, "security", tz)
    expert_hci_themes = expert_themes_html(experts, "hci", tz)
    paper_tag_seed = json.loads(read("data/paper_tags.json") or "{}")
    tag_assets = tag_interaction_assets(paper_tag_seed)

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
.coverage-note{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px;margin:0 0 16px}}
.coverage-note p{{margin:6px 0 0;color:var(--mut);font-size:13px}}.coverage-note ul{{margin:8px 0 0;padding:0;list-style:none;display:grid;gap:5px}}
.coverage-note li{{display:grid;grid-template-columns:130px 1fr;gap:8px;font-size:12px}}.coverage-note li span{{color:var(--mut)}}
.official-group,.advice-group{{margin:18px 0}}.official-group h3,.advice-group h3{{display:flex;justify-content:space-between;gap:10px;font-size:14px}}
.official-group h3 span,.advice-group h3 span{{color:var(--mut);font-size:12px;font-weight:400}}
.official-grid,.advice-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(330px,1fr));gap:12px}}
.official-paper,.advice-paper{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px}}
.official-paper h4,.advice-paper h4{{margin:4px 0 7px;font-size:14px;line-height:1.4}}
.official-paper h4 a,.advice-paper h4 a{{color:var(--fg);text-decoration:none}}
.official-paper h4 a:hover,.advice-paper h4 a:hover{{color:var(--acc)}}
.official-paper p,.advice-paper p{{margin:7px 0;color:var(--mut);font-size:12.5px}}
.author-line,.method-line{{font-size:11.5px;color:var(--mut);margin-top:5px}}
.topic-chip{{display:inline-block;background:#e5edff;color:#2050c0;border-radius:999px;padding:2px 7px;font-size:11px}}
.experiment-group{{margin:18px 0}}.experiment-group h3{{display:flex;justify-content:space-between;gap:10px;font-size:14px}}
.experiment-group h3 span{{color:var(--mut);font-size:12px;font-weight:400}}
.experiment-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}}
.experiment-paper{{background:var(--card);border:1px solid var(--line);border-radius:9px;padding:12px}}
.experiment-paper h4{{margin:4px 0 8px;font-size:14px;line-height:1.4}}
.experiment-paper h4 a{{color:var(--fg);text-decoration:none}}.experiment-paper h4 a:hover{{color:var(--acc)}}
.experiment-paper p{{margin:6px 0;color:var(--mut);font-size:12.5px}}
.experiment-paper p strong{{color:var(--fg)}}.experiment-takeaway{{border-top:1px dashed var(--line);padding-top:7px}}
.experiment-badge{{display:inline-block;border-radius:999px;padding:2px 7px;font-size:11px;margin-right:5px;background:#e7f5ed;color:#137333}}
.experiment-badge.controlled_comparison{{background:#fff4df;color:#9a5b00}}
.experiment-badge.exploratory_comparison{{background:#f3e9ff;color:#7a3ec0}}
.tracking{{color:var(--acc);font-size:11px;margin:3px 0}}
@media(prefers-color-scheme:dark){{.topic-chip{{background:#22345e;color:#9dbcff}}.experiment-badge{{background:#193a25;color:#8fe0a5}}.experiment-badge.controlled_comparison{{background:#3d2d12;color:#f1c27d}}.experiment-badge.exploratory_comparison{{background:#33234d;color:#c8a6ff}}}}
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
    style_match = re.search(r"(?s)<style>.*?</style>", doc)
    style_tag = style_match.group(0) if style_match else ""

    # Main dashboard: four research workspaces; full expert library stays on experts.html.
    doc = re.sub(
        r"(?s)<nav>.*?</nav>",
        '<nav><a href="#ongoing">On-going</a><a href="#usable">Usable Security</a>'
        '<a href="#cybersecurity">网络安全</a><a href="#hci">HCI</a>'
        '<a href="experts.html">大牛库 ↗</a></nav>',
        doc,
        count=1,
    )
    main_content = (
        '<main>'
        '<div class="workspace-intro">'
        '<a href="#ongoing"><b>On-going</b><span>正在推进的安全建议与知识学习</span></a>'
        '<a href="#usable"><b>Usable Security</b><span>按来源，再按 GenAI / 建议学习 / 其他主题</span></a>'
        '<a href="#cybersecurity"><b>网络安全</b><span>趋势、话题传导与大牛主题</span></a>'
        '<a href="#hci"><b>HCI</b><span>指定 HCI 来源趋势与大牛主题</span></a>'
        '</div>'
        '<div id="tag-toolbar" class="tag-toolbar"></div>'
        '<input id="tag-import" type="file" accept="application/json" hidden>'
        '<section id="ongoing"><h2>On-going · 终端用户安全建议与安全知识学习</h2>'
        '<div class="coverage-note"><strong>当前工作区</strong><p>'
        '这里自动汇总所有带“安全建议与学习”标签的论文；您在其他专题给论文增加该标签后，它会立即进入这里。'
        '</p></div><div id="ongoing-dynamic" class="ongoing-grid"></div>'
        '<details class="deep-dive"><summary>查看人工整理的 2025–2026 证据详情</summary>'
        f'{advice_learning_section}</details></section>'
        '<section id="usable"><h2>Usable Security 专题</h2>'
        f'{usable_hub_section}'
        '<details class="deep-dive"><summary>查看用户实验 / A-B Test 方法详情</summary>'
        f'{user_experiments_section}</details>'
        '<details class="deep-dive"><summary>查看 GenAI × Usable Security 扩展证据</summary>'
        f'{genai_html}</details></section>'
        '<section id="cybersecurity" class="trend"><h2>网络安全专题</h2>'
        '<h3>大牛库 · 2025–2026 网络安全论文主题</h3>'
        f'{expert_security_themes}'
        '<h3>安全四大与 SOUPS/PETS · 话题传导</h3>'
        f'{sec_migration_html}'
        '<h3>网络安全趋势</h3>'
        f'{sec_html}</section>'
        '<section id="hci" class="trend"><h2>HCI 专题</h2>'
        '<h3>大牛库 · 2025–2026 HCI 论文主题</h3>'
        f'{expert_hci_themes}'
        '<h3>HCI 隐私与安全趋势</h3>'
        f'{hci_html}</section>'
        '</main>'
    )
    # Use a callable replacement so backslashes in paper titles/abstracts are
    # treated as literal content instead of regex replacement escapes.
    doc = re.sub(r"(?s)<main>.*?</main>", lambda _match: main_content, doc, count=1)
    doc = doc.replace("</body>", f"{tag_assets}</body>", 1)

    experts_doc = f"""<!doctype html>
<html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>大牛库 · Usable Security / HCI</title>
{style_tag}</head><body>
<header><h1>大牛库 · Usable Security / HCI</h1>
<div class="sub">{len(experts)} 人 · 领域内论文 {total_infield} 篇 · 数据更新 {gen}</div></header>
<nav><a href="index.html">← 主看板</a><a href="#new">2026 新工作</a>
<a href="#new-authors">2026 新增作者</a><a href="#experts">完整大牛库</a></nav>
<main>
<section id="new"><h2>大牛 2026 年以来新工作</h2>
<div class="new-work">{new_work}</div></section>
<section id="new-authors"><h2>2026 最新 Usable Security · 新增一作与通讯作者</h2>
<div class="coverage-note"><p>一作按官方作者顺序加入；通讯作者仅在论文 PDF 或作者主页明确标注时认定。
没有可靠 Semantic Scholar ID 的作者标为“待核验”，不会自动绑定同名 profile。</p></div>
<div class="grid">{tracked_cards}</div></section>
<section id="experts"><h2>完整大牛库 · 各学者最近论文</h2>
<div class="grid">{cards}</div></section>
</main></body></html>"""
    experts_doc = experts_doc.replace(
        "<main>",
        '<main><div id="tag-toolbar" class="tag-toolbar"></div>'
        '<input id="tag-import" type="file" accept="application/json" hidden>',
        1,
    )
    experts_doc = experts_doc.replace("</body>", f"{tag_assets}</body>", 1)

    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(doc)
    open(os.path.join(ROOT, "experts.html"), "w", encoding="utf-8").write(experts_doc)
    print(f"看板已生成 index.html + experts.html（{len(experts)} 位追踪作者，{total_infield} 篇领域内论文）")

if __name__ == "__main__":
    main()
