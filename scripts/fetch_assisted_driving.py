#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fetch_assisted_driving.py — 只抓 2025-2026 辅助驾驶的人因/用户研究。

复用 fetch_trends 的检索与过滤规则，独立成文件，避免整轮趋势抓取的限流成本。
输出: data/assisted_driving_2025_2026.json
"""
import json, os, time
from fetch_trends import assisted_driving_rows, DRIVING_QUERY

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "data", "assisted_driving_2025_2026.json")


def main():
    rows = assisted_driving_rows()
    with_method = [p for p in rows if p.get("user_study_evidence")]
    if not rows:
        # An empty harvest is almost always rate limiting, not an empty field.
        raise RuntimeError("辅助驾驶检索返回 0 篇，疑似限流；保留既有输出")
    payload = {
        "generated_at": time.strftime("%Y-%m-%d"),
        "scope": "2025-2026 辅助驾驶 / 自动驾驶的人因与用户研究；来源分 big4、"
                 "hci_ccf_a（CHI/UbiComp/TOCHI/IJHCS）与 hci_watch（CSCW/IMWUT 等观察来源）",
        "query": DRIVING_QUERY,
        "filter": "强指示词命中，或 driver/driving 与车辆语境词同现；"
                  "user_study_evidence 单独标注方法证据",
        "count": len(rows),
        "with_user_study_evidence": len(with_method),
        "papers": rows,
    }
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"写入 {OUT}：{len(rows)} 篇，其中有方法证据 {len(with_method)} 篇")


if __name__ == "__main__":
    main()
