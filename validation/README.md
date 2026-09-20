# Validation record

Date: 2026-09-20. Target release: v0.2.0.

## What was actually exercised

- Python 3.9.6 locally; standard library runtime. The repository also defines CI for Python 3.9/3.11/3.13; a local run alone does not establish remote CI success.
- 29 deterministic regression cases before release preparation, including the release-check/source-drift gate. The final release check log is stored in `iterations/evidence-gates/tests.txt`.
- The standard skill frontmatter validator passed; command help and bundled local documentation links were checked.
- A real Semantic Scholar authenticated paper read succeeded using a local environment key. No key value is included in this repository.
- Real relevance/bulk, arXiv and OpenAlex queries succeeded. Counts below are smoke-test observations, **not domain coverage or screening-quality measurements**.

| Live path | Retained | Retrieved by API calls | API total reported | Bounded/truncated |
|---|---:|---:|---:|---|
| Semantic Scholar relevance | 3 | 3 | 4,051 | yes |
| Semantic Scholar bulk | 3 | 51 | 51 | yes |
| arXiv | 2 | 2 | 2,434 | yes |
| OpenAlex | 2 | 2 | 15,721 | yes |
| Semantic Scholar references | 2 | 2 | not supplied | yes |

Search queries used are the small integration queries described in the local smoke run; API totals are mutable index estimates. The four search paths yielded 10 independent candidates. Reference expansion added 2. These 12 records remain unreviewed and their report correctly stays DRAFT. `report --strict` returned exit 2 rather than falsely certifying them.

The full local run is excluded from version control: raw responses, ordinary research data and local filesystem locations are not necessary for the public software validation summary. Public regression fixtures are explicitly synthetic.

## First iteration

Baseline implementation commit: `2d38d36` (development version 0.1.0; not an independently validated literature-survey result).

An independent code-review agent reproduced four concrete failures. They were converted into regression cases before the fix:

1. Changed research requirements could reuse old judgments; current planned queries could remain unexecuted.
2. JSON null/non-string evidence could be mistaken for populated evidence.
3. A malformed later page could discard previously retrieved papers.
4. Historical success could suppress retries after a later failed refresh.

The candidate adds scope/protocol fingerprints, current-query checks, strict evidence-string checks, partial-page preservation, and latest-attempt retry decisions. It also generates review/coverage templates without overwriting existing judgments. Malformed arXiv totals and OpenAlex later pages have separate regression coverage.

These changes strengthen operational gates. They do **not** demonstrate better unknown-field recall, causal scientific correctness, or independent human screening agreement.

## Behavioral evaluation

Scenario definitions and synthetic source material live in `evals/`. Actual independent execution is recorded separately in `forward-evaluation.md`. Unexecuted scenarios must not be counted as passed tests.

## Limits and publication boundary

- No complete domain survey, human-labeled retrieval benchmark, full-text entailment benchmark, or reproduction study was run.
- The runtime checks evidence presence and consistency; an agent/researcher must check source authenticity and support.
- Keyword databases and dates can be incomplete; bounded retrieval is explicit.
- Only code, documentation, synthetic fixtures and nonsecret validation summaries are intended for publication.
