# 範例：台灣大氣實驗知識庫

這個範例示範 RKF 如何處理：

> 我想整理在台灣的大氣實驗，如 TAMEX、SOMEX、TAHOPE。

流程先用 Codex `academic-research-suite` 做 ARS-style 文獻搜尋與 source verification，
再用 RKF skills 做 source capture、full-text route note、paper reading maturity、
paper wiki draft，以及最後針對 wiki 提問：「未來台灣要做氣象觀測實驗，有哪些建議？」

## 這個範例包含什麼

| Path | 用途 |
|---|---|
| `literature_candidates.md` | 針對主題找到的 SCI paper 候選 |
| `governance/topic_registry.json` | Topic ID、scope、aliases、include/exclude rules、default search strings |
| `skill_mode_walkthrough.md` | 什麼時候使用 ARS mode，什麼時候回到 RKF mode |
| `state/sources/` | Public-safe source records |
| `state/evidence/` | Public-safe evidence artifact pointers；實際 PDF 不在 repo |
| `state/reading/` | Reading ledgers 與人工 full-text route notes |
| `knowledge/papers/` | 含 reading maturity 的 paper wiki pages |
| `knowledge/questions/` | 決策導向的 question page |
| `knowledge/synthesis/` | 回答範例問題的 synthesis |
| `graph/research_graph.json` | Public-safe graph export |

## Reading And Evidence Boundary

實際 PDF 放在 private evidence root。這個 example 只保存
`PRIVATE_EVIDENCE_ROOT/doi_pdf/...` 這類 public-safe pointer。Paper pages 只保存
目前理解、reading maturity 與 locator；不保存全文。

## Alias Note

起始 prompt 保留使用者原始文字。Topic governance 會把模糊或變體名稱先記為
aliases，再由 ARS/RKF 在文獻脈絡中查核後決定 durable naming。

## 核心結果

範例 synthesis 建議：把 TAMEX、SoWMEX/TiMREX、TAHOPE/PRECIP 視為一條
世代演進線，從 mesoscale terrain-rainfall process diagnosis，到 monsoon
rainfall microphysics，再到整合 radar/data assimilation 與 storm microphysics
prediction。

## 截圖

![Skill triggers](screenshots/01_skill_triggers.png)

![SCI candidates](screenshots/03_sci_candidates.png)

![Wiki query answer](screenshots/06_query_answer.png)
