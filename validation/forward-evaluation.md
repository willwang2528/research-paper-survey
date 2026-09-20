# Independent skill-consumer exercise

Executed 2026-09-20 using the candidate skill instructions and CLI. The agent was given the `scope-and-evidence` request and the two synthetic input files in `evals/fixtures/`. It was not given the intended per-paper decisions. No network access or real credential use was part of this exercise.

| Candidate | Observed decision | Evidence-bounded behavior |
|---|---|---|
| Synthetic A | core, explicitly simulation-only | Identified the agent's own failure task; kept 24/40 top-three suspect-step result distinct from causal accuracy |
| Synthetic B | excluded | Cloud service failures did not match the requested agent-self-diagnosis scope; conference preference did not override the hard criterion |
| Synthetic C | pending | Missing full text, exact first-public date and version were not invented |

The agent produced a protocol, imported candidates, reviews, coverage record, synthesis, ordinary report and command exit records. Observed final exits: `audit=1`, `report=0`, `report --strict=2`. Remaining blockers were the pending candidate, incomplete coverage checks and unexecuted planned queries. No search success was fabricated.

## Friction and iteration

The first attempt used `file://` source URLs for the locally read fixture packet. The current validator accepts HTTP(S) source URLs, so these were rejected. The agent used the fictional HTTPS identifiers explicitly supplied by the fixture and separately disclosed the actual local source and absence of network verification. This was a citation-format adjustment in a synthetic exercise, not proof that any real paper exists.

The data-contract documentation now explains this constraint: use the canonical scholarly URL with optional local source file/hash provenance; lacking a verifiable identity remains pending. Automatic checking of local source hashes is not currently implemented.

## What this establishes

This one independent exercise shows that the skill can guide a consumer through the intended decisions and preserve an honest draft when evidence/coverage is incomplete. It is not a statistical benchmark, an independent human screening study, or a recall/precision measurement. The other scenarios in `evals/scenarios.json` were defined for future evaluation; they were not run as additional agent exercises in this release.
