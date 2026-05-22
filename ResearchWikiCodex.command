#!/bin/zsh
cd "$(dirname "$0")" || exit 1
python3 tools/research_wiki_codex_shortcut.py
echo ""
echo "ResearchWiki Codex-first command closed. Press Enter to exit."
read _ || true
