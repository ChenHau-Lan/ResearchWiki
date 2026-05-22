#!/bin/zsh
cd "$(dirname "$0")" || exit 1
python3 tools/init_research_wiki.py
echo ""
echo "InitializeResearchWiki closed. Press Enter to exit."
read _ || true
