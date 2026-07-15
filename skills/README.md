# RKF v1 Skill Routers

RKF skills route natural-language intent into one frozen product surface. They
do not define additional product modes.

| Skill | v1 route | Purpose |
|---|---|---|
| `rkf-auto-connect` | Connect & Activate plus all five workflows | Resolve the central checkout, enforce task-scoped activation, and dispatch a governed request. |
| `rkf-connect` | Connect & Activate | Preview/apply a project connection, validate it, activate for one task, report status, or deactivate. |
| `rkf-evidence-vault` | Add and Read | Capture a candidate without promotion, then record exact-locator Evidence with explicit verification state. |
| `rkf-wiki-core` | Ask | Retrieve governed RKF context with exact-first, evidence-aware answers. |
| `rkf-knowledge-synthesis` | Compare & Synthesize | Compare Evidence, preserve agreement and contradiction, and create a Claim or Synthesis with visible gaps. |
| `rkf-lint` | Review | Report missing locators, pending verification, disputed Claims, safety findings, and next actions. |

Common trigger phrases:

- Connect & Activate: 啟動 RKF、連結 RKF、確認 connection、查看 RKF 狀態、停用 RKF。
- Add: Add DOI、收進 RKF、加入 URL 或 PDF pointer、先保持 candidate。
- Ask: 問 RKF、根據 governed context 回答、沒有 locator 就回報證據不足。
- Read: 記錄 Evidence、加入 page/section/figure/table/paragraph locator、標記 verification。
- Compare & Synthesize: 比較 claims、整理 agreement/contradiction/gap、建立 provisional conclusion。
- Review: 下一篇讀什麼、缺哪些 locator、哪些 Evidence 待確認、檢查 public safety。

Candidate-source helpers, derived projections, compatibility code, and release
tools are internal implementation details. They never create a sixth research
workflow, bypass explicit activation, or upgrade evidence trust by themselves.

Use `MODE_REGISTRY.md` for the frozen workflow registry and `AGENTS.md` for the
evidence, lineage, and public-safety contract.
