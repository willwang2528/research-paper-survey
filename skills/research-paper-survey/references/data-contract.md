# 运行数据契约

契约版本：`schema_version: 1`。下面展示核心字段，脚本生成的模板和当前实现为可执行入口；新增字段应保持兼容并补测试。JSONL 每行是独立 JSON 对象，不能包含注释、Markdown fence 或真实凭据。

## 文件职责

| 文件 | 生成/维护者 | 含义 |
|---|---|---|
| protocol.json | init 后由 agent 完善 | 需求、日期口径、R 条件、查询与覆盖计划 |
| run.json | 脚本 | 运行及版本元信息 |
| search_log.jsonl | 脚本追加 | 实际检索与导入日志、失败/限制 |
| raw/ | 脚本 | 原始响应，供归并及来源回查 |
| papers.jsonl | 脚本/规范化导入 | 工作级候选，不代表已通过筛选 |
| reviews.jsonl | agent/研究者 | 全文与逐条件证据、决定 |
| coverage.json | agent/研究者 | 覆盖检查及缺口 |
| audit.json | 脚本 | 结构门禁结果，不是语义事实证明 |
| report.md | 脚本 | 可追溯清单和检查状态 |
| synthesis.md | agent/研究者 | 有引证的领域地图与学习路线 |
| feedback.jsonl | feedback 命令追加 | 有待评估的 SOP 改进线索 |

不要手工删除错误日志来使 strict 通过。修复后重试并保留历史；若当前审计无法判定错误已解决，记录情况并修复审计逻辑，经测试后再升级。

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

阅读预算、排除标准、种子、词表、停止条件、协议修订理由可放配套 `protocol-notes.md`，不假装这些文字已被机器执行。

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

未知日期保留未知，不用年份虚构 1 月 1 日；上面的日期仅演示格式。venue 字符串不能证明 track、接收状态或 CCF 等级，须在 review 中补官方证据。`import --input records.json --source LABEL` 用于规范化人工检索条目；以数组形式提供记录，每项至少有题名、来源 URL 和可获得的标识符，原始来源由脚本记录。不要把私有访问 token 留在 URL。

`provenance` 记录发现路径，`observations` 保留来源观察值；不要把 API 的互相冲突信息擅自写成已核验事实。修改脚本归并规则前使用冲突、缺 ID 和不同版本夹具回归。

## reviews.jsonl

每篇一条当前验收记录，`work_id` 必须对应候选。下面是**待核验模板**，不能以这些占位内容通过审计：

```json
{
  "work_id": "与 papers.jsonl 一致",
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
- `requirements` 是以协议条件 ID 为键的对象；`verdict`：`yes`、`no`、`unclear`。
- 原文证据优先转述，保留 `source_url` 和可定位的页/节/图表 `locator`；不以只有链接或模型解释代替证据。
- `claims` 条目包含 `text`、`source_url`、`locator`、`evidence`。条件与指标口径写进 text/evidence；跨论文推断须在综合文中明确标注。
- `fulltext.version` 是实际读到的版本，如 arXiv v2 或正式会议版；版本不同不能拼接支持而不说明。
- `date_evidence.basis` 应与协议一致；日期须处于窗口内才可核心纳入，索引入库日不能充数。

core 需要真实身份核对、真实全文阅读、日期证据、全部硬条件 yes、至少一条有据主张。结构审计能检查字段和状态，不能检测伪造证据，也不能证明原文真的蕴含该结论；agent 必须逐篇回原文。

## coverage.json

```json
{
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

状态为 `pending`、`done`、`not_applicable`、`blocked`。done 需证据；not_applicable 需理由；blocked 应说明限制及恢复方式。引用真实 query ID、日志和官方目录检查记录。未命中种子的数量可报告，但不推导未知总体召回率。

## report 与 strict

普通 report 允许显示未完成/待核验草稿。strict 阻止未评审、pending、覆盖不完整、检索失败和无效核心验收等问题。`run-ready` 只表示记录结构完备，即使 strict 通过，也要人工核对科学主张、所有核心证据、真实访问范围和综合结论。report 可链接已有 synthesis.md，但不生成或覆写 agent 的研究综合。

运行完成后检查 `run.json` 与仓库 VERSION，保证实际工具版本可追溯。公共仓库默认只发布代码、模板和无隐私测试数据；实际 run 是否发布由用户任务授权决定。
