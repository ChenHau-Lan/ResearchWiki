# 實作紀錄：我想整理在台灣的大氣實驗

## 1. 起始需求

使用者問題：

> 我想整理在台灣的大氣實驗，如 TAMEX、SOMEX、TAHOPE。

Skill routing：

- `academic-research-skills` / `deep-research:lit-review`：找 SCI paper 與
  可能的 DOI/PDF route。
- `academic-research-skills` / `deep-research:fact-check`：確認 source
  identity，並把 ARS 結果保留為 proposal context。
- `rkf-evidence-vault`：capture source、stage 合法 PDF route、做 PDF QC。
- `rkf-knowledge-synthesis`：從 QCed PDF 建立 paper、concept、overview 與
  synthesis pages。
- `rkf-wiki-core`：用既有 wiki pages 回答「未來台灣要做氣象觀測實驗的建議」。
- `rkf-lint`：確認範例沒有 PDF、全文、本機 private path 進 Git。

## 2. Topic 設計

Topic ID：`taiwan-atmospheric-field-campaigns`

範圍包含 TAMEX、SoWMEX/TiMREX、TAHOPE/PRECIP、Cape Fuguei、Lulin、台灣
複雜地形降雨、radar microphysics、data assimilation 與 aerosol-cloud
observation。

## 3. 文獻搜尋

初始 SCI 候選清單保存在 `literature_candidates.md`。本範例在 checkpoint/QC
後攝取代表性 PDF：

- Chen and Liang 1992 TAMEX midlevel vortex
- You et al. 2020 SoWMEX IOP8 dual-polarimetric radar model validation
- Miao et al. 2025 TAHOPE/PRECIP IOP2 convective cell merger
- Cheung et al. 2020 Cape Fuguei CCN hygroscopicity
- Chang et al. 2021 CCN and diurnal precipitation over Taiwan topography
- Lin et al. 2026 Lulin aerosol-cloud mixing ratio

Kuo and Chen 1990、Chang et al. 2015、Yang et al. 2024 目前仍是候選，等
合法 PDF acquisition 與 QC 完成後才升級成 wiki paper page。

## 4. PDF QC

每篇文章都有 `state/gates/pdf_acquisition/*.md` 記錄：

- source identity
- legal route
- readability
- PDF locators
- no durable article-text layer

## 5. Wiki 攝取

每份 QCed PDF 建立一個 `knowledge/papers/*.md`。每頁只摘要與記錄 locator，
不保存 PDF 或全文。

## 6. Wiki 提問

問題：

> 未來台灣要做氣象觀測實驗，有哪些建議？

回答保存在：

`knowledge/synthesis/future-taiwan-meteorological-observation-experiment.md`

核心結論：未來台灣觀測實驗應把 TAMEX、SoWMEX/TiMREX、TAHOPE/PRECIP
視為設計階梯，從 terrain-rainfall diagnosis 走向 radar microphysics、data
assimilation、prediction products 與 data governance。

## 7. 下一步

- 補 Kuo and Chen 1990 TAMEX overview，通過 PDF QC 後建立 overview。
- 補 Chang, Lee, and Liou 2015 SoWMEX/TiMREX microphysics，通過 PDF QC 後攝取。
- 補 Yang et al. 2024 TAHOPE/PRECIP IOP3 data-assimilation paper。
- 補 radar/disdrometer/profiler/aircraft deployment papers。
- 補更多台灣 in-situ cloud event papers。
- 把 draft synthesis 中的 claim 逐條升級成有 locator 的 claim pages。
