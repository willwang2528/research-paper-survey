# 运行数据契约

契约版本：`schema_version: 1`。0.2.0 增加指纹字段并收紧验收门禁：文件结构仍为 schema 1，但旧 run 不能原样通过，需 prepare 后重新评审和覆盖核查。下面展示核心字段，脚本生成的模板和当前实现为可执行入口；新增字段应保持兼容并补测试。JSONL 每行是独立 JSON 对象，不能包含注释、Markdown fence 或真实凭据。

## 文件职责

| 文件 | 生成/维护者 | 含义 |
|---|---|---|
| protocol.json | init 后由 agent 完善 | 需求、日期口径、R 条件、查询与覆盖计划 |
| run.json | 脚本 | 运行及版本元信息 |
| search_log.jsonl | 脚本追加 | 实际检索与导入日志、失败/限制 |
| raw/ | 脚本 | 原始响应，供归并及来源回查 |
| papers.jsonl | 脚本/规范化导入 | 工作级候选，不代表已通过筛选 |
| reviews.jsonl | agent/研究者 | 全文与逐条件证据、决定 |
| review_queue.jsonl | prepare 生成 | 未评审或范围过期条目的待填模板；不替代当前评审 |
| coverage.json | agent/研究者 | 覆盖检查及缺口 |
| coverage_template.json | prepare 生成 | 当前协议对应的覆盖模板；不覆写已完成记录 |
| audit.json | 脚本 | 结构门禁结果，不是语义事实证明 |
| report.md | 脚本 | 可追溯清单和检查状态 |
| synthesis.md | agent/研究者 | 有引证的领域地图与学习路线 |
| feedback.jsonl | feedback 命令追加 | 有待评估的 SOP 改进线索 |

不要手工删除错误日志来使 strict 通过。修复后重试并保留历史；审计按查询指纹取最新尝试，同指纹成功重试可替代旧失败状态。每条当前计划查询必须已有匹配指纹的最新成功日志。查询指纹包含查询参数、起止日期与工具版本，升级后可能需要重新检索。

## protocol.json

```json
{
  "schema_version": 1,
  "topic": "LLM Agent 自身失败诊断",
  "objective": "学习近期路线并识别证据边界",
  "start_date": "2025-09-20",
  "end_date": "2026-09-20",
  "date_basis": "first_public",
  "requirements": [
    {"id": "R1", "description": "研究对象是 LLM Agent 自身的执行失败", "hard": true},
    {"id": "R2", "description": "提供可核查的方法及评测证据", "hard": true},
    {"id": "P1", "description": "优先可获取代码的工作", "hard": false}
  ],
  "queries": [
    {"id": "Q1", "provider": "s2", "query": "LLM agent failure diagnosis", "mode": "relevance", "limit": 100},
    {"id": "Q2", "provider": "arxiv", "query": "all:\"language model agent\" AND all:debugging", "limit": 100}
  ],
  "coverage_requirements": ["keyword_search", "citation_search", "venue_scan", "recent_preprints", "seed_check"]
}
```

这是教学示例，不是现成完备检索。provider 可为 `s2`、`arxiv`、`openalex`；S2 mode 是 `relevance` 或 `bulk`，query 的 `sort` 可选，具体值以各 provider 的实现与当前官方参数为准。日期依据为 `first_public` 或 `formal_publication`，实际过滤字段不一定与需求口径完全一致，最终由 date_evidence 验收。

阅读预算、排除标准、种子、词表、停止条件、协议修订理由可放配套 `protocol-notes.md`，不假装这些文字已被机器执行。按任务选择渠道，示例中的查询与覆盖项不是每次必跑清单；执行前按实际计划调整。渠道分工与重要未选来源的理由写入该笔记，会议目录的实际浏览范围写入 `venue-scan.md`（见 templates.md），并在对应覆盖项中引用。新增这些人工记录不改变 schema，也不表示脚本自动浏览过目录。

## papers.jsonl 与 import

工作记录使用以下规范字段：

```json
{
  "work_id": "由脚本分配或保留的稳定标识",
  "ids": {"doi": "", "arxiv": "", "s2": "", "openalex": ""},
  "title": "实际论文题名",
  "authors": ["实际作者"],
  "year": 2026,
  "publication_date": "2026-01-01",
  "first_public_date": "2025-12-01",
  "updated_date": "2026-01-02",
  "abstract": "来自所记录来源的摘要",
  "url": "https://example.org/paper",
  "open_access_pdf": "https://example.org/paper.pdf",
  "venue": "实际 venue",
  "provenance": [],
  "observations": []
}
```

未知日期保留未知，不用年份虚构 1 月 1 日；上面的日期仅演示格式。venue 字符串不能证明 track、接收状态或 CCF 等级，须在 review 中补官方证据。`import --input records.json --source LABEL` 接受 JSON 数组，也接受 `.jsonl` 文件中的逐行对象；每项至少有非空 title 和非空 ids 中的稳定标识符，建议同时附 URL。仅有标题或 URL 不支持导入：先回官方来源解析 DOI/arXiv/S2/OpenAlex ID，再导入。原始来源由脚本记录，不要把私有访问 token 留在 URL。

`provenance` 记录发现路径，`observations` 保留来源观察值；不要把 API 的互相冲突信息擅自写成已核验事实。修改脚本归并规则前使用冲突、缺 ID 和不同版本夹具回归。

## reviews.jsonl

每篇一条当前验收记录，`work_id` 必须对应候选。先运行 `prepare --run <run>`，读取 review_queue.jsonl 和 coverage_template.json 及返回的两个指纹。它不会覆写 reviews.jsonl/coverage.json；队列包含未评审或 scope 过期条目，已存在且 scope 一致的 pending 仍需手工继续处理。下面是**待核验模板**，不能以这些占位内容通过审计：

```json
{
  "work_id": "与 papers.jsonl 一致",
  "scope_fingerprint": "prepare 生成的当前范围指纹，完成真实复核后保留",
  "decision": "pending",
  "reason": "尚未取得并核对全文",
  "reviewer": "核验者标识",
  "reviewed_at": "2026-09-20T00:00:00Z",
  "identity": {"verified": false, "source_url": ""},
  "fulltext": {"reviewed": false, "source_url": "", "version": ""},
  "date_evidence": {"basis": "first_public", "date": "", "source_url": "", "locator": ""},
  "requirements": {
    "R1": {"verdict": "unclear", "source_url": "", "locator": "", "evidence": "", "rationale": "尚未检查"},
    "R2": {"verdict": "unclear", "source_url": "", "locator": "", "evidence": "", "rationale": "尚未检查"}
  },
  "claims": [],
  "limitations": [],
  "reading_priority": "未排序",
  "reading_reason": "待全文核验后确定"
}
```

- `decision`：`core`、`background`、`excluded`、`pending`。
- `scope_fingerprint`：对 protocol 排除 `queries` 与 `coverage_requirements` 后的内容计算的指纹。所有 decision 都检查，包括 excluded/background。更改对象、日期、目标或需求后必须重新核对，不得仅复制新 hash 冒充复核；仅修改查询不会使范围指纹失效。
- `requirements` 是以协议条件 ID 为键的对象；`verdict`：`yes`、`no`、`unclear`。
- 原文证据优先转述，保留 `source_url` 和可定位的页/节/图表 `locator`；不以只有链接或模型解释代替证据。
- 当前 `source_url` 接受 HTTP(S) 的论文官方/可回查入口，不接受 `file://`。离线阅读真实 PDF 时仍填论文规范 URL，可另加 `source_file`（相对运行目录）和 `source_sha256` 记录实际读取文件；这两个扩展字段目前仅留档，不由审计器验证哈希。没有可核对的论文身份入口时保留 pending，不编造 URL。离线合成演练使用 fixture 自带标识时必须明确标为模拟，不能报告成真实论文认证。
- `claims` 条目包含 `text`、`source_url`、`locator`、`evidence`。条件与指标口径写进 text/evidence；跨论文推断须在综合文中明确标注。
- `fulltext.version` 是实际读到的版本，如 arXiv v2 或正式会议版；版本不同不能拼接支持而不说明。
- `date_evidence.basis` 应与协议一致；日期须处于窗口内才可核心纳入，索引入库日不能充数。

core 需要真实身份核对、真实全文阅读、日期证据、全部硬条件 yes、至少一条有据主张。结构审计能检查字段和状态，不能检测伪造证据，也不能证明原文真的蕴含该结论；agent 必须逐篇回原文。

## coverage.json

```json
{
  "protocol_fingerprint": "prepare 生成的完整协议指纹，完成覆盖重核后保留",
  "checks": [
    {"id": "keyword_search", "status": "pending", "evidence": "", "reason": "尚未执行"},
    {"id": "citation_search", "status": "pending", "evidence": "", "reason": "待选种子"},
    {"id": "venue_scan", "status": "pending", "evidence": "", "reason": "待确定会议目录"},
    {"id": "recent_preprints", "status": "pending", "evidence": "", "reason": "待执行近期补查"},
    {"id": "seed_check", "status": "pending", "evidence": "", "reason": "待校准"}
  ],
  "limitations": []
}
```

状态为 `pending`、`done`、`not_applicable`、`blocked`。done 需证据；not_applicable 需理由；blocked 应说明限制及恢复方式。`protocol_fingerprint` 覆盖整个协议，包括 queries 和 coverage_requirements；任意协议内容变化后重查覆盖，不得只替换 hash。引用真实 query ID、日志和官方目录检查记录。未命中种子的数量可报告，但不推导未知总体召回率。

## report 与 strict

普通 report 允许显示未完成/待核验草稿。strict 阻止未评审、pending、指纹不匹配/缺失、覆盖不完整、计划查询尚未成功执行、未恢复检索失败和无效核心验收等问题。`run-ready` 只表示记录结构完备，即使 strict 通过，也要人工核对科学主张、所有核心证据、真实访问范围和综合结论。report 可链接已有 synthesis.md，但不生成或覆写 agent 的研究综合。

运行完成后检查 `run.json` 与仓库 VERSION，保证实际工具版本可追溯。公共仓库默认只发布代码、模板和无隐私测试数据；实际 run 是否发布由用户任务授权决定。
