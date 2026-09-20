# Changelog

## 0.2.2 — 2026-09-20

- 明确按任务选渠道，无须每次全搜；细化目标会议近几届目录浏览、关键词之外候选发现及覆盖记录。兼容文档修订，无新增 API 或自动浏览能力，旧运行无需数据迁移。
- 验证记录：[iterations/task-sources-venue-browse](iterations/task-sources-venue-browse/plan.json)。回归通过不代表研究召回率已测量。

## 0.2.1 — 2026-09-20

- 将需额外GitHub授权的Actions配置保留为未启用示例，本地回归与运行能力不变
- 验证记录：[iterations/ci-portability](iterations/ci-portability/plan.json)。回归通过不代表研究召回率已测量。

## 0.2.0 — 2026-09-20

- 绑定需求与覆盖指纹，修复证据类型检查、异常分页保留及最新失败重试；补齐独立使用验证和迁移说明
- 验证记录：[iterations/evidence-gates](iterations/evidence-gates/plan.json)。回归通过不代表研究召回率已测量。

按 SemVer 记录可追溯改动；版本提升不等于研究质量已改善。

## 0.1.0 — 2026-09-20

- 初始 SOP skill：需求协议、多路检索、全文逐项验收、覆盖检查、研究综合与阅读计划。
- 标准库 CLI：Semantic Scholar、arXiv、OpenAlex 检索；引用扩展；人工导入；证据结构审计与报告。
- 运行版本、原始响应、查询日志、失败/截断及反馈记录。
- 合成回归覆盖凭据保护、分页、标识符归并和核心纳入门禁。

限制：不自动验证原文蕴含关系，不宣称全领域召回率；网络访问和索引覆盖依赖上游。
