# Research Wiki 圖文快速開始

[English](research_wiki_skill_first_quickstart.en.md)

Research Wiki 是一個由 LLM 協助維護的 Markdown 研究知識庫。你把來源放進 `raw/`，讓 Codex 協助整理成 `wiki/`，再用 lint 維持連結、證據等級與研究問題的健康狀態。

![Research Wiki workflow](assets/skill_first/01_router_overview.png)

## 1. 建立研究知識庫

Research Wiki 有三個工作區：

- `raw/` 保存來源與證據。
- `wiki/` 保存整理後的研究理解。
- `maintenance/` 保存待審事項、repair plan、state 與 graph。

主要工作流：

```text
source-intake -> paper-ingest -> knowledge-workbench -> synthesis-research -> wiki-lint
```

你可以直接對 Codex 說像 `Use source-intake/add-source ...` 這樣的 skill/mode 句子，也可以打開 `ResearchWikiCodex.command` / `ResearchWikiCodex.cmd` 從選單選 skill 與 mode。

## 2. 第一次打開 Repo

在 Codex 裡打開這個 repo。若你還沒有 repo，請 Codex 幫你 clone；若已經在 repo 中，就請它直接使用目前資料夾。

你可以貼這段：

```text
請幫我從 0 啟動 Research Wiki。
請先讀 README.zh-TW.md、USER_GUIDE.zh-TW.md、INSTALL.zh-TW.md、AGENTS.md。
請檢查必要工具，缺工具時先說明用途；需要系統安裝或權限時先問我。
檢查成功後，請帶我用 source-intake/add-source 加入第一個 DOI 或 URL。
```

完成後，你會知道 repo 是否可用、第一篇來源要放在哪裡，以及下一步該使用哪個 mode。

## 3. 加入第一篇 Source

使用 `source-intake/add-source` 加入 DOI、DOI URL、article URL、PDF URL 或來源註記。

![source-intake flow](assets/skill_first/02_source_intake_flow.png)

這一步做三件事：

- 把來源放進 `raw/paper_sources.md`。
- 讓 dashboard 知道這篇 paper 等待處理。
- 保留後續取得全文與建立 paper page 的線索。

只使用你有權閱讀或下載的來源。加入來源不代表已經讀完全文，也不會建立 paper page。

## 4. 取得並整理 Full Text

使用 `source-intake/refresh-dashboard` 檢查 dashboard、PDF evidence 與 index 狀態。當來源可讀時，使用 `source-intake/qced-full-text` 建立 `raw/full_text/paper_file_key.md`。

Full text 進入 `raw/full_text/` 前要先確認：

- title、authors、year、venue、DOI 正確；
- 段落順序可讀；
- 表格、公式、圖說沒有被抽字破壞；
- frontmatter 標示 `qc_status: codex_qc_done`。

## 5. 建立 Paper Page

當 QCed full text 已經存在，使用 `paper-ingest/ingest-qced-full-text`。輸出會是 `wiki/literature/` 下面的 paper page。

![paper ingest boundary](assets/skill_first/03_paper_ingest_boundary.png)

Paper page 只整理單篇 paper：

- 它描述這篇 paper 的問題、方法、結果、限制與來源指標。
- 它不複製完整文章。
- 它不直接寫跨文獻結論。
- 若只有 metadata 或 abstract，頁面要標成 `metadata-only` 或 `abstract-only`。

## 6. Query：問目前已經知道什麼

使用 `knowledge-workbench/query` 問資料庫問題。

![knowledge workbench modes](assets/skill_first/04_knowledge_workbench_modes.png)

Query 會從既有 wiki 與 evidence index 回答，並標示：

- 哪些內容來自 full-read literature；
- 哪些只是 abstract、seminar 或 project context；
- 哪些 claim 還缺來源；
- 哪些問題值得放進 review queue。

Query 適合探索目前知識庫，不會修改檔案。

## 7. Save：把值得留下的內容放到正確位置

如果 Query 結果值得保存，先用 `knowledge-workbench/query-to-save` 整理成 Save proposal，再用 `knowledge-workbench/save` 寫入正確 target layer。

![save target layer](assets/skill_first/05_save_target_layer.png)

常見 target：

- 單篇 paper 事實：`wiki/literature/`
- 反覆出現的術語、方法、資料集、變數：`wiki/concepts/`
- 跨文獻判斷：`wiki/synthesis/`
- project decision 或會議後演化：`wiki/project_synthesis/` / `wiki/meetings/`
- 不確定、衝突、低 confidence：`maintenance/review_queue.md`

如果證據還不夠，先保存成 review item。

## 8. Synthesis：把多篇 Paper 連成研究判斷

當一篇 paper 可能影響多個 concept、synthesis 或 active question，使用 `synthesis-research/fanout-review` 建立 review proposal。

![synthesis review gate](assets/skill_first/06_fanout_review_gate.png)

Review proposal 應該回答：

- 這個 source 影響哪些頁面；
- 它支持或挑戰哪些 claim；
- confidence 是否合適；
- 是否需要 counter-evidence；
- 是否改變既有 interpretation。

核准後才使用 `synthesis-research/apply-approved-fanout` 寫入正式 wiki。

## 9. Wiki Lint：維持知識庫健康

使用 `wiki-lint` 定期檢查 Research Wiki。Lint 的目標是讓 knowledge base 持續可讀、可追溯、可擴充。

![wiki lint checks](assets/skill_first/07_wiki_lint_checks.png)

常用 modes：

- `structure-lint`：檢查 frontmatter、index、路徑、wikilinks、Graph Links 與 orphan pages。
- `semantic-lint`：檢查 stale claims、contradictions、evidence tier、missing counter-evidence 與 supersession。
- `repair-plan`：產生人工修復計劃。
- `state-graph`：重建 `maintenance/state.json` 與 `maintenance/graph.json`。

Lint 發現的缺口通常會回到三個地方：新的 source intake、review queue，或一次明確的 Save。

## 10. 下一步

- 查 mode 權限與進階維護：讀 [USER_GUIDE.zh-TW.md](../../USER_GUIDE.zh-TW.md)。
- 查完整 pipeline contract：讀 [Pipeline Architecture](../guides/research_wiki_pipeline_architecture.zh-TW.md)。
