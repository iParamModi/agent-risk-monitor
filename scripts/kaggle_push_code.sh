#!/usr/bin/env bash
# Uploads the committed repo (git archive HEAD: no .env, no AgentRisk, no model weights) as the PRIVATE
# Kaggle dataset <KAGGLE_USERNAME>/agent-risk-code, which the Kaggle jobs in kaggle/ read.
#   bash scripts/kaggle_push_code.sh "message"     (first run creates the dataset, later runs add a version)
# Needs KAGGLE_USERNAME and KAGGLE_API_TOKEN (in .env, never committed) and the kaggle CLI.
set -euo pipefail
cd "$(dirname "$0")/.."
set -a; . ./.env; set +a
MSG="${1:-update code}"
GITDIR=$(git rev-parse --git-dir)
if [ -d "$GITDIR/rebase-merge" ] || [ -d "$GITDIR/rebase-apply" ] || [ -f "$GITDIR/MERGE_HEAD" ]; then
  echo "refusing: a rebase or merge is in progress, HEAD is not your commit" >&2; exit 1
fi
git fetch -q origin
if [ -n "$(git log origin/main..HEAD --oneline)" ] || [ -n "$(git log HEAD..origin/main --oneline)" ]; then
  echo "refusing: HEAD differs from origin/main; pull and push first so Kaggle runs the code on GitHub" >&2; exit 1
fi
echo "uploading code at $(git log -1 --format='%h %s')"
DIR=$(mktemp -d)
git archive --format=tar.gz -o "$DIR/code.tar.gz" HEAD
if git archive HEAD | tar -t | grep -E '(^|/)\.env$|agentrisk\.jsonl$|^data/raw/agentrisk/|^data/external/agentrisk/|\.gguf$|\.safetensors$'; then
  echo "refusing: secret, AgentRisk data or weights in the archive" >&2; exit 1
fi
cat > "$DIR/dataset-metadata.json" <<EOF
{"title": "agent-risk-code", "id": "${KAGGLE_USERNAME}/agent-risk-code", "licenses": [{"name": "other"}]}
EOF
if kaggle datasets status "${KAGGLE_USERNAME}/agent-risk-code" >/dev/null 2>&1; then
  kaggle datasets version -p "$DIR" -m "$MSG"
else
  kaggle datasets create -p "$DIR"          # private by default
fi
rm -rf "$DIR"
