#!/usr/bin/env bash
# force_sync.sh — push ~/sow_clean to GitHub SOW repo

set -e

# ensure we’re in the correct folder
cd "$(dirname "$0")"

echo "Pointing origin at SOW.git..."
git remote remove origin   2>/dev/null || true
git remote add origin git@github.com:DurangoDavid/SOW.git

echo "Cleaning index (respect .gitignore)..."
git rm --cached -r .       2>/dev/null || true
git add .

echo "Committing changes..."
git commit --author="David Maxey <dm@gtmharmony.com>" \
           -m "Force sync: clean SOW project" --allow-empty

echo "Force-pushing to origin/main..."
git branch -M main
git push --force origin main

echo "✅ Sync complete."
