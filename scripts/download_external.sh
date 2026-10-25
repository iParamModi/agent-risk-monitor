#!/usr/bin/env bash
# Download R-Judge and ATBench into data/raw/ exactly as received (DATASET.md section 2).
# data/raw/ is read-only after download and never committed (STRUCTURE.md section 6).
set -euo pipefail
cd "$(dirname "$0")/.."

RAW=data/raw
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ---- R-Judge (GitHub, no licence file: research use only, keep our repo private) ----
RJ_URL=https://github.com/Lordog/R-Judge.git
if [ ! -f "$RAW/r_judge/VERSION.txt" ]; then
  TMP=$(mktemp -d)
  git clone --depth 1 "$RJ_URL" "$TMP/r_judge"
  RJ_COMMIT=$(git -C "$TMP/r_judge" rev-parse HEAD)
  # Drop the clone's .git so the files commit as plain files, not a submodule link.
  rm -rf "$TMP/r_judge/.git"
  mkdir -p "$RAW/r_judge"
  cp -r "$TMP/r_judge/." "$RAW/r_judge/"
  rm -rf "$TMP"
  {
    echo "source: $RJ_URL"
    echo "commit: $RJ_COMMIT"
    echo "downloaded_utc: $NOW"
    echo "licence: none in repository (research use only, do not redistribute)"
  } > "$RAW/r_judge/VERSION.txt"
fi

# ---- ATBench (Hugging Face, Apache-2.0) ----
ATB_REPO=AI45Research/ATBench
ATB_REV=${ATB_REV:-$(curl -sf "https://huggingface.co/api/datasets/$ATB_REPO" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['sha'])")}
mkdir -p "$RAW/atbench/ATBench"
# Only the ATBench config (1,000 trajectories); ATBench500 is an older release, do not mix.
curl -fL --retry 3 -o "$RAW/atbench/ATBench/test.json" \
  "https://huggingface.co/datasets/$ATB_REPO/resolve/$ATB_REV/ATBench/test.json"
curl -fL --retry 3 -o "$RAW/atbench/README.md" \
  "https://huggingface.co/datasets/$ATB_REPO/resolve/$ATB_REV/README.md"
{
  echo "source: https://huggingface.co/datasets/$ATB_REPO (config ATBench, file ATBench/test.json)"
  echo "revision: $ATB_REV"
  echo "sha256: $(sha256sum "$RAW/atbench/ATBench/test.json" | cut -d' ' -f1)"
  echo "downloaded_utc: $NOW"
  echo "licence: apache-2.0"
} > "$RAW/atbench/VERSION.txt"

# ---- AgentRisk (SemEval shared task, Hugging Face; no licence stated: never commit, see .gitignore) ----
AR_REPO=AgentRisk/agentrisk-data-2027
AR_REV=${AR_REV:-bc7cbf702846e53ecbb31abcdb387ae4ec9f9392}    # checked 2026-10-25; change only on purpose
mkdir -p "$RAW/agentrisk/data" "$RAW/agentrisk/metadata"
for f in data/train.jsonl data/dev.jsonl metadata/split_manifest.jsonl README.md; do
  curl -fL --retry 3 -o "$RAW/agentrisk/$f" "https://huggingface.co/datasets/$AR_REPO/resolve/$AR_REV/$f"
done
{
  echo "source: https://huggingface.co/datasets/$AR_REPO"
  echo "revision: $AR_REV"
  for f in data/train.jsonl data/dev.jsonl metadata/split_manifest.jsonl; do
    echo "sha256 $f: $(sha256sum "$RAW/agentrisk/$f" | cut -d' ' -f1)"
  done
  echo "downloaded_utc: $NOW"
  echo "licence: none stated (shared-task data; do not redistribute)"
} > "$RAW/agentrisk/VERSION.txt"

echo "R-Judge: $(find "$RAW/r_judge/data" -name '*.json' | wc -l) JSON files"
echo "AgentRisk: $(cat "$RAW/agentrisk/data/train.jsonl" "$RAW/agentrisk/data/dev.jsonl" | wc -l) items"
echo "ATBench: $(du -h "$RAW/atbench/ATBench/test.json" | cut -f1)"
