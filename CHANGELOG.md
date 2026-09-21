# Changelog

## 0.2.7 — 2026-09-21

- 论文 URL 并入日期收录行首；未检索到 arXiv 时省略日期及占位文字，保留官方全文入口。仅展示修订，无 schema 迁移。
- 验证记录：[iterations/inline-paper-url](iterations/inline-paper-url/plan.json)。回归通过不代表研究召回率已测量。

## 0.2.6 — 2026-09-21

- 调整论文开头顺序，作者单位独占列表项；中国机构中文、其他机构英文，保留已知署名而非中文名待核实占位符。
- 验证记录：[iterations/affiliation-language-order](iterations/affiliation-language-order/plan.json)。回归通过不代表研究召回率已测量。

## 0.2.5 — 2026-09-21

- 预印本展示仅写预印本，删除未核实正式收录等后缀；核验状态保留在证据记录，筛选逻辑不变。
- 验证记录：[iterations/concise-preprint-label](iterations/concise-preprint-label/plan.json)。回归通过不代表研究召回率已测量。

## 0.2.4 — 2026-09-21

- 精简论文开头：移除重复标签与英文单位对照，中文题名单列，会议后直接接年月，URL无前缀；保留摘要和完整核验记录。
- 验证记录：[iterations/compact-paper-opening](iterations/compact-paper-opening/plan.json)。回归通过不代表研究召回率已测量。

## 0.2.3 — 2026-09-21

- 固定逐篇英文题名、版本与收录元数据、全部署名单位、最新版 arXiv 链接和摘要总结；补充核验及缺失值规则。兼容展示修订，无 schema 迁移，CLI 仍为审计草稿。
- 验证记录：[iterations/paper-opening-metadata](iterations/paper-opening-metadata/plan.json)。回归通过不代表研究召回率已测量。

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
