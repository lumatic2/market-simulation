#!/usr/bin/env bash
# install.sh — deploy market-simulation skill to ~/.claude/skills/market-simulation/
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
TARGET="$HOME/.claude/skills/market-simulation"
mkdir -p "$TARGET"
cp "$REPO_ROOT/SKILL.md" "$TARGET/SKILL.md"
echo "deployed: $TARGET/SKILL.md  (source: $REPO_ROOT/SKILL.md)"

