# RKF Inbox Capture Workflow

這份流程說明如何把 ChatGPT 對話、網頁 clip、DOI、URL、想法與暫存片段先放進
RKF inbox，再用保守規則連回 `SourceRecord`、paper page 或其他 wiki object。

## 核心原則

- 所有外部材料先進 `knowledge/inbox/`，不要直接寫成 stable claim。
- Inbox item 可以保留短摘錄、來源 URL、DOI、你的想法與 AI/agent note。
- DOI injection 只做 source identity、paper draft、inbox backlink 與 reading-state 連結。
- `Reader Notes` 放你的想法；`Source-Grounded Notes` 只放來源明確支持的內容。
- `AI/Agent Notes` 和 inbox item 都不能單獨作為 claim evidence。
- 不把完整 article text、整段私人 ChatGPT transcript、PDF、browser capture 或 private path
  存進 public wiki。

## ChatGPT 網頁版怎麼存

短期推薦使用「手選片段 + shared link metadata」：

1. 在 ChatGPT 網頁版開啟對話。
2. 只複製需要保存的片段、DOI、URL 或自己的想法，不複製整段私人 transcript。
3. 如果內容不敏感，可以用 ChatGPT 的 share button 產生
   `https://chatgpt.com/share/...` 連結，作為 `source_url`。
4. 用自然語言請 agent 保存，或使用 CLI：

```bash
python3 tools/rk.py inbox capture "ChatGPT note on aerosol paper" \
  --origin chatgpt-web \
  --source-url "https://chatgpt.com/share/CONVERSATION_ID" \
  --doi "10.1234/example" \
  --clip "Short public-safe excerpt or summary." \
  --reader-note "My idea or project relation."
```

如果不想讓 DOI 連回 paper page，加上：

```bash
--no-inject
```

## DOI Injection 規則

當 inbox item 有 DOI 時，RKF 預設會：

- 建立或更新 `state/sources/*.json` 的 `SourceRecord`。
- 如果沒有 paper page，建立 conservative paper draft。
- 如果已有 paper page，只追加 inbox backlink，不重寫既有人工筆記。
- 在 paper reading ledger 記錄 `inbox-injection` event。

RKF 不會因為 inbox item 裡出現某個說法，就自動建立 stable claim 或 trusted
synthesis。Claim promotion 仍需要 locator-backed evidence、既有 supported RKF page，
或 annotated/trusted human feedback。

## 之後可擴充的入口

- ChatGPT data export ZIP importer：適合批次匯入舊對話，但必須先進 inbox review。
- Browser/extension clipper：適合從網頁選取段落後直接呼叫 `rk inbox capture`。
- 跨專案 agent handoff：其他專案只需把 short clip、URL、DOI 與 reader note 傳回 RKF
  inbox，不需要知道 RKF 內部 page routing。

## 安全提醒

ChatGPT shared link 沒有細緻權限控管；任何拿到連結的人都可能看到該 conversation
snapshot。只在非敏感內容上使用 shared link，並把真正需要長期保存的內容整理成短摘錄、
summary 或 reader note。
