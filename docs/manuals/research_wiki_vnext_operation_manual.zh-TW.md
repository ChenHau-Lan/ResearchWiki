# Research Wiki vNext 圖文操作手冊（Legacy）

這份 v1/vNext 操作手冊已被 v2 的 [Skill-first 圖文快速開始](research_wiki_skill_first_quickstart.zh-TW.md) 取代。

保留這個檔案只為了讓舊連結不斷裂。請不要再依照舊版 command option numbers 操作；Research Wiki v2 的正式入口是 pipeline skills + modes：

```text
source-intake -> paper-ingest -> knowledge-workbench -> synthesis-research -> wiki-lint
```

## v2 要改用什麼

- 新手配圖教學：[Skill-first 圖文快速開始](research_wiki_skill_first_quickstart.zh-TW.md)
- Mode reference：[USER_GUIDE.zh-TW.md](../../USER_GUIDE.zh-TW.md)
- 完整權限與資料邊界：[Pipeline Architecture](../guides/research_wiki_pipeline_architecture.zh-TW.md)

## 舊手冊的保留原因

舊版手冊曾用來驗證 v1/vNext 的 PDF intake、dashboard、QC handoff、query/save、fan-out、semantic lint、thesis review 與 runtime graph。v2 已把這些能力重新整理到五個 skills 中，因此舊手冊不再是操作入口。

若要清理舊手冊與舊截圖，請先看 `maintenance/documentation_cleanup_candidates_2026-05-24.md`，逐一確認 exact path；不要使用 recursive、wildcard 或批量刪除。
