# RKF v1 快速開始

> Status: Current
> Applies to: RKF v1.2 target（尚未 release；latest tag v1.1.0）
> Last verified: 2026-07-15

## 1. 選擇 installation profile

### Local core

```bash
python3 tools/bootstrap_rkf.py
python3 tools/bootstrap_rkf.py --apply
python3 tools/check_install.py --profile core --strict --json
```

這只初始化 local workspace。成功時會回傳 `"profile": "core"` 與
`"ready": true`；缺少 Codex connector 仍屬 optional warning。

### Codex integration

以相同 connector request 先 preview、再 apply，接著驗證 Codex-specific profile
並 resolve 已安裝的 connector：

```bash
python3 tools/bootstrap_rkf.py --install-connector
python3 tools/bootstrap_rkf.py --apply --install-connector
python3 tools/check_install.py --profile codex --strict --json
python3 tools/rkf_auto_connect.py resolve
```

在此 profile 中，缺少或過期的 connector／skill 會讓 strict check 失敗。
無論使用哪個 profile，PDF、article text、secret 與 private storage path 都不進
committed knowledge。

## 2. 連接研究專案

先 preview，再明確 apply `connect-project`：

```bash
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project
python3 tools/rkf_auto_connect.py connect-project /path/to/research-project --apply
```

它會建立包含隨機穩定 `project_id` 的 v2 `.rkf-connect.toml` 與輕量 `RKF/`
bridge；不複製第二份 wiki 或 private index。

## 3. 每個 task 明確啟動

新 task 預設 OFF。說「啟動 RKF」後再 validate connection。每次 task 有唯一
`activation_id`；action lineage 會遮蔽路徑並保持 idempotent。完成後說「停用 RKF」。

## 4. 執行隔離的第一個閉環

```bash
python3 tools/demo_quickstart.py --check
```

此指令使用兩篇 temporary synthetic papers，不使用 network、global connector、PDF
或使用者資料。它會驗證 activation、五條 workflow、deactivation，以及只有 exact
locator Evidence 才能支援正式 claim 的規則。

## 5. 以真實來源使用五條 workflow

- Add DOI／URL／PDF pointer／note。
- Ask 有來源邊界的問題；沒有 locator 的 context 會明確標示為不可支援 claim。
- Read 時可先記錄 FindingDraft，不必立即中斷去找 locator；補成 exact 後才能提升
  為 Evidence。原本 direct exact-locator Evidence capture 仍可使用。
- Compare & Synthesize Claim；`verified` 必須有人為確認。
- Review 缺 locator、待確認 evidence、矛盾與下一步。

精確範圍見 `MODE_REGISTRY.md` 與 `docs/V1_SCOPE_INVENTORY.md`。
