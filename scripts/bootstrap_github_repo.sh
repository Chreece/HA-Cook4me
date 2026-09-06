#!/usr/bin/env bash
set -euo pipefail
REPO="Chreece/HA-Cook4me"
DESCRIPTION="Home Assistant integration for KRUPS/Tefal Cook4Me with cloud monitoring, Recipe Hub, pantry/diet recommendations and AI-assisted cook-along recipes."

command -v gh >/dev/null || { echo "GitHub CLI (gh) is required" >&2; exit 2; }
if ! git rev-parse --git-dir >/dev/null 2>&1; then
  git init
  git branch -M main
fi
git add .
if ! git diff --cached --quiet; then
  git commit -m "HA-Cook4me $(python scripts/version.py validate)"
fi
if ! gh repo view "$REPO" >/dev/null 2>&1; then
  gh repo create "$REPO" --public --source=. --remote=origin --push --description "$DESCRIPTION"
else
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "git@github.com:${REPO}.git"
  git push -u origin main
fi
gh repo edit "$REPO" --description "$DESCRIPTION" --enable-issues \
  --add-topic home-assistant \
  --add-topic homeassistant \
  --add-topic hacs \
  --add-topic custom-integration \
  --add-topic cook4me \
  --add-topic cookeo \
  --add-topic krups \
  --add-topic tefal \
  --add-topic recipe \
  --add-topic smart-home
VERSION="$(python scripts/version.py validate)"
if ! git rev-parse "$VERSION" >/dev/null 2>&1; then
  git tag "$VERSION"
fi
git push origin "$VERSION"
echo "Repository bootstrapped: https://github.com/$REPO"
