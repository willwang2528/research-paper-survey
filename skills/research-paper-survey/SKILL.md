---
name: research-paper-survey
description: 调研一个领域的近期论文、建立研究地图和阅读计划，并逐篇提供需求符合性证据。用于领域 paper survey、recent work、文献检索与筛选、论文阅读路线、检索报告更新，以及研究和迭代该 SOP；不用于仅摘要单篇论文。支持 Semantic Scholar、arXiv、OpenAlex 脚本检索及人工来源导入。
metadata:
  version: "0.2.4"
---

# Research Paper Survey

把研究需求转成有证据的论文清单和学习路线。完整流程是：需求协议 → 术语与种子 → 多路检索 → 去重与版本核对 → 初筛 → 全文逐项验收 → 跨论文综合 → 查漏 → 阅读 → 反馈迭代。

这是面向研究学习的可追溯工作流。脚本负责数据获取、记录、结构校验和草稿；执行 skill 的 agent 负责读原文、判断适配、验证主张并写综合。通过脚本审计不等于获得科学结论正确性证明，也不自动构成正式系统综述。

## 何时读取其他文件

- 开始一次调研：读 [workflow.md](references/workflow.md)，按阶段执行。
- 编辑运行文件或排查审计：读 [data-contract.md](references/data-contract.md)。
- 需要逐篇证据卡与综合模板：读 [templates.md](references/templates.md)。
- 要改进本 skill、升级版本或分析反馈：读 [evolution.md](references/evolution.md)。
- 核对方法依据、API 能力：读 [sources.md](references/sources.md)，再按需访问官方来源。来源记录日期不代表永不过期。

## 1. 确定范围

先从用户已有资料恢复背景，明确研究对象、目标问题、场景、日期窗口、日期口径、允许论文类型、硬条件、偏好、阅读预算和停止条件。只追问影响筛选的关键缺口；可合理假设的记录在协议中并继续。

将硬条件编号 R1…Rn。研究对象不同不能凭术语相似纳入；例如“Agent 自身失败诊断”不等于“Agent 诊断云故障”。CCF A/B 默认是偏好，只有用户明确要求才是硬条件。不要为凑论文数放宽条件。

运行目录放在用户工作区。下文 `<skill_dir>` 是本 SKILL.md 所在目录；`<run>` 是该次调研目录。不要假定当前 shell 已在 skill 目录。

```sh
python3 <skill_dir>/scripts/survey.py doctor
python3 <skill_dir>/scripts/survey.py init --topic "研究问题" --start 2025-09-20 --end 2026-09-20 --out <run>
```

随后编辑 `<run>/protocol.json`，将模板变成真实需求，明确 R 条件和计划查询。日期是示例，必须按当前任务修改。先读生成的文件，再编辑；不得用默认查询充当完成的研究设计。

## 2. 接通数据源

Semantic Scholar key 只从本地环境或凭据文件读取：`SEMANTIC_SCHOLAR_API_KEY`、`S2_API_KEY`、`SEMANTIC_SCHOLAR_API_KEY_FILE`。也支持显式环境文件：

```sh
python3 <skill_dir>/scripts/survey.py --env-file /private/path/keys.env doctor
```

`--env-file` 放在子命令之前。用户说本地已有 key 时，先查已配置变量名、已有配置线索和文件路径；不要回显值，不要全盘扫描凭据，不要把 key 写入协议、查询日志、报告或仓库。需要时只向用户询问凭据位置。

OpenAlex key 为可选配置，按 doctor 输出和当前官方限额判断是否可用；未配置或 API 受限时如实记录。鉴权、网络或限流失败不等于零篇命中。

## 3. 检索与补查

建立对象、问题、场景、方法、评测的术语表，覆盖全称、缩写和同义表达。第一轮主要组合“对象 × 问题”；从命中文献扩词。少量种子应覆盖不同作者群体和路线。

分别配置各平台查询，不能跨平台照搬语法。S2 relevance 与 bulk 是不同模式，网页规则也不等于 API 规则。预设返回上限必须写进覆盖边界。

```sh
python3 <skill_dir>/scripts/survey.py search --run <run>
python3 <skill_dir>/scripts/survey.py snowball --run <run> --paper-id DOI:10.xxxx/example --direction references --limit 100
python3 <skill_dir>/scripts/survey.py snowball --run <run> --paper-id ARXIV:2501.00001 --direction citations --limit 100
python3 <skill_dir>/scripts/survey.py import --run <run> --input records.json --source "Official proceedings"
```

示例标识符是占位符。引用扩展通过 S2，具体 ID 前缀以官方 API 支持为准。`import` 输入格式见数据契约。Google Scholar、官方论文集、作者主页及浏览器检索发现的论文，可整理后导入；不要把当前脚本没有执行的渠道写成已自动检索。

按任务选渠道，不要求每次全部搜索。根据调研用途、领域、时间窗口和预算，选择能互补的发现、补查与核验来源，在 `protocol-notes.md` 记录分工及重要未选来源的理由；`queries` 只保留本次计划执行的脚本查询，`coverage_requirements` 按实际覆盖计划设置。模板不是必跑清单，也不能在运行失败后删掉计划项来掩盖缺口。任务与来源的对应建议见 workflow.md 阶段 2。

需要近期会议补查时，浏览目标会议最近几届的目录（例如最近 2–3 届，具体随时间窗口调整），按 session/track 查看标题，对任务可能相关或标题含义不明确的论文继续读摘要，补查标题没有使用预设关键词的工作；不要只在目录内再次搜索同一关键词。记录具体会议、年份、track、目录 URL、实际浏览范围和新增候选，部分浏览须披露缺口；发现的论文仍走同一全文验收流程。细节与记录模板见 workflow.md 阶段 3 和 templates.md。

已知种子、替代术语与不同引用圈等按本次覆盖计划检查，某项不适用时说明原因。新增工作趋少只是停止依据之一，不能证明穷尽。检索日志保存实际式子、参数、时间、范围与失败，不事后改写查询历史。

## 4. 去重、筛选、逐篇验收

先核对 DOI/arXiv 等标识符，保留所有来源。标题相似只生成查重线索。自动归并后仍需核对预印本、会议版、期刊扩展版差异。

检索/导入后，或需求协议变化后，先生成当前验收模板：

```sh
python3 <skill_dir>/scripts/survey.py prepare --run <run>
```

命令生成 `review_queue.jsonl` 和 `coverage_template.json`，返回当前 scope/protocol 两个 fingerprint，不覆写 `reviews.jsonl` 或 `coverage.json`。队列列出未评审或范围指纹过期的条目；同一范围内已有 pending 仍需继续处理，队列为空不代表审查结束。

摘要初筛只排除明确不符合者。以队列模板读核心候选全文，再将验收结果合并进 `reviews.jsonl`，每个 work 保留一条当前记录：身份来源、所读版本、日期依据、每个硬条件的 `yes/no/unclear` 与证据、主要主张与限制、决定理由、核验者和日期。

所有决定（含 background/excluded/pending）必须携带当前 `scope_fingerprint`；范围不含 queries/coverage_requirements。需求变化后重核所有受影响决定，不能只改 hash 求通过。覆盖验收携带整个协议的 `protocol_fingerprint`；修改查询或覆盖计划也会使旧覆盖记录过期。旧 run 缺少这些字段时先 prepare，再真实复核后迁移。

只有以下都满足，才能写 `decision: core`：

1. 身份已核实，全文已阅读，版本可定位。
2. 日期按协议口径在窗口内，有来源依据。
3. 每项硬条件都是 `yes`，有原文位置、证据和理由。
4. 至少一个主要主张有可回查的原文支持；所有写入报告的重要主张均须核对。

拿不到全文或存在关键未知，放 `pending`；方法借鉴放 `background`；明确不符放 `excluded` 并记录条件和原因。偏好和高引用不能抵消硬条件不满足。

元数据存在、需求符合和主张成立分三层检查。API 摘要与模型自信不能代替全文证据。数字保留指标分母、规模对象、实验条件。理论、系统、benchmark 使用适合其研究类型的质量检查。

## 5. 综合与交付

依据 `coverage_template.json` 更新 `coverage.json`，记录每项检查的证据、缺口与停止原因，并在实际重核后采用当前协议指纹。然后运行：

```sh
python3 <skill_dir>/scripts/survey.py audit --run <run>
python3 <skill_dir>/scripts/survey.py report --run <run>
python3 <skill_dir>/scripts/survey.py report --run <run> --strict
```

普通报告允许诚实草稿；strict 是发布前结构门禁，要求消除未审条目、pending、指纹过期、未完成覆盖和检索失败等阻塞，并要求当前每条计划查询有匹配参数的最新成功日志。同一查询指纹重试成功可覆盖先前失败状态，但保留历史。不要为通过门禁把未知改成 yes，或删掉失败记录。

脚本报告之后，agent 必须补充 `synthesis.md`：按“子问题 × 方法路线 × 假设 × 证据 × 局限”比较，给出阅读顺序、关键对照和未决问题；所有主张连接逐篇证据。再人工抽查链接和全部核心结论。不要声称脚本自动完成了这些工作。

面向读者的每篇介绍必须先展示：英文完整题名首行标题 → 精简元数据行（日期 ｜ venue/track 与适用 CCF 等级，空格接收录年月 ｜ 作者单位：去重中文名称）→ 独立无序列表项的中文题名 → 无前缀的最新版 arXiv URL → 摘要总结，再展开分析。填写及未知值规则见 [逐篇介绍模板](references/templates.md#面向读者的逐篇介绍固定开头)。这些字段由 agent 查源核验，脚本草稿不会自动补齐。

最终交付包含范围、领域地图、阅读路线、逐篇证据、检索日志、排除与待核验清单、覆盖限制。明确检索记录数、独立候选数、全文审查数和四类决定数，说明哪些计数是人工补充。查询可重跑，不保证动态数据库返回相同结果。

学习用三遍法：初读判断价值、再读理解机制、只对核心论文重建推理。笔记生成、本人能解释、代码运行和结果复现分别记录。

## 6. 每次运行反馈，按版本改进

```sh
python3 <skill_dir>/scripts/survey.py feedback --run <run> --category "retrieval" --observation "已知种子未命中，现有查询遗漏了一个术语" --proposal "增加同义词查询，并用独立种子集验证"
```

自迭代是有证据的维护闭环：运行反馈 → 复现问题 → candidate 分支 → 修改 → 回归与方法评估 → 版本和 CHANGELOG → 发布。脚本不会自动改写、安装或发布自身。发现一次漏检不代表可以宣称整体召回率提高；在用来调参的种子上改善，要用独立集合检查。

仓库维护者使用 `<repo>/scripts/evolve.py new/check/release` 记录提案、执行回归和更新本地版本；它不会 commit/tag/push。具体参数见 [evolution.md](references/evolution.md)。修改 SOP 时同时检查脚本契约、模板、文档和测试一致性。版本变化必须能映射到 commit 和运行记录，旧报告保留当时版本和证据，不静默覆盖。
