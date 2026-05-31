# RKF 操作手冊

Research Knowledge Framework（RKF）是一個以 LLM Wiki 為核心的研究知識框架。
它把研究討論、文獻線索、topic、question、claim、concept、synthesis 變成可治理、
可查詢、可累積的長期記憶。

PDF 不是知識庫的源頭，而是 paper 閱讀時最常見、最強的 evidence carrier。RKF
真正管理的是：來源是否可信、證據是否能回到 locator、討論結果是否值得保存、
topic 是否漂移，以及 wiki 是否能在下次研究時接續使用。

![Skill triggers](assets/rkf_taiwan_atmospheric_experiment/01_skill_triggers.png)

## 核心心智模型

LLM Wiki 的核心不是「把資料夾變漂亮」，而是讓 LLM 的思考可以累積。ARS 可以幫你
快速研究、查核、寫作與審查；RKF 補上的是長期記憶、topic governance、evidence
boundary 與可維護的 wiki graph。

```text
研究想法 -> topic governance -> evidence candidates -> ARS analysis
-> RKF memory decision -> wiki page / review queue / synthesis
```

Wiki page 不只有 paper。RKF 會維護 paper、question、concept、claim、topic、
overview、synthesis 等頁面。一次 query 的回答不是 wiki page；只有當它被保存成
question、claim、concept 或 synthesis 時，才成為長期知識物件。

## RKF 與一般 LLM Wiki 的差異

一般 LLM Wiki 的設計重點是降低知識庫維護成本：人類把文章、筆記、PDF 或會議記錄放進
raw collection，LLM 讀取後維護 wiki、index、log 和交叉引用。這很適合個人知識管理、
閱讀伴侶、團隊內部 wiki 或 Obsidian-first workflow。

RKF 保留這個核心，但把它變成 academic research workflow。差異不是資料夾名稱，而是
「什麼能被升級成穩定研究知識」：

- 一般 LLM Wiki 的 raw source 可以直接驅動 wiki 更新；RKF 的 DOI、URL、PDF、topic
  lead 先是 candidate 或 SourceRecord。
- 一般 LLM Wiki 的 ingest 偏向摘要與連結；RKF 的 paper page 需要合法 acquisition、
  PDF/OCR/visual QC、locator notes 和 evidence boundary。
- 一般 LLM Wiki 的好回答可直接存成頁面；RKF 的 query answer 先是 save/review proposal，
  只有符合保存條件才成為 question、claim、concept 或 synthesis。
- 一般 LLM Wiki 的 lint 偏向矛盾、孤兒頁、過期內容；RKF 另外檢查 metadata-only
  promotion、claim support、ARS handoff、topic drift 和 public-safety。
- 一般 LLM Wiki 讓 Obsidian graph 變好用；RKF 另外輸出 typed research graph，讓
  source、evidence、topic 和 knowledge object 的關係可審計。

因此，RKF 的定位是 evidence-governed LLM Wiki。它可以像 Obsidian wiki 一樣被閱讀與瀏覽，
但不能把「已整理」誤當成「已有證據」。

## 從 0 建立一個 Codex 研究知識庫

1. 在 Codex 中建立一個新的研究專案資料夾，例如 `ResearchKnowledgeFramework`。
2. 將 RKF repo 放進這個資料夾，作為 rules、templates、schemas、skills、manuals
   與 public-safe wiki pages 的 Git root。
3. 在 Codex 安裝或啟用 `academic-research-skills`。ARS 是研究分析與寫作能力來源；
   RKF 是保存與治理層。
4. 先用本機 RKF workspace 開始，不必一開始就設定跨電腦同步。共享資料庫、Drive
   連結與 private artifact 位置是實驗性 `rkf-connect` 流程，放在本手冊最後。
5. 建立第一個 topic。AI 會先搜尋既有 topic registry，若找不到合適 topic，才提議
   新 topic；你可以後續修正 aliases、scope、include/exclude rules、search strings。
6. 開始 capture DOI、URL、PDF、題目或研究想法。這些先是 candidates，不是 evidence。
7. 找文獻後先停在 checkpoint：哪些已取得可 QC artifact、哪些缺 PDF/full text、哪些
   需要你自行透過合法管道取得。
8. 只有通過 evidence QC 的 paper artifact 才能建立 paper wiki page；跨文獻想法再
    保存成 question、concept、claim 或 synthesis。

![Codex workspace setup](assets/rkf_taiwan_atmospheric_experiment/02_source_intake.png)

## 用 Obsidian 閱讀 RKF

RKF 可以直接作為 Obsidian vault 開啟。若使用本機 repo，打開 RKF root；若使用共享資料庫，
打開 `storage.wiki_root` 指向的 shared wiki folder。Obsidian 是閱讀、檢查與圖譜瀏覽介面；
穩定寫入仍應由 RKF skills 和 gates 控制。

建議閱讀入口：

- `index.md`：LLM 和人類快速定位頁面的壓縮目錄。
- `log.md`：跨 session 操作歷史與較長的 narrative workflow record。
- `hot.md`：最近反覆出現的 public-safe 研究問題和 paper-search demand。
- `knowledge/papers/`：已通過 evidence gate 的 paper notes。
- `knowledge/questions/`、`knowledge/concepts/`、`knowledge/claims/`、`knowledge/synthesis/`：
  可重用的研究問題、概念、主張與綜整。
- `knowledge/topics/` 與 `governance/topic_registry.json`：topic scope、aliases、include/exclude
  rules 和 search strings。
- `state/gates/`：可以人工 review 的 acquisition、QC 或 support checkpoints。

建議不要在 Obsidian 中手動維護這些內容：

- 不要把 PDF、全文、browser capture、私人截圖或 private Drive path 拖進 public vault。
- 不要手動把 candidate paper 改成 paper page；先回到 acquisition 與 QC。
- 不要刪除或批量改寫 `state/`、`graph/`、`hot.md` 的機器可讀區塊。
- 若要人工修正 wiki page，保留 frontmatter、`evidence_boundary`、locator 與 review blocker；
  修正後讓 RKF 做 lint。

Obsidian graph view 可以用來看 topic、paper、concept、question 和 synthesis 的連接形狀。
如果某個重要 paper page 沒有連到 concept 或 synthesis，這通常不是視覺問題，而是
topic-review 或 graph-lint 的信號。Dataview 類插件可用 frontmatter 欄位如 `type`、
`topics`、`evidence_tier`、`review_stage` 建立列表，但這些列表只是閱讀輔助，不改變
evidence status。

## 什麼時候用什麼 Skill 和 Mode

| 階段 | 使用情境 | Skill | Mode | 產出 | 重要邊界 |
|---|---|---|---|---|---|
| 釐清題目 | 題目、縮寫或範圍不清楚 | `academic-research-skills` | `deep-research:socratic` 或 `deep-research:quick` | 搜尋範圍與關鍵字 | 還不寫 RKF wiki |
| 找文獻 | 需要 SCI paper、DOI、研究脈絡 | `academic-research-skills` | `deep-research:lit-review` | 候選文獻清單 | 候選不是 evidence |
| 查核來源 | DOI、作者、版本、取得路徑需要確認 | `academic-research-skills` | `deep-research:fact-check` | source verification notes | ARS output 仍是 proposal |
| 攝取來源 | 有 DOI/URL/PDF/topic lead | `rkf-evidence-vault` | `capture` | SourceRecord | 不能直接生成 paper page |
| 候選管理 | 找完文獻但還缺 PDF 或全文 | `rkf-evidence-vault` | `discover` | candidate backlog / missing artifact checkpoint | 缺 evidence 的 paper 留在 review queue |
| 取得 evidence | 找到合法 PDF、官方文件、截圖或授權文本 | `rkf-evidence-vault` | `acquire` | acquisition checkpoint | 不明來源要停止 |
| Evidence QC | 需要確認 artifact 可用性 | `rkf-evidence-vault` | `verify-pdf` | QCed reading artifact 與 locators | 未 QC 不得寫 paper |
| 寫 wiki | Evidence 已 QC，可建立知識頁 | `rkf-knowledge-synthesis` | `distill-paper`、`save-concept`、`synthesize` | paper/concept/synthesis pages | 每個 claim 要能回到 locator |
| Topic 維護 | topic 長大、候選堆積、範圍漂移 | `rkf-knowledge-synthesis` | `topic-review` | merge/split/search-string/update proposal | 先提建議，不直接大改 registry |
| 問知識庫 | 需要根據既有 wiki 回答問題 | `rkf-wiki-core` | `query` | RKF context + ARS analysis + save proposal | 回答不自動成為 wiki page |
| 維護 | topic 成長、重大新增、分享前 | `rkf-lint` | `structure-lint`、`evidence-lint`、`graph-lint`、`ars-handoff-lint`、`public-safety-lint`、`repair-plan` | findings 或修復計畫 | repair-plan 不自動批量改內容 |
| 連接共享資料庫 | 多台電腦、Drive 共享、外部 sandbox 存取 | `rkf-connect` | `shared-database-plan`、`link-workspace`、`sandbox-grant`、`sandbox-save-proposal` | 連接計畫或 proposal | 實驗性；不提交本機 link 或 private path |

## Skill Triggers / 常用觸發詞

| Skill | English Triggers | 中文觸發詞 |
|---|---|---|
| `academic-research-skills` | literature review, deep research, fact check, source verification | 文獻回顧、深度研究、找 SCI、查 DOI、查核來源 |
| `rkf-evidence-vault` | find papers, capture DOI, missing PDF, acquire evidence, PDF/OCR QC | 文獻搜尋、加入 DOI/URL/PDF、缺 PDF、合法取得、PDF 檢查、OCR 檢查 |
| `rkf-knowledge-synthesis` | paper note, wiki page, concept, question, claim, synthesis, topic review | 整理成 wiki、論文筆記、概念頁、問題頁、claim、綜整、topic 整理、topic 建議 |
| `rkf-wiki-core` | ask the wiki, ARS reasoning, save memory, graph, sandbox capsule | 問知識庫、ARS 分析、回寫 wiki、保存討論、知識圖譜、外部 sandbox |
| `rkf-lint` | audit, maintenance, repair plan, public safety, evidence boundary | 檢查、定期維護、修復計畫、證據邊界、發布安全、private path 檢查 |
| `rkf-connect` | shared database, Google Drive, symlink, junction, sandbox access | 共享資料庫、多台電腦、Google Drive、ln、symlink、junction、連結 wiki、外部 sandbox 權限 |

## Topic Governance

Topic 是 RKF 的研究索引，不只是資料夾名稱。每個 topic 應包含：

- topic ID：穩定、短、可放進 frontmatter。
- aliases：同義詞、縮寫、拼字變體。
- scope：這個 topic 管什麼。
- include / exclude rules：哪些文獻該進來，哪些不該進來。
- default search strings：ARS 和搜尋工具預設用的查詢語句。
- canonical pages：主要 topic、concept、synthesis 頁。
- review cadence：多久檢查一次 topic drift 和 candidate backlog。

當你提出新任務時，AI 應先查 topic registry，找最接近的 topic。如果沒有合適 topic，
再建立新 topic proposal。你可以後續修正 alias、scope、include/exclude 與 search
strings，這些修正會讓下一次文獻搜尋更穩定。

Topic 需要定期查看，不是只在建立時設定一次。`topic-review` 會回答四個問題：

- 這個 topic 是否變得太寬，需要拆成子題？
- 是否有兩個 topic 其實在管同一件事，應該 merge 或用 alias 串起來？
- candidate backlog 裡哪些 paper 還缺 artifact、哪些已不符合 scope？
- default search strings 是否太舊，導致 ARS 一直找到同一批或錯誤方向的文獻？

常用要求：

- 「幫我定期查看這個 topic，列出 merge/split 建議。」
- 「整理這個 topic 的 aliases、include/exclude rules 和 search strings。」
- 「根據目前 wiki，建議下一輪文獻搜尋要補哪些關鍵字。」
- 「檢查這個 topic 底下哪些 candidate 還缺 PDF，哪些應該移到其他 topic。」

## Wiki Page 類型與範本功能

RKF 的 wiki page 是知識物件，不只是閱讀筆記。不同 page type 的功能如下：

| Page Type | 主要功能 | 核心欄位 / section | 何時建立 |
|---|---|---|---|
| `paper` | 保存一篇已 QC artifact 的閱讀結果 | source identity、evidence boundary、PDF/visual locators、reading notes、claims to promote、graph links | 有合法且 QC 過的 paper artifact |
| `question` | 保存值得追蹤的研究問題 | question、why it matters、current evidence、missing evidence、next search | query 後發現問題會反覆被問或需要後續搜尋 |
| `concept` | 保存可重複使用的方法、變數、儀器、機制或資料集 | definition、scope、related papers、use cases、open caveats | 多篇文獻反覆出現同一概念 |
| `claim` | 保存可被證據支持或待查核的主張 | claim statement、supporting locator、confidence、caveat、review blocker | 某句話可能進 synthesis 或論文，但需要可追溯 |
| `topic` | 管理研究範圍與搜尋策略 | topic ID、aliases、scope、include/exclude、default searches、canonical pages、review cadence | 開始一個研究方向或整理既有方向 |
| `overview` | 保存專案、資料集、experiment 或領域概覽 | context、scope、key artifacts、related topics、limitations | 來源不是單一 SCI paper，但能提供脈絡 |
| `synthesis` | 保存跨來源判斷、研究建議或可重用答案 | synthesis question、evidence base、claims、gaps、recommendations、review status | 回答跨多個 source、影響研究決策或會反覆使用 |
| `project-synthesis` | 保存某個專案階段的整體結論 | project goal、source set、decision log、remaining blockers、next actions | 一個研究專案需要階段性整理 |
| `meeting` | 保存會議中產生的研究決策與待辦 | agenda、decisions、evidence links、action items、save proposals | 會議結論會影響 topic 或 synthesis |
| `seminar` | 保存演講、讀書會、研討會中的可回寫知識 | speaker/context、main claims、related papers、questions、follow-up | 外部知識來源值得轉成 question/concept/claim |

所有 page 都應有 frontmatter：`type`、`status`、`review_stage`、`topics`、
`evidence_boundary`、`created`、`updated`。`evidence_boundary` 用來表示這頁是基於
PDF evidence、既有 wiki page、ARS proposal，還是仍有 review blocker。

## Evidence Checkpoint 與 QC

找完 SCI paper 後，不要立刻寫 paper page。先建立 checkpoint：

| 類別 | 意義 | 下一步 |
|---|---|---|
| 已取得可 QC artifact | 有合法 PDF、官方文件或授權文本 | 進入 evidence QC |
| 缺 PDF / 缺全文 | 只有 DOI、metadata、abstract 或候選頁 | 留在 candidate backlog，不寫 paper page |
| 需要使用者取得 | 可能有學校授權、作者稿、出版社頁、掃描件 | 使用者取得後再回到 RKF |

PDF QC 發生在 acquisition checkpoint 之後、paper page 之前。它確認：

- source identity：title、authors、DOI、journal、year 是否一致。
- legal route：open access、publisher free access、institutional access、user-provided artifact 或官方文件。
- version：publisher version、author manuscript、preprint、scan 是否標清楚。
- readability：PDF 可渲染，頁面和圖表可讀。
- locator：paper page 使用的頁碼、章節、圖表或視覺位置。

古早文獻若是掃描圖形檔，QC 需要補上 visual/OCR notes。可以用頁面截圖、頁碼、
人工讀圖、OCR confidence note。若 OCR 不可靠，只能保存 visual locator 和人工摘要；
不要宣稱已取得可全文搜尋的 full-read text evidence。

![Evidence QC](assets/rkf_taiwan_atmospheric_experiment/04_pdf_qc.png)

## 實作範例：台灣大氣實驗

完整範例在
[`examples/taiwan-atmospheric-experiment/`](../../examples/taiwan-atmospheric-experiment/)。
起始 prompt 是：

> 我想整理在台灣的大氣實驗，如 TAMEX、SOMEX、TAHOPE。

### 1. 建立 Topic

AI 會先檢查 topic registry 是否已有相關 topic。若已有相近 topic，會把新候選掛到該
topic；若沒有，才建立新 topic proposal。範例使用：

Topic ID：`taiwan-atmospheric-field-campaigns`

Scope：台灣大氣觀測 campaign 與 field study，重點包含 TAMEX、SoWMEX/TiMREX、
TAHOPE/PRECIP、複雜地形降雨、Mei-yu fronts、southwest monsoon、typhoon
rainfall、dual-polarimetric radar、data assimilation、aerosol、CCN 與 cloud
microphysics。

### 2. 用 ARS 找 SCI Paper

這一步使用 `academic-research-skills` 的 `deep-research:lit-review` 產生候選，再用
`deep-research:fact-check` 查 DOI、期刊、版本與取得路徑。

| 狀態 | Paper | DOI / Route | RKF 決策 |
|---|---|---|---|
| 已 QC，已進 wiki | Chen and Liang 1992 TAMEX midlevel vortex | `10.2151/jmsj1965.70.1_25`; J-STAGE free PDF | 建立 TAMEX paper page |
| 候選，缺 artifact | Kuo and Chen 1990 TAMEX overview | `10.1175/1520-0477(1990)071<0488:TTAMEA>2.0.CO;2`; AMS | 等使用者取得合法 PDF 或授權文本 |
| 已 QC，已進 wiki | You, Chung, and Tsai 2020 SoWMEX IOP8 | `10.3390/rs12183004`; MDPI | manual browser checkpoint 後 QC |
| 候選，缺 artifact | Chang, Lee, and Liou 2015 SoWMEX/TiMREX microphysics | `10.1175/MWR-D-14-00081.1`; AMS/UCAR | 留在 candidate backlog |
| 已 QC，已進 wiki | Miao et al. 2025 TAHOPE/PRECIP IOP2 | `10.1029/2024JD042375`; open PDF route | 建立 TAHOPE/PRECIP paper page |
| 候選，缺 artifact | Yang et al. 2024 TAHOPE/PRECIP IOP3 | `10.1175/MWR-D-24-0049.1`; AMS | 等合法 PDF/QC |
| Project context | TAHOPE official introduction PDF | official project PDF | 建立 project overview，不當作 SCI paper |

![SCI candidates](assets/rkf_taiwan_atmospheric_experiment/03_sci_candidates.png)

### 3. 從 Evidence 攝取到 Wiki Page

Paper page 是一種 wiki page，但不是唯一 wiki page。範例 paper page 會包含：

- frontmatter：type、status、source_id、review_stage、evidence_boundary、topics。
- Source Identity：這篇 paper 的 DOI、journal、experiment、evidence status。
- PDF / visual locators：摘要、方法、圖表或結論在 artifact 的位置。
- Reading Notes：研究問題、資料、方法、核心發現。
- Claims To Promote：可升級為 claim 的句子，但仍要保留 locator 與 caveat。
- Graph Links：連到 topic、concept、question、synthesis。

![Wiki paper page](assets/rkf_taiwan_atmospheric_experiment/05_wiki_page.png)

攝取完 paper pages 後，ARS 可以基於這些頁面建議值得問的問題，例如：

- 這些 experiment 的觀測設計如何從地形降雨診斷走向 prediction system？
- 哪些儀器或資料流在不同世代 experiment 中反覆出現？
- 哪些候選文獻缺 artifact，會限制目前 synthesis 的可信度？

### 4. 針對 Wiki 提問並保存 Synthesis

問題：

> 未來台灣要做氣象觀測實驗，有哪些建議？

流程是：

1. RKF 先取回相關 topic、paper、concept、question、candidate backlog。
2. ARS 針對這些受治理的 wiki context 做分析與建議。
3. RKF 標出 evidence gap 和仍需使用者取得 artifact 的文獻。
4. RKF 記錄 public-safe hot-query signal，讓反覆出現的問題能進入 topic review。
5. 若答案跨多個 source、形成研究決策、未來會反覆使用、或影響 topic direction，
   才保存為 synthesis。

範例 synthesis 建議把 TAMEX、SoWMEX/TiMREX、TAHOPE/PRECIP 視為設計階梯：
從地形降雨診斷走向 radar microphysics、data assimilation、prediction products
與 data governance。

![Query answer](assets/rkf_taiwan_atmospheric_experiment/06_query_answer.png)

## 用 `hot.md` 追蹤反覆出現的研究需求

`hot.md` 是最近常被問到的問題與 paper-search 需求的單一檢索檔。用它來看目前哪些
topic 最活躍、哪些問題反覆出現、哪些 paper lead 正在被搜尋，以及哪些 query 還沒有
對應到受治理的 topic。

它只是 operational memory。`hot.md` 裡的一行不會讓 claim 成立，不算 evidence，
也不會建立 paper page。它告訴 RKF 研究流程正在需要什麼，讓 topic review 可以回應：
補 aliases、更新 search strings、整理 candidate backlog，或提出新 topic proposal。

常見用法：

- 問 wiki 或搜尋文章時，RKF 記錄 public-safe hot-query event。
- 做 topic 維護前先看 `hot.md`，找反覆問題與過期搜尋需求。
- unknown-topic query 先當 triage item，不要自動建立新 topic。
- 常被問的問題可用來判斷是否需要保存成 question、synthesis，或 topic-review proposal。

外部 sandbox 用法：

- sandbox 應回傳 hot-query proposal，或透過 RKF hot-query 行為記錄短而 public-safe 的研究問題。
- 不要另外建立 hot-query 分檔，也不要設置獨立 sandbox inbox。
- 紀錄行應保持簡短，格式如下：

```text
- 2026-05-26 | origin=external-sandbox | topic=aerosol-ice-phase-clouds | intent=paper-search | query="supercooled liquid IWP aerosol mechanism"
```

不要把 PDF、文章全文、browser capture、raw chat transcript、私人 Drive path、本機路徑、
token 或 secrets 放進 `hot.md`。

## `log.md` 與操作日誌慣例

`log.md` 的用途是讓下一次 LLM session 和人類 reviewer 快速知道 wiki 最近發生什麼事。
它不是 evidence layer，也不是 raw transcript。所有內容都必須 public-safe、可摘要、可
grep，並且避免放入 PDF 內容、全文摘錄、私人路徑或未審查的長聊天紀錄。

RKF 日誌分成兩種層級：

- Compact event：短操作紀錄，用於 capture、save、index refresh、hot-query 等機器可讀事件。
  形式通常是 timestamp、action 和一句 message。
- Narrative record：較長的 workflow 記錄，用於一次完整研究流程、功能對照、topic review
  或重大設計決策。

Narrative record 建議格式：

```text
## [YYYY-MM-DD] action | short title

### 觸發
使用者需求、問題或來源。

### Evidence boundary
這次記錄能支持什麼，不能支持什麼。

### Context
讀到哪些 governed wiki pages、source records、gates 或外部 conceptual references。

### Decision / Output
本次產出的保存決策、wiki 改動或後續 proposal。

### Follow-up
下一步要補的 evidence、topic review、lint 或人工檢查。
```

`index.md` 回答「有哪些頁面」；`log.md` 回答「最近做了什麼」；`hot.md` 回答「最近反覆
需要什麼」。三者都能幫助 LLM 接續工作，但只有符合 evidence gate 的 knowledge page 才能
承載穩定研究主張。

## 維護為什麼重要

知識庫不維護會慢慢失真：topic 會漂移、candidate paper 會被忘記、claim 會脫離
evidence、graph link 會斷、synthesis 會過期、private evidence 可能被誤放進 Git。

維護可以這樣呼叫：

- 「幫我做這個 topic 的定期維護。」
- 「檢查有哪些 candidate 還缺 PDF 或全文。」
- 「檢查 synthesis 是否過期，哪些 claim 需要更新。」
- 「做 evidence-lint、graph-lint 和 public-safety-lint。」
- 「產生 repair-plan，不要自動改內容。」

建議節奏：

- Active topic：每週檢查 topic drift、candidate backlog、evidence boundary、graph links。
- 重大新增 PDF / ARS report / synthesis 前後：半自動觸發 evidence-lint 與 ars-handoff-lint。
- Stable topic：每月檢查 stale synthesis、unresolved candidates、duplicate concepts。
- 分享或發布前：一定做 public-safety-lint。
- 穩定 wiki 寫入後：刷新 `index.md`，讓 `log.md` 保留下一次 LLM session 可讀的操作軌跡，並查看 `hot.md` 的重複問題。

## 實驗項目：建立共享資料庫在不同電腦

共享資料庫不是 RKF 的基本需求，而是當你想在多台電腦或外部 sandbox 共用同一份研究
記憶時才啟用。這部分由 `rkf-connect` 管理。

目前方法：

```text
<Drive ResearchSync>/
  raw/
  wiki/
    index.md
    log.md
    knowledge/
    state/
    governance/
    graph/
```

- Google Drive for desktop 作為共享資料夾，`raw` 和 `wiki` 放真實資料。
- 每台電腦在自己的 RKF 專案資料夾建立本機 link，連到 Drive 裡的 `raw` 和 `wiki`。
- macOS/Linux 可用 `ln` 或 symlink；Windows 可用 junction 或 symlink。
- 不把跨平台 link、private Drive path 或授權資料 commit 到 public repo。
- 當 `storage.wiki_root` 有設定時，RKF 會把該資料夾視為 `knowledge`、`state`、
  `governance`、`graph` 的 active database。
- `index.md` 提供 LLM session 壓縮取回入口；`log.md` 保存 append-only 操作歷史。
- 外部 sandbox 預設只讀 wiki。先產生 `external-sandbox` context capsule，再用
  `prompts/external_sandbox_bootstrap.zh-TW.md` 啟動另一個 sandbox。
- 可信任的 sandbox 可以被授予 RKF repo 寫入權限，並透過 RKF CLI 直接執行
  `capture -> acquire -> verify-pdf -> distill`。這仍然必須通過 evidence gates。
- 若只有搜尋結果、topic fit 不確定、PDF 尚未 QC、locator 不足、claim support 不明確，
  或 sandbox 沒有寫入權限，回傳 `sandbox-save-proposal`，再由 RKF 決定是否保存。

外部 sandbox 搜尋與閱讀論文時，建議路徑是：

```text
literature search
  -> source candidate
  -> capture DOI/URL/PDF pointer
  -> legal acquisition checkpoint
  -> PDF/OCR/visual QC with locators
  -> paper wiki distillation
```

請記住：candidate 不是 evidence，ARS/deep-research 報告本身也不是 evidence。暫時讀取
PDF text 或 OCR text 可以用來理解文章，但不要把全文、PDF、browser capture、private
Drive path、token 或 local secret 寫入 RKF。

`rkf-connect` 的常用要求：

- 「幫我規劃 Google Drive 共享資料庫，讓 Mac 和 Windows 都可以連到同一份 raw/wiki。」
- 「檢查這台電腦的 RKF link 設定，確認沒有把 private path 寫進 repo。」
- 「生成外部 sandbox 可用的 wiki 讀取說明和回寫 proposal 格式。」
- 「在另一個 sandbox 啟動 RKF 模式，讓它可以搜尋論文並照 gates 加入 wiki。」
- 「把外部 sandbox 覺得有價值的問題轉成 RKF question proposal。」

## Reference Sources

- [Kuo and Chen 1990 TAMEX overview](https://journals.ametsoc.org/abstract/journals/bams/71/4/1520-0477_1990_071_0488_ttamea_2_0_co_2.xml)
- [J-STAGE Chen and Liang 1992 TAMEX paper](https://www.jstage.jst.go.jp/article/jmsj1965/70/1/70_1_25/_article)
- [J-STAGE Wang and Chen 2003 TAMEX paper](https://www.jstage.jst.go.jp/article/jmsj/81/2/81_2_339/_article)
- [MDPI You et al. 2020 SoWMEX IOP8 paper](https://www.mdpi.com/2072-4292/12/18/3004)
- [UCAR Chang et al. 2015 SoWMEX/TiMREX paper](https://www.eol.ucar.edu/publications/kinematic-and-microphysical-characteristics-and-associated-precipitation-efficiency)
- [TAHOPE Project Office](https://rain.as.ntu.edu.tw/TAHOPE/TAHOPE-home.html)
- [TAHOPE introduction PDF](https://exp.pccu.edu.tw/TAHOPE_2019/data/TAHOPE_Introduction.pdf)
- [Miao et al. 2025 TAHOPE/PRECIP PDF](https://tropical.colostate.edu/Publications/papers/Miao_etal_JGR_2025.pdf)
- [TAHOPE/PRECIP IOP3 paper record](https://www.researchgate.net/publication/384138264_Investigating_the_mechanisms_of_an_intense_coastal_rainfall_event_during_TAHOPEPRECIP-IOP3_using_a_multiscale_radar_ensemble_data_assimilation_system)
