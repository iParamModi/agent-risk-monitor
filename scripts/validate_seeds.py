"""Validate seed specs against configs/schemas/seed.schema.json.

Usage:
    python -m scripts.validate_seeds                # all seeds in data/seeds/{in_domain,ood}
    python -m scripts.validate_seeds path/to/one.yaml ...

Checks, beyond the JSON schema:
- the file name matches the seed_id
- seed_id domain/type agree with the domain/case_type fields

Exits non-zero if any seed fails. DRAFT (Step 8); gold_policy_ids are not
checked against the policy store yet (policies come in Step 5).
"""
import sys
from pathlib import Path

import yaml

from src.common.io import REPO_ROOT
from src.common.schema import schema_errors

SEED_DIRS = [REPO_ROOT / "data" / "seeds" / "in_domain",
             REPO_ROOT / "data" / "seeds" / "ood"]


def _targets(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(a) for a in argv]
    files: list[Path] = []
    for d in SEED_DIRS:
        files.extend(sorted(d.glob("*.yaml")))
    return files


def check_file(path: Path) -> list[str]:
    try:
        spec = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as e:
        return [f"YAML parse error: {e}"]
    if not isinstance(spec, dict):
        return ["top level is not a mapping"]

    errors = schema_errors(spec, "seed")

    seed_id = spec.get("seed_id")
    if seed_id and path.stem != seed_id:
        errors.append(f"file name {path.stem!r} != seed_id {seed_id!r}")
    if isinstance(seed_id, str):
        parts = seed_id.split("-")  # e.g. IND-FILE-T1-001
        if len(parts) == 4:
            _, dom, typ, _ = parts
            if spec.get("domain") and dom != spec["domain"]:
                errors.append(f"seed_id domain {dom!r} != domain field {spec['domain']!r}")
            if spec.get("case_type") and typ != spec["case_type"]:
                errors.append(f"seed_id type {typ!r} != case_type field {spec['case_type']!r}")
    return errors


def main(argv: list[str]) -> int:
    targets = _targets(argv)
    if not targets:
        print("no seed files found")
        return 0
    bad = 0
    for path in targets:
        errs = check_file(path)
        if errs:
            bad += 1
            print(f"FAIL {path}")
            for e in errs:
                print(f"     - {e}")
        else:
            print(f"ok   {path}")
    print(f"\n{len(targets) - bad}/{len(targets)} seeds valid")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
