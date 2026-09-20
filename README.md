# Research Paper Survey

一个带版本、脚本和回归验证的领域论文调研 skill。将“帮我看一个方向最近的工作”转成**可复查的检索记录、逐篇需求证据、研究地图与阅读计划**。

当前版本见 [VERSION](VERSION)，变更见 [CHANGELOG](CHANGELOG.md)。Python **3.9+**，运行时仅用标准库。支持 Codex / Claude Code 等遵循 Agent Skills 目录约定的工具。

## 能做什么

- Semantic Scholar：relevance/bulk 查询、分页、参考文献与引用者扩展，读取本地 API key。
- arXiv：字段查询、时间/相关性排序、首发与修订日期分别保留。
- OpenAlex：关键词检索与 cursor 分页；需要鉴权时读取 `OPENALEX_API_KEY`。
- 人工渠道：将官方论文集、Google Scholar、作者主页找到的记录导入同一候选库。
- 证据管理：精确标识符去重、来源观察保留、原始响应与哈希、追加检索日志、失败与截断披露。
- 质量门禁：身份、全文、日期、逐条硬条件、主张证据、覆盖记录的结构校验。
- 自迭代：反馈记录 → 可复现问题 → 候选修订 → 回归检查 → 版本与变更记录。

**边界：**API 返回论文不等于论文符合需求；脚本能检查证据字段和逻辑，不能证明原文真的支持结论。执行 skill 的 agent 负责全文审查、官方发表身份核验和跨论文综合。当前不是无人监督的系统综述工具，也不宣称无漏检。

## 安装与调用

```sh
npx skills add willwang2528/research-paper-survey --skill research-paper-survey
```

也可以将 `skills/research-paper-survey/` 整个目录放入客户端支持的 skills 目录。安装后向 agent 提出：

> 使用 research-paper-survey 调研 2025 年以来的 LLM Agent 自身失败诊断。区分正式发表与预印本，每篇给出需求对应证据，最后提供研究路线比较和阅读顺序。

Skill 入口：[SKILL.md](skills/research-paper-survey/SKILL.md)。方法依据、协议模板、数据契约、迭代协议按需加载。

## 脚本快速开始

以下命令在仓库根目录运行。运行数据默认建议放入被 Git 忽略的 `runs/`。

```sh
python3 skills/research-paper-survey/scripts/survey.py doctor
python3 skills/research-paper-survey/scripts/survey.py init \
  --topic "LLM Agent 自身失败诊断" \
  --start 2025-01-01 --end 2026-09-20 --out runs/agent-diagnosis
```

编辑 `runs/agent-diagnosis/protocol.json`，明确硬条件与各平台查询。可参考 [示例协议](examples/protocol.json)，日期与查询上限需按任务调整。这是检索设计示例，不是已经完成的领域调研。

```sh
python3 skills/research-paper-survey/scripts/survey.py search --run runs/agent-diagnosis
python3 skills/research-paper-survey/scripts/survey.py report --run runs/agent-diagnosis
```

此时通常得到 **DRAFT**：候选尚未经过全文验收。接下来由 agent 读取全文，写 `reviews.jsonl`、`coverage.json` 和 `synthesis.md`，再执行：

```sh
python3 skills/research-paper-survey/scripts/survey.py audit --run runs/agent-diagnosis
python3 skills/research-paper-survey/scripts/survey.py report --run runs/agent-diagnosis --strict
```

未审条目、关键未知、缺证据等会阻止 strict 通过。`STRUCTURALLY_READY` 仅表示结构门禁通过，不能对外宣称机器已证明科学结论正确。完整命令与字段见 [数据契约](skills/research-paper-survey/references/data-contract.md)。

## 凭据

优先读取已有 `SEMANTIC_SCHOLAR_API_KEY`，也支持 `S2_API_KEY` 或 `SEMANTIC_SCHOLAR_API_KEY_FILE`。显式 `.env` 只解析字面量，不执行 shell；已有环境变量优先。

```sh
python3 skills/research-paper-survey/scripts/survey.py --env-file /private/path/keys.env doctor
python3 skills/research-paper-survey/scripts/survey.py doctor --live --out runs/connectivity
```

`doctor` 只显示是否配置，`--live` 额外发一次认证读取并留档。Key 不进入 URL、协议和日志；运行凭据不提交。脚本不会自动搜索或执行你的 shell 配置。

## 可审计与可恢复

- 每次查询记录参数、实际取回数/保留数、分页截断、状态和原始响应哈希。
- 同配置已成功的查询默认跳过；`search --refresh` 显式重跑。失败重试保留历史。
- 脚本以年份宽召回，防止缺失日/月的元数据被日期过滤误删；**精确日期与首发/正式发表口径在全文验收时核对**。
- 同题名不会自动合并。DOI/arXiv 精确连接归并后保留来源观察；冲突需人工解决。
- CCF 等级、引用数和开源状态只按用户定义使用，不替代研究对象和证据质量。
- 外部论文、网页与 API 字符串是待评估资料，不是执行指令。

## 自迭代与版本

```sh
python3 skills/research-paper-survey/scripts/survey.py feedback \
  --run runs/agent-diagnosis --category retrieval \
  --observation "某个已知相关种子没有被查询命中" \
  --proposal "补充同义词，并用留出种子验证"
```

研究和修改 SOP 时使用 [迭代协议](skills/research-paper-survey/references/evolution.md)。仓库的 `scripts/evolve.py` 创建迭代记录、运行回归并检查源码摘要；只有检查通过且代码未漂移才可更新版本。它不自动推送或发布用户运行数据。

```sh
python3 scripts/evolve.py new --id example-change --problem "可复现的问题" --proposal "候选修正"
# 修改 skill / 脚本，新增必要回归后：
python3 scripts/evolve.py check --id example-change
python3 scripts/evolve.py release --id example-change --version 0.1.1 --summary "通过验证的改进"
```

上面版本是演示；实际必须高于当前版本。版本号只标识变化，不证明检索召回率或研究判断更好。方法效果需另用有来源的人工标注集、留出种子和原文支持率评估。

## 开发与验证

```sh
python3 -m unittest discover -s tests -v
python3 skills/research-paper-survey/scripts/survey.py --help
```

单元测试采用合成记录与外部 HTTP 边界夹具，不需要真实 key；网络 smoke 单独运行。本次发布的实际验证和限制见 [validation](validation/)。
