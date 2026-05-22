# 支援與 Issue 回報

Research Wiki 採用 privacy-safe issue 回報。

## 產生 Issue 草稿

執行：

```bash
python3 tools/support_report.py --issue-url
```

工具會寫入 `maintenance/support_report.md`，並產生 GitHub issue 預填連結。它不會自動送出 issue。

## 送出前檢查

請確認 issue 內容沒有：

- private PDF
- 文章全文
- 本機 home-directory 路徑
- Codex logs
- 敏感 DOI 清單或個人研究狀態

工具會自動遮蔽常見私密資料，但最後仍需要人工確認。

## 建議 Labels

- `new-user-test`
- `install`
- `core-contract`
- `command-ui`
- `privacy`
- `needs-triage`
