#!/usr/bin/env bash
# Sync from your fork: pull in new/changed files from origin, but keep YOUR
# version for files you've actually edited (your trace).
#
# Run from repo root: ./sync_from_fork.sh

set -e
cd "$(dirname "$0")"

# Files you changed (your trace) — keep these as-is
MY_TRACE_FILES=(
  "04_deployment/digitalocean/shinypy/requirements.txt"
)

# If untracked workflow files would be overwritten by merge, back them up
for f in .github/workflows/deploy-plumber.yml .github/workflows/deploy-shinypy.yml .github/workflows/deploy-shinyr.yml; do
  if [[ -f "$f" ]] && ! git ls-files --error-unmatch "$f" &>/dev/null; then
    mkdir -p .github/workflows_backup
    mv "$f" .github/workflows_backup/ 2>/dev/null || true
  fi
done

echo "Fetching from origin (your fork)..."
git fetch origin

echo "Merging origin/main..."
if git merge origin/main -m "Sync from fork (keep local changes for my files)"; then
  echo "Merge completed with no conflicts."
  exit 0
fi

# We have conflicts; keep our version for "my trace" files, take theirs for the rest
echo "Resolving conflicts: keeping your version for your files, taking fork's for others..."
for f in "${MY_TRACE_FILES[@]}"; do
  if git status --short "$f" 2>/dev/null | grep -q .; then
    echo "  Keeping your version: $f"
    git checkout --ours -- "$f"
    git add -- "$f"
  fi
done

# For any remaining conflicted files, take fork's version
for f in $(git diff --name-only --diff-filter=U); do
  echo "  Taking fork's version: $f"
  git checkout --theirs -- "$f"
  git add -- "$f"
done

echo "Completing merge..."
git commit --no-edit
echo "Done. Your branch is now synced with your fork; your edited file(s) were kept."
