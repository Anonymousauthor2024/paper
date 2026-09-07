# 安全领域 · 新趋势

## 子领域 · usable security（SOUPS + PETS + 四大会 usable/user study）
_样本 1186 篇（基线 581 篇 2020-2023 / 近期 605 篇 2024-2026）_

### 趋势解读
- **生成式 AI 正进入可用安全与隐私研究**：agents、LLM-based 与 LLMs 从基线期近乎缺席转为近期集中出现，说明研究问题已从传统界面与行为风险扩展到人与生成式 AI 的安全互动、信任和防护。
- **隐私保护机制仍是稳定主线**：privacy、private、privacy-preserving 与 local differential privacy 同时处于高频或快速增长位置，表明该子领域继续关注如何让隐私机制既可验证又能被实际使用和理解。
- **风险研究继续贴近日常使用场景**：phishing、perceptions、web 与 fingerprinting 指向用户对欺诈、跟踪和网络隐私风险的理解与应对；这比安全整体榜单更强调人的判断与使用情境。

### 引用增速最快的代表论文（Top 5）
- **[Do Users Write More Insecure Code with AI Assistants?](https://arxiv.org/abs/2211.03622)**（2022，年均 86.4，共 432）——暂无人工核对的中文简介；请查看原始摘要。
- **[GLAZE: Protecting Artists from Style Mimicry by Text-to-Image Models](https://arxiv.org/abs/2302.04222)**（2023，年均 76.0，共 304）——Glaze 让艺术家在公开作品前加入人眼几乎不可察觉的“风格斗篷”，使生成模型在使用这些图片微调时难以准确模仿艺术风格。对千余名艺术家的研究及实验结果显示，它在常规条件和适应性反制下都能显著破坏风格模仿，同时兼顾可用性与扰动可接受度。
- **[SoK: Taxonomy of Attacks on Open-Source Software Supply Chains](https://arxiv.org/abs/2204.04008)**（2022，年均 63.6，共 318）——论文构建了一个跨编程语言和生态的开源软件供应链攻击分类，以攻击树覆盖从代码贡献到软件包分发的全过程，并整理出 107 种攻击向量、94 起真实事件和 33 项缓解措施。17 名领域专家和 134 名开发者的调查验证了该分类的正确性、完整性和可理解性，并评价了各项防护的效用与成本。
- **[99% False Positives: A Qualitative Study of SOC Analysts' Perspectives on Security Alarms](https://www.usenix.org/conference/usenixsecurity22/presentation/alahmadi)**（2022，年均 47.2，共 236）——研究通过 20 名 SOC 从业者的在线调查和 21 名安全从业者的定性研究考察安全告警中的高误报问题，发现许多所谓“误报”其实是由组织内合法行为触发、但被分析师选择忽略的真实告警。论文指出手工验证会造成告警疲劳，并提出可靠、可解释、可分析、情境化和可迁移五项告警设计要求。
- **[Don't Listen To Me: Understanding and Exploring Jailbreak Prompts of Large Language Models](https://arxiv.org/abs/2403.17336)**（2024，年均 43.0，共 129）——暂无人工核对的中文简介；请查看原始摘要。

### 其余高增速论文（6–15）
- 2024 | 年均 40.3 — **[DeGPT: Optimizing Decompiler Output with LLM](https://www.semanticscholar.org/paper/32bb8b85124e554dd995e1c3a102eb921a710a99)**
- 2022 | 年均 39.0 — **[Lost at C: A User Study on the Security Implications of Large Language Model Code Assistants](https://arxiv.org/abs/2208.09727)**
- 2023 | 年均 33.8 — **[SoK: Secure Aggregation Based on Cryptographic Schemes for Federated Learning](https://www.semanticscholar.org/paper/b7882b7243cfe4b64006f42865e70ebfbf09d6ce)**
- 2023 | 年均 32.0 — **[SoK: History is a Vast Early Warning System: Auditing the Provenance of System Intrusions](https://www.semanticscholar.org/paper/7598956efd3cdda714509f02aa1907984525c481)**
- 2022 | 年均 26.6 — **[Universal Atomic Swaps: Secure Exchange of Coins Across All Blockchains](https://www.semanticscholar.org/paper/b361a12c714b2d5cf8a6239ed37d01a332878952)**
- 2024 | 年均 26.3 — **[Using AI Assistants in Software Development: A Qualitative Study on Security Practices and Concerns](https://arxiv.org/abs/2405.06371)**
- 2024 | 年均 25.7 — **[An LLM-Assisted Easy-to-Trigger Backdoor Attack on Code Completion Models: Injecting Disguised Vulnerabilities against Strong Detection](https://arxiv.org/abs/2406.06822)**
- 2024 | 年均 25.3 — **[SafeGen: Mitigating Sexually Explicit Content Generation in Text-to-Image Models](https://arxiv.org/abs/2404.06666)**
- 2022 | 年均 24.0 — **[A Unified Framework for Quantifying Privacy Risk in Synthetic Data](https://arxiv.org/abs/2211.10459)**
- 2024 | 年均 22.0 — **[SafeEar: Content Privacy-Preserving Audio Deepfake Detection](https://arxiv.org/abs/2409.09272)**

### 数据依据：新兴关键词
- **agents** — 近期 8 篇 / 基线 0 篇，增长 ×7.7
- **proofs** — 近期 7 篇 / 基线 0 篇，增长 ×6.7
- **permission** — 近期 6 篇 / 基线 0 篇，增长 ×5.8
- **llm-based** — 近期 6 篇 / 基线 0 篇，增长 ×5.8
- **local differential** — 近期 6 篇 / 基线 0 篇，增长 ×5.8
- **uncovering** — 近期 5 篇 / 基线 0 篇，增长 ×4.8
- **conversational** — 近期 5 篇 / 基线 0 篇，增长 ×4.8
- **scams** — 近期 5 篇 / 基线 0 篇，增长 ×4.8
- **chinese** — 近期 5 篇 / 基线 0 篇，增长 ×4.8
- **llms** — 近期 5 篇 / 基线 0 篇，增长 ×4.8
- **phishing** — 近期 8 篇 / 基线 1 篇，增长 ×3.8
- **usable privacy** — 近期 6 篇 / 基线 1 篇，增长 ×2.9
- **framework** — 近期 21 篇 / 基线 6 篇，增长 ×2.9
- **training** — 近期 9 篇 / 基线 2 篇，增长 ×2.9
- **graph neural** — 近期 6 篇 / 基线 1 篇，增长 ×2.9

### 数据依据：近期高频词
privacy(189)　security(75)　data(63)　private(35)　privacy-preserving(30)　learning(29)　secure(26)　attacks(23)　security privacy(21)　models(21)　framework(21)　perceptions(19)　inference(18)　federated(18)　fingerprinting(17)

## 整体 · 安全四大会全部（USENIX / S&P / CCS / NDSS）
_样本 5531 篇（基线 2876 篇 2020-2023 / 近期 2655 篇 2024-2026）_

### 趋势解读
- **大模型安全成为增长最集中的方向**：LLM、LLMs、LLM-based、agentic 和 agents 的增速显著高于其他主题，说明安全四大会正在快速形成围绕模型、智能体及其应用栈的研究集群。
- **攻击面从模型扩展到 RAG 与智能体链路**：retrieval-augmented generation、prompt injection 相关高被引论文和 agentic 共同表明，研究重点不再局限于模型本体，而是覆盖外部知识、工具调用和多步交互。
- **自动化检测与攻防仍占据主体**：attacks、detection、fuzzing、vulnerabilities 和 learning 是近期高频词，显示安全整体仍以攻击发现、漏洞检测和自动化防御为核心；这与可用安全子领域的人本取向形成明显差异。

### 引用增速最快的代表论文（Top 5）
- **[Extracting Training Data from Diffusion Models](https://arxiv.org/abs/2301.13188)**（2023，年均 257.2，共 1029）——论文证明图像扩散模型会记忆并在生成时泄露训练图片，并通过“生成—过滤”流程从先进模型中提取出一千余个训练样本，包括个人照片和企业商标。对多种训练设置的分析表明，扩散模型的隐私风险高于以往的 GAN，可能需要新的隐私保护训练方法。
- **["Do Anything Now": Characterizing and Evaluating In-The-Wild Jailbreak Prompts on Large Language Models](https://arxiv.org/abs/2308.03825)**（2023，年均 179.8，共 719）——研究使用 JailbreakHub 分析了 2022 年 12 月至 2023 年 12 月间的 1,405 条真实越狱提示，识别出 131 个越狱社区及提示注入、权限提升等主要策略。基于 13 类禁用场景的 107,250 个测试样本，作者发现六种主流 LLM 的防护均不充分，部分提示在 ChatGPT 与 GPT-4 上的攻击成功率达到 0.95。
- **[Great, Now Write an Article About That: The Crescendo Multi-Turn LLM Jailbreak Attack](https://arxiv.org/abs/2404.01833)**（2024，年均 140.7，共 422）——Crescendo 是一种从看似无害的问题开始、再利用模型前序回答逐轮升级的多轮越狱攻击，并可由 Crescendomation 工具自动执行。它在多种商用和开源模型及多模态模型上均表现出较高成功率，在 AdvBench 子集上明显超过当时的先进越狱方法。
- **[StruQ: Defending Against Prompt Injection with Structured Queries](https://arxiv.org/abs/2402.06363)**（2024，年均 132.7，共 398）——StruQ 通过结构化查询把应用指令与用户数据分成两个通道，并训练模型只服从指令通道中的内容，从源头处理提示注入所利用的“指令与数据混淆”。系统由安全前端和专门微调的模型组成，实验显示它能显著提高提示注入抵抗力，同时几乎不损害正常任务效用。
- **[Formalizing and Benchmarking Prompt Injection Attacks and Defenses](https://arxiv.org/abs/2310.12815)**（2023，年均 116.8，共 467）——暂无人工核对的中文简介；请查看原始摘要。

### 其余高增速论文（6–15）
- 2024 | 年均 114.7 — **[Large Language Model guided Protocol Fuzzing](https://www.semanticscholar.org/paper/4fcd49afa8d0a960c6d07aa4e7a37956f5307a8a)**
- 2023 | 年均 106.8 — **[Analyzing Leakage of Personally Identifiable Information in Language Models](https://arxiv.org/abs/2302.00539)**
- 2022 | 年均 106.0 — **[FLAME: Taming Backdoors in Federated Learning](https://www.semanticscholar.org/paper/4089197a8fef8935bab8b879adc08dc5fdf53c6d)**
- 2024 | 年均 100.3 — **[PentestGPT: Evaluating and Harnessing Large Language Models for Automated Penetration Testing](https://www.semanticscholar.org/paper/27d0561813c6134d62a48cdc42e1aede23e76f98)**
- 2024 | 年均 100.0 — **[PoisonedRAG: Knowledge Corruption Attacks to Retrieval-Augmented Generation of Large Language Models](https://arxiv.org/abs/2402.07867)**
- 2023 | 年均 96.5 — **[Poisoning Web-Scale Training Datasets is Practical](https://arxiv.org/abs/2302.10149)**
- 2022 | 年均 86.4 — **[Do Users Write More Insecure Code with AI Assistants?](https://arxiv.org/abs/2211.03622)**
- 2025 | 年均 80.0 — **[Prompt Injection Attack to Tool Selection in LLM Agents](https://arxiv.org/abs/2504.19793)**
- 2023 | 年均 79.8 — **[Large Language Models for Code: Security Hardening and Adversarial Testing](https://arxiv.org/abs/2302.05319)**
- 2025 | 年均 77.5 — **[DataSentinel: A Game-Theoretic Detection of Prompt Injection Attacks](https://arxiv.org/abs/2504.11358)**

### 数据依据：新兴关键词
- **llm** — 近期 40 篇 / 基线 0 篇，增长 ×43.3
- **llm-based** — 近期 12 篇 / 基线 0 篇，增长 ×13.0
- **llms** — 近期 35 篇 / 基线 2 篇，增长 ×12.6
- **retrieval-augmented** — 近期 11 篇 / 基线 0 篇，增长 ×11.9
- **co2** — 近期 11 篇 / 基线 0 篇，增长 ×11.9
- **scam** — 近期 8 篇 / 基线 0 篇，增长 ×8.7
- **addressing** — 近期 8 篇 / 基线 0 篇，增长 ×8.7
- **retrieval-augmented generation** — 近期 8 篇 / 基线 0 篇，增长 ×8.7
- **basalt** — 近期 8 篇 / 基线 0 篇，增长 ×8.7
- **agents** — 近期 14 篇 / 基线 1 篇，增长 ×7.6
- **explainable** — 近期 7 篇 / 基线 0 篇，增长 ×7.6
- **multi-party private** — 近期 7 篇 / 基线 0 篇，增长 ×7.6
- **chinese** — 近期 7 篇 / 基线 0 篇，增长 ×7.6
- **agentic** — 近期 7 篇 / 基线 0 篇，增长 ×7.6
- **deccan** — 近期 7 篇 / 基线 0 篇，增长 ×7.6

### 数据依据：近期高频词
attacks(270)　security(256)　privacy(193)　detection(153)　data(134)　learning(128)　attack(126)　models(124)　efficient(110)　fuzzing(107)　secure(99)　vulnerabilities(90)　poster(89)　language(87)　large(80)
