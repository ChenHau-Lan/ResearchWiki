# RKF Mode Registry

Modes are grouped under five active RKF skills. The ARS bridge is an implicit
protocol, not an active skill. The Codex app is the user-facing interaction
surface; legacy tool commands are an implementation detail for agents, tests,
and maintenance only.

## `rkf-evidence-vault`

| Mode | English / 中文 Trigger | Output | Oversight | Write Boundary |
|---|---|---|---|---|
| `inbox-capture` | ChatGPT conversation, web clip, URL/DOI lead, cross-project note; 存到 inbox, 網頁剪藏, 對話保存 | inbox item plus optional SourceRecord/paper backlink | Medium | `knowledge/inbox/`, optional `state/sources/` and paper backlink |
| `capture` | DOI, URL, PDF pointer, topic seed, idea, question; 來源攝取, 加入 DOI/URL/PDF | `SourceRecord` with conservative reading fields | Medium | `state/sources/` |
| `discover` | literature discovery, topic/hot-query search, paper-radar metadata, candidates; 文獻搜尋, 找 SCI paper, 自動找 paper | exact-hash candidate preview/run and selected capture receipts | Medium | `discover.preview`; designated-writer `discover.record` / `discover.accept`; `state/search_runs/` |
| `acquire` | user-provided PDF/full text, legal route note, legacy checkpoint; 取得PDF, 使用者提供PDF, 全文狀態 | full-text status update, artifact pointer, or legacy route note | High | `state/sources/`, `state/evidence/`, optional `state/gates/` |
| `verify-pdf` | PDF/OCR/visual check, identity/readability check, locator capture; PDF檢查, OCR檢查, 定位頁碼 | checked reading artifact and maturity upgrade | High | `state/evidence/` |

## `rkf-knowledge-synthesis`

| Mode | English / 中文 Trigger | Output | Oversight | Write Boundary |
|---|---|---|---|---|
| `distill-paper` | create/update paper reading draft; 論文整理成 paper draft, 論文筆記 | paper page with reading maturity | Medium | `knowledge/papers/` |
| `save-question` | open question, uncertainty, search plan; 問題頁, 研究問題, 待查問題 | question page | Medium | `knowledge/questions/` |
| `save-concept` | recurring method, mechanism, dataset, variable; 概念頁, 方法, 儀器, 變數 | concept page | Medium | `knowledge/concepts/` |
| `save-claim` | locator-backed or reviewable claim; claim, 主張, 證據句 | claim page/review item | High | `knowledge/claims/` |
| `synthesize` | cross-source judgment, reusable recommendation, repeated human-reviewed answer; 綜整, synthesis, 研究建議 | synthesis page with maturity fields | High | `knowledge/synthesis/` |
| `emerge` | unnamed patterns, nightly synthesis, pattern discovery; emerge, pattern discovery | low-maturity synthesis draft | Medium | `knowledge/synthesis/` only with explicit write approval |
| `topic-governance` | topic ID, aliases, scope, default search; 主題治理, topic registry | topic registry/page | Medium | `governance/`, `knowledge/topics/` |
| `topic-review` | regular topic review, merge/split suggestion, stale candidate cleanup, search refresh; 定期查看topic, topic整理, topic建議 | topic review report and update proposal | Medium | `governance/`, review queue |

## `rkf-wiki-core`

| Mode | English / 中文 Trigger | Output | Oversight | Write Boundary |
|---|---|---|---|---|
| `query` | ask what the wiki knows; 問知識庫, 從wiki回答 | governed context + optional ARS analysis | Medium | hot-query event unless disabled; no knowledge write unless saved |
| `hot-query` | recurring research question, paper-search demand; 熱門問題, 常問題目, hot.md | retrieval dashboard | Low | `hot.md` |
| `paper-status` | show registered paper maturity; paper狀態, 閱讀成熟度 | maturity/status report | Low | Codex app report |
| `paper-feedback` | record user question, correction, annotation, trust change; 記錄feedback, 人工註解 | ledger event and maturity update | Medium | `state/reading/`, paper frontmatter |
| `paper-queue` | papers needing PDF, feedback, repeated-question review, synthesis review; paper queue, paper推播 | prioritized queue | Low | Codex app report |
| `paper-nudge` | scheduled registered-paper reminder; daily paper nudge, 每日推播 | public-safe nudge text | Low | Codex app report or automation digest |
| `world` | L0-L3 workspace bootstrap, current state; status, world, 接續thread | critical facts, active reading, readiness, graph links | Low | Codex app report |
| `save` | persist durable non-paper knowledge; 回寫wiki, 保存討論結果 | selected knowledge object; explicit update required for overwrite | Medium | `knowledge/` |
| `evolve` | low-risk direct page integration; rewrite existing page, AI Integration Note, 自動演化 | AI-marked page rewrite or high-risk blocker | Medium/High by priority | target knowledge page |
| `challenge` | use RKF knowledge to argue against a target; 反駁自己, challenge synthesis | counterpoints and downgrade suggestions | Medium | Codex app report only |
| `propagate` | affected-page preview/audit after new evidence or synthesis; propagation review, 受影響頁面 | manual preview/audit fallback | Medium | Codex app report or `state/gates/propagation/` |
| `graph` | export links and state; 知識圖譜, graph links | graph JSON | Low | `graph/` |
| `codex-handoff` | create a compact wiki context capsule for another Codex session/project; Codex handoff prompt, context capsule | context capsule | Medium | `prompts/` |
| `public-dashboard` | research hotspot dashboard, GitHub Pages, RKF settings visualization; 研究熱點網站, 儀表板 | aggregate-only preview, private visual review, and exact-hash local site snapshot | High for publication | `dashboard.preview`; private `dashboard.review`; approved `dashboard.publish` to `site/data/` |

## `rkf-lint`

| Mode | English / 中文 Trigger | Output | Oversight | Write Boundary |
|---|---|---|---|---|
| `structure-lint` | frontmatter, page type, topic registry; 結構檢查 | findings | Low | Codex app report |
| `evidence-lint` | reading maturity, full-text state, claim boundary, legacy records; 證據檢查, 閱讀成熟度 | findings | Medium | Codex app report |
| `graph-lint` | typed graph and wiki links; 圖譜檢查, broken links | findings | Low | Codex app report |
| `ars-handoff-lint` | ARS output labeled as proposal; ARS回寫檢查 | findings | Medium | Codex app report |
| `public-safety-lint` | PDFs, article text, local paths, private state; 發布安全, private path | findings | High | Codex app report |
| `reconcile` | contradiction scan and AI-marked blockers; 矛盾整合, reconcile | contradiction report or page-local blockers | High | target pages through `evolve` |
| `repair-plan` | repair suggestions; 修復計畫, 不自動改 | plan only | Medium | report |

## `rkf-connect`

| Mode | English / 中文 Trigger | Output | Oversight | Write Boundary |
|---|---|---|---|---|
| `shared-database-plan` | shared database, Google Drive ResearchSync, RAW/wiki layout; 建立共享資料庫, 多電腦共享, Google Drive資料庫 | machine-neutral connection plan | High | docs/proposal only |
| `link-workspace` | link Drive RAW/wiki into RKF folder, symlink, junction, ln; 連結wiki, 連結RAW, symlink, junction | per-machine link checklist | High | local setup notes; no committed links |
| `handoff-grant` | Codex handoff read access, context capsule, permission boundary; Codex handoff讀取wiki, session授權 | access capsule with read/save boundaries | High | `prompts/` or handoff text |
| `handoff-bootstrap` | start RKF in another Codex session/project; 在其他Codex session啟動RKF, handoff啟動提示 | reusable bootstrap prompt | Medium | committed prompt template only |
| `handoff-direct-write` | trusted Codex handoff requests guarded RKF actions after explicit write approval; 其他Codex session搜尋論文並加入wiki | guarded Codex app workflow | High | RKF actions preserve maturity and claim boundaries |
| `handoff-save-proposal` | handoff found useful question/claim/synthesis; handoff回寫, 保存有意義問題 | RKF save/review proposal | Medium | review queue or proposal text |
| `connect-project` | make RKF available to another local project; 連結研究專案, project bridge | previewed v2 marker and non-overwriting `RKF/` bridge | Medium | target `.rkf-connect.toml` and missing `RKF/` files only |

## Bridge Protocol

ARS outputs from `deep-research`, `academic-paper`, `academic-paper-reviewer`,
or `academic-pipeline` can become RKF proposals only. For wiki questions, RKF
retrieves governed wiki context, ARS reasons over the context, and RKF saves
the result only through explicit `save`, `review`, `synthesize`, or paper
reading-draft updates. ARS output cannot by itself satisfy a claim boundary.
