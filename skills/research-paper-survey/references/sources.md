# 方法和实现的来源

整理日期：2026-09-20。此清单承接本 SOP 的来源研究，提供可核查入口；不表示每次运行都重新访问了所有来源。API、认证、限额和 CCF 目录会变化，实际执行遇到不确定时查当前官方文档并记录访问日期。

## 方法依据

| 来源 | 支持的环节 | 不应推导的结论 |
|---|---|---|
| [PRISMA-S](https://pmc.ncbi.nlm.nih.gov/articles/PMC8270366/) | 透明报告数据库、检索式、日期、限制和检索过程 | 填完清单不证明检索完整或质量达标 |
| [PRISMA 2020 扩展清单](https://www.prisma-statement.org/s/PRISMA_2020_expanded_checklist-yc78.pdf) | 文献选择、排除原因与研究报告透明性 | 学习型 survey 不因此自动成为正式系统综述 |
| [Wohlin 2014：Snowballing Guidelines](https://www.wohlin.eu/ease14.pdf) | 前向/后向引用扩展与迭代检索 | 单个引用圈不代表整个领域 |
| [Keshav：How to Read a Paper](https://systems.cs.columbia.edu/ds2-class/papers/keshav-paper.pdf) | 三遍阅读、分配阅读深度 | 读三遍不自动证明掌握或复现 |
| [CCF 目录及官方说明](https://www.ccf.org.cn/Academic_Evaluation/By_category/) | venue 分类与使用边界 | 会议等级不等于单篇质量或相关性 |

逐篇 R 条件验收卡、结构门禁与反馈版本闭环是本项目的工程综合设计，不把它们冒称为这些来源的统一标准。

## 检索平台的官方入口

- [Semantic Scholar Academic Graph API](https://api.semanticscholar.org/api-docs/graph)：paper search、bulk search、references/citations、字段与认证。网页 FAQ 不能替代端点文档。
- [Semantic Scholar FAQ](https://webflow.semanticscholar.org/faq)：网页产品检索能力及边界。
- [OpenAlex API 文档](https://docs.openalex.org/)；[Search](https://help.openalex.org/api/searching/)；[Filtering](https://help.openalex.org/api/filtering/)；[Works attributes](https://help.openalex.org/data/works/attributes/)：结构化查询、日期及字段定义。优先遵循当前 API 文档，旧帮助链接可能迁移。
- [arXiv API Manual](https://info.arxiv.org/help/api/user-manual.html)：查询字段、排序、返回元数据与使用规则；[moderation](https://info.arxiv.org/help/moderation/index.html)：预印本审核边界。
- [Google Scholar Help](https://scholar.google.com/intl/en/scholar/help.html)：检索、引用者、版本及展示范围。当前脚本没有 Scholar 抓取器。
- [PMLR](https://proceedings.mlr.press/) 与 [ACL Anthology](https://aclanthology.org/)：官方论文集例子；根据领域选择相应入口，不硬性要求查这些会议。
- [DBLP 收录说明](https://dblp.dagstuhl.de/faq/5210119.html)：CS 元数据范围；[OpenReview 数据说明](https://docs.openreview.net/how-to-guides/data-retrieval-and-modification/how-to-get-all-notes-for-submissions-reviews-rebuttals-etc)：投稿/评审/决定数据的区别。

## 工具借鉴与边界

- [K-Dense literature-review](https://github.com/K-Dense-AI/scientific-agent-skills/tree/main/skills/literature-review)：参考任务组织及多库工作流。其 DOI 核验不能替代本文的适配和主张核验；本项目不宣称复用了其完整实现或验收标准。
- [DeerFlow systematic-literature-review](https://github.com/bytedance/deer-flow/tree/main/skills/public/systematic-literature-review)：参考候选收集与综合组织。arXiv 单入口和固定篇数不是充分覆盖。
- [CoLRev](https://github.com/CoLRev-Environment/colrev)：长期文献工作流、去重筛选和协作的工程参考；当前 skill 不依赖它。
- [ASReview](https://github.com/asreview/asreview) 与 [官方工作流文章](https://asreview.nl/blog/seven-ways-to-integrate-asreview/)：候选排序与初筛辅助；不替代全文质量评价或合理停止策略。
- [DeepPaperNote](https://github.com/917Dhj/DeepPaperNote)：选定论文后的单篇深读可选下游；不负责证明领域检索覆盖。

这些工具是参考入口，不因出现在这里就自动安装、执行或授权外部操作。研究其代码时应固定 commit，区分 README 主张、静态代码观察、实际 smoke 与方法有效性实验。
