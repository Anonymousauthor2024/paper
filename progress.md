# 论文追踪知识库 — Progress

## 项目目标
一个论文追踪知识库，聚焦两个领域：

- **Usable Security（安全可用性）**：安全四大会（CCS / USENIX Security / NDSS / S&P）+ SOUPS 中用了质性 / 用户研究方法的论文。
- **HCI 隐私安全**：CHI / CSCW 中 security & privacy 相关论文，重点标注 AI / LLM 相关。

三个追踪维度：
1. **传统方向新工作** —— 按关键词 + 目标会议过滤。
2. **领域新趋势** —— 关键词增长率 + 引用增速。
3. **大牛库（核心）** —— 只追领域大牛的新论文，用"人"过滤质量；检测大牛转向的新方向作为趋势预警。

## 架构决定
- 用**目录**分领域，不用 git branch。
- 数据源：**Semantic Scholar API + arXiv + DBLP**。
- 更新方式：**GitHub Actions 定时（cron）云端跑**，不依赖本地开机；结果自动 commit 回仓库。
- 展示：**GitHub Pages 网页看板**。
- 大牛库**不预先分 security/hci**；抓到的论文按 venue 自动归到 `security/` 或 `hci/`。

## 关键工程点
- **Semantic Scholar 作者消歧不可靠**：一个大牛常被拆成多个 profile（Yang Wang 5 个、Schaub / Cranor 各 2 个）。库里每个大牛绑定一组 `ss_author_ids`，抓取时全部拉取并去重，否则会漏论文。
- 计划补 **DBLP 作者页**作为兜底（DBLP 消歧更稳）。

## 大牛库种子（v1，已确认，共 8 人）
见 `people/experts.json`：
Yang Wang, Yaman Yu, Yixin Zou, Jingjie Li, Tanusree Sharma, Kanye Ye Wang, Florian Schaub, Lorrie Faith Cranor。

种子来源：从 Yaman Yu / Kanye Ye Wang 的合作网扩展，人工按方向筛选，剔除自动驾驶 / 联邦学习等无关方向的高产合作者。

## 目录结构
```
paper/
├── people/experts.json      # 大牛库种子
├── security/
│   ├── experts/             # 大牛在安全会议的新论文
│   ├── traditional/         # usable security 关键词新工作
│   └── trends/              # 安全领域新趋势
├── hci/
│   ├── experts/             # 大牛在 CHI/CSCW 的新论文
│   ├── traditional/         # HCI 隐私安全关键词新工作
│   └── trends/              # HCI 领域新趋势
├── scripts/                 # 抓取脚本
├── data/                    # 结构化元数据(json)
└── progress.md
```

## 待办
- [x] `scripts/fetch_experts.py`：拉每个大牛的论文，多 profile 合并去重，按 venue 归类，直接列最近论文
- [x] `scripts/find_profiles.py`：扫描同名 SS profile 查漏，补齐漏绑 id（输出 `people/profile_audit.md`）
- [x] 大牛"新方向"检测 → 改为直接列最近论文标题（自动关键词提炼不可靠，已放弃）
- [ ] `scripts/fetch_trends.py`：全领域关键词增长 + 引用增速
- [ ] 补全每个大牛的 DBLP 作者页
- [ ] GitHub Actions 定时配置
- [ ] HTML 看板 + GitHub Pages
- [ ] 候选大牛榜脚本（SOUPS + CHI/CSCW 高频作者）扩展 experts

## 进度日志
- **2026-07-28**：确定架构与数据源；验证 Semantic Scholar API 可用；定位并确认 8 位种子大牛（解决 Yang Wang 5-profile、Schaub/Cranor 2-profile 合并问题）；建目录骨架 + `people/experts.json` + `progress.md`；首次 push。
- **2026-07-28（续）**：实现 `fetch_experts.py`（多 profile 合并、venue 分类、直接列最近论文、18 月窗口）；新增 `find_profiles.py` 查漏工具，补齐 5 位大牛漏绑 profile（Yixin Zou 领域内 7→35 篇，Jingjie/Tanusree/Schaub/Cranor 各有补绑）；更新全部输出与 `profile_audit.md`。人工排除 Tanusree 的同名误绑（Final Fantasy）与 Yang Wang 合作网补查。
- **2026-07-29**：确认安全四大为 IEEE S&P / NDSS / USENIX Security / ACM CCS；扩展
  Big4 usable-security 检索到 `usable / usability / user study / human-centered`，并增加摘要方法证据筛选。
  新增官方 accepted-paper 审计脚本、2026 Big4 人工核验子集和 2025–2026 终端用户安全建议/
  安全知识学习专题。看板拆分为 `index.html` 与 `experts.html`，大牛 2026 新工作在大牛页置顶。
  新增作者按官方一作顺序加入；通讯作者仅在有明确证据时标注。
- **2026-07-29（用户实验专题）**：新增 A/B test、随机/受控实验、组间/组内、因子实验、
  现场/在线实验等检索词，并要求“干预/操纵 + 比较条件 + 真实参与者 + 安全结果指标”。
  人工核验 2025–2026 代表性研究，按强实验、受控比较、探索性比较分级，加入主看板独立模块。
- **2026-07-29（自动召回校验）**：USENIX 2026 抓取扩展到 Technical Sessions /
  presentation 页面；实验规则加入通用 `experiment`，但强制要求明确人类研究证据。
  重跑后自动召回 Czybik 等 5 篇候选，未向人工专题数据直接插入论文。
- **2026-07-29（摘要结构化）**：官方实验论文直接并入对应年份/来源的已有结果，
  与人工专题使用相同展示且不显示自动标签。设计、样本、操纵、比较、结果指标、
  主要结果和话题均从 abstract 自动抽取；与人工专题去重且不修改人工 JSON。
- **2026-07-29（四专题与标签）**：主看板改为 On-going、Usable Security、网络安全、
  HCI 四个工作区。Usable Security 按“安全四大 / 其他安全会议 / 指定 HCI 来源”分层，
  每层再分 GenAI、安全建议与学习、其他主题并允许交叉。网络安全与 HCI 分别增加大牛库
  2025–2026 论文主题切片；HCI 仅纳入 CHI、CSCW、TOCHI、UbiComp/IMWUT、IJHCS，
  排除 IJHCI。新增浏览器本地多标签、标签筛选及 JSON 导入导出功能。
- **2026-07-29（统一主题标签）**：取消 Usable Security 的笼统“其他”分组，改为复用
  网络安全专题的七类研究主题；按标题、主题、简介、摘要、方法和实验字段多标签匹配，
  同一论文可同时出现在多个主题，只有完全未命中的论文进入“其他新方向”。
