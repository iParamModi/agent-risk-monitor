#!/usr/bin/env bash
# Download R-Judge and ATBench into data/raw/ exactly as received (DATASET.md section 2).
# data/raw/ is read-only after download and never committed (STRUCTURE.md section 6).
set -euo pipefail
cd "$(dirname "$0")/.."

RAW=data/raw
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# ---- R-Judge (GitHub, no licence file: research use only, never commit) ----
RJ_URL=https://github.com/Lordog/R-Judge.git
mkdir -p "$RAW/r_judge"
if [ ! -d "$RAW/r_judge/.git" ]; then
  git clone --depth 1 "$RJ_URL" "$RAW/r_judge"
fi
{
  echo "source: $RJ_URL"
  echo "commit: $(git -C "$RAW/r_judge" rev-parse HEAD)"
  echo "downloaded_utc: $NOW"
  echo "licence: none in repository (research use only, do not redistribute)"
} > "$RAW/r_judge/VERSION.txt"

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

echo "R-Judge: $(find "$RAW/r_judge/data" -name '*.json' | wc -l) JSON files"
echo "ATBench: $(du -h "$RAW/atbench/ATBench/test.json" | cut -f1)"
