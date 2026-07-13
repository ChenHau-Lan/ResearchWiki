# 實作紀錄：我想整理在台灣的大氣實驗

## 1. 起始需求

使用者問題：

> 我想整理在台灣的大氣實驗，如 TAMEX、SOMEX、TAHOPE。

Skill routing：

- `academic-research-suite` / `deep-research:lit-review`：找 SCI paper 與
  可能的 DOI/PDF route。
- `academic-research-suite` / `deep-research:fact-check`：確認 source
  identity，並把 ARS 結果保留為 proposal context。
- `rkf-evidence-vault`：capture source、追蹤 full-text route、做 locator check。
- `rkf-knowledge-synthesis`：建立 paper reading draft、concept、overview 與
  synthesis pages。
- `rkf-wiki-core`：用既有 wiki pages 回答「未來台灣要做氣象觀測實驗的建議」。
- `rkf-lint`：確認範例沒有 PDF、全文、本機 private path 進 Git。

## 2. Topic 設計

Topic ID：`taiwan-atmospheric-field-campaigns`

範圍包含 TAMEX、SoWMEX/TiMREX、TAHOPE/PRECIP、Cape Fuguei、Lulin、台灣
複雜地形降雨、radar microphysics、data assimilation 與 aerosol-cloud
observation。

## 3. 文獻搜尋

初始 SCI 候選清單保存在 `literature_candidates.md`。本範例先建立 reading draft，
再透過 full-text route note 和 locator check 提升代表性 paper 的成熟度：

- Chen and Liang 1992 TAMEX midlevel vortex
- You et al. 2020 SoWMEX IOP8 dual-polarimetric radar model validation
- Miao et al. 2025 TAHOPE/PRECIP IOP2 convective cell merger
- Cheung et al. 2020 Cape Fuguei CCN hygroscopicity
- Chang et al. 2021 CCN and diurnal precipitation over Taiwan topography
- Lin et al. 2026 Lulin aerosol-cloud mixing ratio

Kuo and Chen 1990、Chang et al. 2015、Yang et al. 2024 目前仍是候選或
metadata-only item，等 user PDF/full text 與 locator 可用後再提升 claim readiness。

## 4. Reading Maturity Update

每篇文章都有 `state/reading/fulltext_routes/*.md` 記錄：

- source identity
- full-text route
- readability
- locators
- no durable article-text layer

## 5. Wiki 攝取

每個 registered paper 都可以建立一個 `knowledge/papers/*.md`。每頁摘要目前理解、
記錄 reading maturity，並在可用時保存 locator；不保存 PDF 或全文。

## 6. Wiki 提問

問題：

> 未來台灣要做氣象觀測實驗，有哪些建議？

回答保存在：

`knowledge/synthesis/future-taiwan-meteorological-observation-experiment.md`

核心結論：未來台灣觀測實驗應把 TAMEX、SoWMEX/TiMREX、TAHOPE/PRECIP
視為設計階梯，從 terrain-rainfall diagnosis 走向 radar microphysics、data
assimilation、prediction products 與 data governance。

## 7. 下一步

- 補 Kuo and Chen 1990 TAMEX overview draft；若 full text 不可得，再請 user 提供 PDF。
- 補 Chang, Lee, and Liou 2015 SoWMEX/TiMREX microphysics，等 full-text route 或 user PDF 可用後提升 maturity。
- 將 Yang et al. 2024 TAHOPE/PRECIP IOP3 data-assimilation paper 保留在 active queue，直到 full text 和 locator 可用。
- 補 radar/disdrometer/profiler/aircraft deployment papers。
- 補更多台灣 in-situ cloud event papers。
- 把 draft synthesis 中的 claim 逐條升級成有 locator 的 claim pages。
