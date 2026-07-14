# RKF v1 快速開始

## 1. 初始化中央 RKF

```bash
python3 tools/bootstrap_rkf.py preview
python3 tools/bootstrap_rkf.py apply
python3 tools/check_install.py
```

PDF、article text、secret 與 private storage path 不進 committed knowledge。

## 2. 連接研究專案

先 preview，再明確 apply `connect-project`。它會建立包含隨機穩定 `project_id` 的 v2
`.rkf-connect.toml` 與輕量 `RKF/` bridge；不複製第二份 wiki 或 semantic index。

## 3. 每個 task 明確啟動

新 task 預設 OFF。說「啟動 RKF」後再 validate connection。每次 task 有唯一
`activation_id`；action lineage 會遮蔽路徑並保持 idempotent。完成後說「停用 RKF」。

## 4. 完成第一個 paper 閉環

- Add DOI／URL／PDF pointer／note。
- Ask 有來源邊界的問題。
- Read 並記錄 exact locator Evidence。
- Compare & Synthesize Claim；`verified` 必須有人為確認。
- Review 缺 locator、待確認 evidence、矛盾與下一步。

Optional provider 可取得全文、做 appraisal 或增加 semantic retrieval，但不是必要依賴，
也不能自動提高 trust。

精確範圍見 `MODE_REGISTRY.md` 與 `docs/V1_SCOPE_INVENTORY.md`。
