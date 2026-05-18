#!/usr/bin/env bash
set -euo pipefail

REPO_PATH="${1:-$(cd "$(dirname "$0")/.." && pwd)}"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-1800}"
LABEL="${LABEL:-com.researchwiki.gitautosync}"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PYTHON_BIN="${PYTHON_BIN:-python3}"

mkdir -p "$HOME/Library/LaunchAgents"

cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PYTHON_BIN</string>
    <string>$REPO_PATH/tools/git_auto_sync.py</string>
    <string>sync</string>
  </array>
  <key>WorkingDirectory</key>
  <string>$REPO_PATH</string>
  <key>StartInterval</key>
  <integer>$INTERVAL_SECONDS</integer>
  <key>RunAtLoad</key>
  <true/>
  <key>StandardOutPath</key>
  <string>$REPO_PATH/.git/auto-sync.out.log</string>
  <key>StandardErrorPath</key>
  <string>$REPO_PATH/.git/auto-sync.err.log</string>
</dict>
</plist>
PLIST

launchctl unload "$PLIST" >/dev/null 2>&1 || true
launchctl load "$PLIST"
echo "Installed launchd agent '$LABEL' for $REPO_PATH every $INTERVAL_SECONDS seconds."
