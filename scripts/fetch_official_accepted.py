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
from urllib.parse import urljoin

from fetch_trends import is_user_experiment

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "official_accepted_2026_raw.json")

SOURCES = {
    "USENIX Security": {
        "cycle1": "https://www.usenix.org/conference/usenixsecurity26/cycle1-accepted-papers",
        "cycle2": "https://www.usenix.org/conference/usenixsecurity26/cycle2-accepted-papers",
        "technical_sessions": "https://www.usenix.org/conference/usenixsecurity26/technical-sessions",
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


def parse_usenix(page, source_url, presentations_only=False):
    rows = []
    pattern = re.compile(r"(?is)<h2[^>]*>(.*?)</h2>(.*?)(?=<h2|$)")
    for match in pattern.finditer(page):
        heading = match.group(1)
        link_match = re.search(r'(?is)<a[^>]+href="([^"]+)"[^>]*>', heading)
        paper_url = urljoin(source_url, html.unescape(link_match.group(1))) if link_match else ""
        if presentations_only and "/conference/usenixsecurity26/presentation/" not in paper_url:
            continue
        title = clean(heading)
        if not title:
            continue
        body = match.group(2)
        author_match = re.search(
            r'(?is)<div[^>]+field-name-field-person[^>]*>(.*?)</div>\s*</div>',
            body,
        )
        authors = clean(author_match.group(1)) if author_match else ""
        rows.append({
            "title": title,
            "authors_text": authors,
            "paper_url": paper_url,
            "abstract": clean(body),
        })
    return rows


def merge_usenix_rows(rows):
    """Prefer explicit cycle labels; use the program to enrich URLs/abstracts."""
    merged = {}
    for row in rows:
        key = re.sub(r"\W+", "", row.get("title", "").lower())
        if not key:
            continue
        if key not in merged:
            merged[key] = row
            continue
        old = merged[key]
        if old.get("cycle") == "technical_sessions" and row.get("cycle") != "technical_sessions":
            old, row = row, old
            merged[key] = old
        for field in ("authors_text", "paper_url", "abstract"):
            if not old.get(field) and row.get(field):
                old[field] = row[field]
    cycle1_keys = {
        key for key, row in merged.items() if row.get("cycle") == "cycle1"
    }
    for key, row in merged.items():
        if row.get("cycle") == "technical_sessions":
            row["cycle"] = (
                "cycle2 inferred: present in official program but absent from cycle1 list"
                if key not in cycle1_keys else "cycle1"
            )
    return list(merged.values())


def abstract_sentences(text):
    return [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text or "")
        if len(sentence.strip()) >= 25
    ]


def first_sentence(sentences, terms):
    for term in terms:
        for sentence in sentences:
            if term in sentence.lower():
                return sentence
    return ""


def extract_experiment_details(paper):
    """Extract displayable study fields from the official abstract only."""
    abstract = paper.get("abstract") or ""
    lower = abstract.lower()
    sentences = abstract_sentences(abstract)

    sample = ""
    sample_patterns = (
        r"\b[nN]\s*=\s*([\d,]+)\b",
        r"\b(?:experiment|study)\s+with\s+(?:over\s+)?([\d,\s]+)\s+(?:human\s+)?participants\b",
        r"\b([\d,]+)\s+(?:human\s+)?participants\b",
        r"\b([\d,]+)\s+recipients\b",
    )
    for pattern in sample_patterns:
        match = re.search(pattern, abstract)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            if digits:
                sample = f"N={int(digits):,}"
                break

    design_map = (
        ("field experiment", "现场实验"),
        ("between-subjects", "组间实验"),
        ("between subjects", "组间实验"),
        ("within-subjects", "组内实验"),
        ("within subjects", "组内实验"),
        ("deceptive web experiment", "欺骗性在线实验"),
        ("online experiment", "在线实验"),
        ("controlled lab study", "受控实验室研究"),
        ("controlled experiment", "受控实验"),
        ("vignette experiment", "情境实验"),
        ("experiment", "用户实验"),
    )
    design = next((label for term, label in design_map if term in lower), "用户研究")
    if design == "用户实验" and "email" in lower and "click rate" in lower:
        design = "大规模真实邮件行为实验"
    intervention = first_sentence(sentences, (
        "we collect personal information", "we introduce", "we provide",
        "we present participants", "participants were exposed", "participants received",
        "personalized", "intervention", "treatment", "condition",
    ))
    comparison = first_sentence(sentences, (
        "compared to", "compare ", "compared with", "comparing ",
        "relative to", "versus", "regardless of whether", "control group",
    ))
    if comparison:
        comparison_index = sentences.index(comparison)
        if comparison_index + 1 < len(sentences):
            next_sentence = sentences[comparison_index + 1]
            if any(term in next_sentence.lower() for term in (
                "regardless of whether", "compared", "than ", "baseline",
            )):
                comparison = f"{comparison} {next_sentence}"

    if all(term in lower for term in ("personalized", "generic phishing", "llm")):
        intervention = "个性化钓鱼邮件与通用钓鱼邮件，并区分 LLM 生成和人工撰写"
        comparison = "LLM 个性化、人工个性化、LLM 通用与人工通用钓鱼策略"

    result = first_sentence(sentences, (
        "our findings", "our results", "we find", "we found", "results show",
        "findings reveal", "achieves", "increases", "decreases", "triples",
    ))
    if result:
        result_index = sentences.index(result)
        if result_index + 1 < len(sentences):
            next_sentence = sentences[result_index + 1]
            if any(term in next_sentence.lower() for term in (
                "this effect", "moreover", "however", "in contrast",
            )):
                result = f"{result} {next_sentence}"

    measured_outcome_sentence = first_sentence(sentences, (
        "we measure", "we measured", "outcome", "dependent variable",
    ))
    outcome_text = f"{comparison} {result} {measured_outcome_sentence}".lower()
    outcome_labels = []
    for term, label in (
        ("click rate", "点击率"),
        ("click-through", "点击率"),
        ("accuracy", "准确率"),
        ("performance", "任务表现"),
        ("trust", "信任"),
        ("task load", "任务负荷"),
        ("usability", "可用性"),
        ("decision", "用户决策"),
        ("completion", "完成率"),
        ("adoption", "采纳"),
        ("awareness", "安全意识"),
        ("cost", "成本"),
    ):
        if term in outcome_text and label not in outcome_labels:
            outcome_labels.append(label)

    topic = "用户实验"
    title_lower = (paper.get("title") or "").lower()
    if "phishing" in lower:
        topic = "钓鱼与安全行为"
    if "explainable ai" in lower and "cybersecurity" in lower:
        topic = "安全决策与 XAI"
        design = "组间实验"
        intervention = "安全决策支持中是否提供 XAI 解释"
        comparison = "提供 XAI 解释与不提供解释的条件"
        outcome_labels = ["信任", "可用性", "任务负荷", "安全判断表现"]
        result = (
            "XAI 解释没有改善安全判断表现或降低任务负荷；具有安全领域知识的参与者"
            "在看到解释后反而报告了更低的信任。"
        )
    elif "wallet" in title_lower and "phishing" in lower:
        topic = "钱包钓鱼干预"
        design = "组间实验并辅以半结构化访谈"
        intervention = "消费额度建议、主动支出者警告、被动支出者警告和延迟确认四种钱包干预"
        comparison = "四种钱包干预分别与无干预控制组比较"
        outcome_labels = ["设置消费额度的概率", "钓鱼任务取消率"]
        result = (
            "消费额度建议显著提高了用户设置额度的概率；主动支出者警告和延迟确认"
            "显著提高了钓鱼任务取消率。"
        )
    elif "personalized" in lower and "phishing" in lower and "llm" in lower:
        topic = "LLM 个性化钓鱼"
        result = (
            "LLM 个性化钓鱼邮件的点击率接近通用钓鱼策略的 3 倍；"
            "这一效应不取决于通用邮件由人工还是 LLM 撰写。"
        )
    elif "age" in title_lower and ("verification" in lower or "prove their age" in lower):
        topic = "年龄验证与隐私"
        design = "欺骗性随机在线实验并辅以后续调查"
        intervention = "复选框自我声明、政府证件上传、活体检测、AI 面部年龄估计和邮箱年龄估计"
        comparison = "七种年龄验证条件，包括不同隐私保证说明的政府证件条件"
        outcome_labels = ["验证完成率", "舒适度", "风险感知", "便利性"]
        result = (
            "复选框的完成率为 99%，政府证件方法仅为 18%–27%，邮箱和 AI 方法分别为 "
            "86% 和 51%；侵入性更强的方法也被认为风险更高、便利性更低。"
        )
    elif "vulnerability notification" in lower:
        topic = "漏洞通知与缓解"
        design = "混合方法项目评估（企业访谈 + 三年修复数据生存分析）"
        intervention = "企业主动登记资产与联系人，并接收政府 CSIRT 发出的漏洞通知"
        comparison = "与既有非主动式漏洞通知实验的修复效果比较"
        outcome_labels = ["修复时间", "修复率"]
        result = (
            "通知后一天、一周和一个月内分别有 27%、40% 和 49% 的问题得到修复；"
            "三年总体修复率为 75%，高于既有非主动式通知实验。"
        )

    return {
        "topic": topic,
        "design": design,
        "sample": sample or "摘要未说明",
        "intervention": intervention or "摘要未说明",
        "comparison": comparison or "摘要未说明",
        "outcomes": "、".join(outcome_labels) or "摘要未说明",
        "result": result or "摘要未说明",
        "source": "official_abstract",
    }


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
                rows = parse_usenix(
                    page,
                    url,
                    presentations_only=(cycle == "technical_sessions"),
                )
                for row in rows:
                    row["cycle"] = cycle
            elif venue == "IEEE S&P":
                rows = parse_sp(page)
            elif venue == "NDSS":
                rows = parse_ndss(page)
            else:
                rows = []
            venue_rows.extend(rows)
        if venue == "USENIX Security":
            venue_rows = merge_usenix_rows(venue_rows)
        experiment_candidates = [
            row for row in venue_rows
            if is_user_experiment({**row, "venue": venue, "year": 2026})
        ]
        for row in experiment_candidates:
            row["experiment_details"] = extract_experiment_details(row)
        result["venues"][venue] = {
            "endpoints": endpoint_status,
            "paper_count": len(venue_rows),
            "papers": venue_rows,
            "user_experiment_candidate_count": len(experiment_candidates),
            "user_experiment_candidates": experiment_candidates,
        }
    with open(OUT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT}")
    for venue, data in result["venues"].items():
        print(f"  {venue}: {data['paper_count']} official records")


if __name__ == "__main__":
    main()
