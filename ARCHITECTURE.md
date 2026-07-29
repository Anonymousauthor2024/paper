# 论文追踪知识库 · 架构与搭建方法

一个追踪 **usable security / HCI 隐私安全** 领域的论文知识库。核心思路：**数据抓取与展示分离**——几个脚本把数据从 Semantic Scholar 拉下来、处理后存成文件，看板脚本只读这些文件拼成网页，不联网、不重算。

## 数据流

```
Semantic Scholar API
      │
      ├─ scripts/fetch_experts.py  ─→ data/experts_papers.json      （大牛论文，去重+分类）
      │                            ─→ people/latest_by_expert.md
      │                            ─→ security|hci/experts/latest.md
      ├─ scripts/find_profiles.py  ─→ people/profile_audit.md        （profile 查漏报告）
      ├─ scripts/fetch_trends.py   ─→ security|hci/trends/latest.md   （领域趋势）
      │                            ─→ data/trends.json
      │
   （人工维护）people/experts.json（大牛种子）  data/title_zh.json（中文翻译）
      │
      ▼
   scripts/build_dashboard.py  ─→ index.html                        （自包含单页看板）
```

## 各部件职责

### 数据源
Semantic Scholar Academic Graph API（免费，无需 key；可选环境变量 `S2_API_KEY` 提速）。提供作者、论文、venue、引用数、arXiv 链接等。

### people/experts.json —— 大牛种子库（人工维护）
每位大牛一条记录。**关键设计：`ss_author_ids` 是一组 id 而非一个**，因为 Semantic Scholar 的作者消歧不可靠，常把同一个人拆成多个 profile。字段：`name / affiliation / role / known_for / ss_author_ids / dblp / note`。

### scripts/fetch_experts.py —— 大牛论文抓取
读种子库，把每位大牛**所有 profile** 的论文都拉下来、按 `paperId` 去重，再按会议 venue 分成四类：
- `security`：四大会（USENIX/S&P/CCS/NDSS）+ SOUPS + PETS
- `hci`：CHI / CSCW(PACM HCI)
- `preprint`：arXiv，且标题含领域词（否则降级 other，挡掉混入的无关论文）
- `other`：其余

输出全量结构化 json 和按学者/按领域的 markdown 清单。直接列最近论文标题（不做机器关键词提炼——实测标题关键词提炼会被跨领域论文和技术词污染，不可靠）。

### scripts/find_profiles.py —— profile 查漏
对每位大牛搜同名 profile，用 batch 接口拉候选的 venue，按 usable security/HCI 会议论文认领，报告"疑似漏绑"的 id 供人工确认。补进 `experts.json` 后 Yixin Zou 就从 7 篇领域论文补到了 35 篇。局限：只按会议 venue 认领，只发 arXiv 的新 profile 可能漏检；对超常见名（如 Yang Wang）search 覆盖不到小 profile。

### scripts/fetch_trends.py —— 领域趋势
按会议名批量拉领域论文（SOUPS+PETS 全收；四大会用 `interview | survey | questionnaire` 过滤出用户研究论文；CHI 用 `privacy|security|…` 过滤）。算两个信号：
- **新兴关键词**：论文分基线（2020–2023）和近期（2024–2026）两段，按"近期文档频率 ÷ 基线文档频率"排，增长快的是新趋势。
- **引用增速**：近年论文按"总引用 ÷ 论文年龄"排，年均被引高的是高影响工作。

### data/title_zh.json —— 中文翻译对照表
`paperId → {en, zh}`。翻译单独存，不混进抓取逻辑。看板按 paperId 查中文。

### scripts/build_dashboard.py —— 看板生成
读上述所有产物，拼成一个 `index.html`：
- 大牛库：读 `experts_papers.json`，过滤 2025+ 领域内论文，每篇配 `title_zh.json` 的中文，渲染成卡片（tag / venue / 年份 / 🆕 / 可点链接）。
- 趋势：读两个 trends markdown，简单转 HTML 嵌入。
- 内联 CSS，深浅色自适应，纯静态，可直接用 GitHub Pages 托管。

## 关键设计决策与踩过的坑

- **SS 作者消歧不可靠**：必须多 profile 合并去重 + 定期用 `find_profiles.py` 查漏，否则漏一半论文。
- **venue 靠会议名匹配**：CHI 在 SS 里是 "International Conference on Human Factors in Computing Systems"；CCS 用全名；CSCW 名字很乱，第一版用 CHI 为 HCI 主力。
- **四大会区分 usable**：用 `interview | survey` 过滤比 "usable" 更准——用户研究论文一定提访谈/问卷，系统安全论文不会。
- **SS query 语法**：空格必须编码成 `%20`（`+` 会被当成 AND 操作符）；多词短语不加引号也会被当 AND。
- **趋势是统计出来的**，不是人工总结——词频文档频率增长 + 引用增速。
- **不做标题关键词自动提炼**：会被跨领域论文和技术词污染，改成直接列论文标题。

## 目录结构

```
paper/
├── people/
│   ├── experts.json           # 大牛种子（人工维护）
│   ├── latest_by_expert.md    # 按学者的最近论文
│   └── profile_audit.md       # 查漏报告
├── security/{experts,traditional,trends}/latest.md
├── hci/{experts,traditional,trends}/latest.md
├── scripts/
│   ├── fetch_experts.py
│   ├── find_profiles.py
│   ├── fetch_trends.py
│   └── build_dashboard.py
├── data/
│   ├── experts_papers.json
│   ├── trends.json
│   └── title_zh.json
├── index.html                 # 看板
├── progress.md
└── ARCHITECTURE.md            # 本文件
```

## 怎么更新

手动依次运行：

```bash
python scripts/fetch_experts.py    # 拉大牛论文
python scripts/find_profiles.py    # （可选）查漏
python scripts/fetch_trends.py     # 拉领域趋势
python scripts/build_dashboard.py  # 重新生成 index.html
```

翻译表 `data/title_zh.json` 在有新 2025+ 论文时需补充对应 `paperId` 的中文。

## 待办

- GitHub Actions 定时自动跑上面四个脚本并 push
- 整体趋势（整个安全 / 整个 HCI，与 usable / 隐私安全子领域对比）
- GitHub Pages 发布看板

## 2026-07-29 架构更新

- 安全四大固定为：IEEE S&P、NDSS、USENIX Security、ACM CCS。`scripts/fetch_trends.py`
  为每个会议维护 Semantic Scholar venue 别名。
- 四大会 usable-security 子集采用两阶段方法：先检索
  `interview / survey / questionnaire / usable / usability / user study / human-centered`，
  再要求标题或摘要同时出现人本研究范围和用户研究方法证据。
- `scripts/fetch_official_accepted.py` 只抓取官方 2026 accepted-paper 页面，输出
  `data/official_accepted_2026_raw.json`；页面不存在表示“尚未公开”，不表示零篇论文。
- `data/usable_security_2026.json` 是人工核验的 2026 Big4 usable-security 子集，记录会议、
  Cycle、方法、一作、通讯作者证据和中文简介。
- `data/end_user_advice_learning_2025_2026.json` 单独维护终端用户安全建议、安全知识获得、
  意识测量、教育干预和警告理解相关论文。
- `scripts/build_dashboard.py` 生成两个本地页面：
  - `index.html`：2026 Big4 最新工作、建议/学习专题、趋势和 GenAI 专题；
  - `experts.html`：大牛 2026 新工作置顶，其后为 2026 新增作者和完整大牛库。
- 通讯作者只在论文 PDF、出版页或作者主页明确标注时认定；不以末位作者自动推断。
