"""Lists the records in data/records/ that differ from a git commit, and which fields changed.

Run it before `python -m src.data_gen.split --relock`: only the records you meant to change may be listed
(e.g. a required_checks pass may change gold.required_checks and nothing else).

    python scripts/changed_records.py [--ref HEAD]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = ("all_in_domain.jsonl", "all_ood.jsonl")


def by_id(text: str) -> dict[str, dict]:
    return {r["record_id"]: r for r in (json.loads(line) for line in text.splitlines() if line.strip())}


def changed_fields(old: dict, new: dict) -> list[str]:
    """'gold.required_checks', 'visible.trajectory', ...: two levels deep."""
    out = []
    for key in sorted(set(old) | set(new)):
        a, b = old.get(key), new.get(key)
        if a == b:
            continue
        if isinstance(a, dict) and isinstance(b, dict):
            out += [f"{key}.{k}" for k in sorted(set(a) | set(b)) if a.get(k) != b.get(k)]
        else:
            out.append(key)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ref", default="HEAD", help="git commit to compare with (default: the last commit)")
    args = ap.parse_args(argv)
    total = 0
    for name in FILES:
        rel = f"data/records/{name}"
        shown = subprocess.run(["git", "show", f"{args.ref}:{rel}"], cwd=ROOT, capture_output=True, text=True)
        old = by_id(shown.stdout) if shown.returncode == 0 else {}
        new = by_id((ROOT / rel).read_text(encoding="utf-8"))
        for rid in sorted(new.keys() - old.keys()):
            print(f"added    {rid}")
        for rid in sorted(old.keys() - new.keys()):
            print(f"removed  {rid}")
        changed = sorted(rid for rid in new.keys() & old.keys() if new[rid] != old[rid])
        for rid in changed:
            print(f"changed  {rid} [{new[rid]['split']}]: {', '.join(changed_fields(old[rid], new[rid]))}")
        total += len(changed) + len(new.keys() ^ old.keys())
    print(f"{total} records differ from {args.ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
