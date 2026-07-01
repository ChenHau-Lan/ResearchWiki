# Open-Source Template Scan For RKF

Date: 2026-06-22

## Scope

本次掃描目標不是改用外部專案，而是尋找可借鏡的開源 wiki / PKM / digital garden
模式，改善 RKF 的 v0 個人化 LLM literature wiki。掃描來源以公開 repository 與官方
README 為主。

## Shortlist

| Project | Observed pattern | RKF decision |
|---|---|---|
| Quartz | Markdown digital garden publishing layer；把 Markdown 內容轉成網站 | 可借鏡 publication/export layer，但不把 publication 變成 paper intake 的核心入口 |
| Dendron | Local-first Markdown PKM；schema/template、hierarchy、vault separation | 借鏡 schema-like template、consistent hierarchy、vault separation；不依賴 Dendron runtime |
| Foam | VS Code-based PKM；research notes、rediscoverable notes、graph/link tooling | 借鏡 editor-friendly Markdown 與 graph/link workflow；RKF 保持 editor-agnostic |
| Logseq | Privacy-first open-source knowledge platform；支援 Markdown/Org-mode；DB/test graph 分流 | 借鏡 live graph/test graph 分離與 local-first posture；不導入 Logseq DB |

## Design Lessons For RKF

- Keep Markdown as the durable object. External tools can edit, publish, or index
  it, but RKF should not hide literature state behind a UI-only database.
- Keep personal/live wiki roots separate from repo fixtures. Dendron vaults and
  Logseq test graphs both support this separation pattern.
- Use templates and section contracts before adding a database. Dendron-style
  schema/templates map well to RKF paper/synthesis/topic templates.
- Graph and backlinks are useful as retrieval aids, but they should not replace
  evidence maturity, locator checks, or reading ledgers.
- Publication/export should be optional. Quartz is useful later if RKF needs a
  public digital garden, but the current workflow should stay reading-first.

## Adopt Now

- Markdown-first paper page sections.
- Thin CLI backend for repeatable generation, lint, graph, index, queue, and
  automation.
- Repo/live-data separation through `rkf.workspace.toml`.
- Test/fixture data stays in repo; personal wiki/raw data stays external.

## Defer

- Hosted UI or app shell.
- Database-backed graph rewrite.
- Static-site publication layer.
- Direct dependency on a PKM tool runtime.

## Sources Checked

- Quartz repository: https://github.com/jackyzha0/quartz
- Dendron repository: https://github.com/dendronhq/dendron
- Foam repository: https://github.com/foambubble/foam
- Logseq repository: https://github.com/logseq/logseq
