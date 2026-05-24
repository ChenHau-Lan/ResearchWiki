# Research Wiki 全量匯入圖文教學（Legacy）

[English](research_wiki_full_ingest_walkthrough.en.md)

這份 v1 walkthrough 已被 v2 的 [Skill-first 圖文快速開始](research_wiki_skill_first_quickstart.zh-TW.md) 取代。

保留這個檔案只為了讓舊連結不斷裂。請不要再依照舊版 command option numbers 操作；Research Wiki v2 的正式入口是 pipeline skills + modes：

```text
source-intake -> paper-ingest -> knowledge-workbench -> synthesis-research -> wiki-lint
```

## 重要修正：Fan-out 不再是一般下一步

舊版第 8 段把 fan-out apply 寫得太像例行流程。v2 的正確做法是：

1. 先使用 `synthesis-research/fanout-review` 建立 candidate 或 review proposal。
2. 人工檢查 target pages、supported/challenged claims、confidence、counter-evidence 與 supersession risk。
3. 只有明確批准的 candidate，才可使用 `synthesis-research/apply-approved-fanout`。

`apply-approved-fanout` 是進階寫入 mode，不是 beginner workflow 的預設步驟。

## 請改讀

- [Skill-first 圖文快速開始](research_wiki_skill_first_quickstart.zh-TW.md)
- [使用指南](../../USER_GUIDE.zh-TW.md)
- [Pipeline Architecture](../guides/research_wiki_pipeline_architecture.zh-TW.md)
