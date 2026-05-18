# 雙電腦 GitHub 自動同步

這個 repo 使用 `tools/git_auto_sync.py` 讓 Windows 與 Mac 都能定期和 GitHub 交叉比對，再安全同步。

## 同步原則

- 每次先執行 `git fetch --prune`，比對本機 `HEAD` 與 upstream。
- 若本機有修改，先跑 `tools/wiki_lint.py`，再 `git add -A` 與自動 commit。
- 若遠端較新，使用 `git pull --rebase --autostash` 把本機 commit 接到遠端之後。
- 若本機較新，執行 `git push`。
- 若發生 rebase conflict，腳本會停止，不會覆蓋另一台電腦的內容。
- `raw/` 仍由 `.gitignore` 保持本機化，不會被自動推送。

## 手動交叉比對

在任一台電腦的 repo 目錄執行：

```bash
python tools/git_auto_sync.py status
```

輸出會顯示：

- `local_ahead`: 本機比 GitHub 多幾個 commit。
- `remote_ahead`: GitHub 比本機多幾個 commit。
- `worktree_changes`: 本機是否有尚未 commit 的修改。

## 手動同步

```bash
python tools/git_auto_sync.py sync
```

Mac 若只有 `python3`：

```bash
python3 tools/git_auto_sync.py sync
```

## Windows 自動排程

在 PowerShell 內進入 repo 後執行：

```powershell
.\tools\install_windows_sync_task.ps1 -IntervalMinutes 30
```

這會建立 Windows 工作排程 `ResearchWikiGitAutoSync`，每 30 分鐘同步一次。

如果 Windows 找不到 `python`，請指定 Python 路徑：

```powershell
.\tools\install_windows_sync_task.ps1 -PythonPath "C:\path\to\python.exe" -IntervalMinutes 30
```

## macOS 自動排程

在 Mac 的 repo 目錄執行：

```bash
chmod +x tools/install_macos_sync_launchd.sh
./tools/install_macos_sync_launchd.sh
```

預設每 1800 秒同步一次。要改成 10 分鐘：

```bash
INTERVAL_SECONDS=600 ./tools/install_macos_sync_launchd.sh
```

## 衝突時

如果兩台電腦同時改到同一段內容，腳本會停在 rebase conflict。處理順序：

```bash
git status
```

手動修正衝突檔案後：

```bash
git add <fixed-file>
git rebase --continue
python tools/git_auto_sync.py sync
```

若不確定怎麼合併，先不要 `push`，把 `git status` 與衝突檔案內容貼回來處理。
