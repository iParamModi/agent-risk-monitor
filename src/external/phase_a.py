"""Phase A external training list: the records the monitor learns risk_label / risk_type from.

Run: python -m src.external.phase_a   (after src.external.agentrisk)
Start: R-Judge and ATBench 300-record train samples (R12.2) + all AgentRisk train records (R12.5).
Then, per source (Meet, 2026-10-26, from the EDA notebook: the pool was 53% PRIVACY_LEAKAGE):
- UNSAFE PRIVACY_LEAKAGE is randomly downsampled to at most PRIVACY_CAP
- SAFE is randomly downsampled to the source's new UNSAFE count, so each source stays 50/50 at most;
  AgentRisk drops replies to the user (meta.flags reply_to_user, a SAFE shortcut) first
The 300-samples are not changed: they still mark which records needed a human risk type.
R-Judge risk types come from the finished re-check (map_risk.load_human_types), the same values
map_risk writes into r_judge.jsonl.
Writes data/external/splits/phase_a_train.txt and data/external/phase_a_report.json.
"""
import random
import sys
from collections import Counter

from src.common.io import REPO_ROOT, read_jsonl, write_json
from src.external.map_risk import load_human_types

EXT_DIR = REPO_ROOT / "data" / "external"
SPLIT_DIR = EXT_DIR / "splits"
OUT = SPLIT_DIR / "phase_a_train.txt"
REPORT = EXT_DIR / "phase_a_report.json"
PRIVACY_CAP = 60
SEED = 20261026
SOURCES = ("r_judge", "atbench", "agentrisk")


def is_reply(rec: dict) -> bool:
    return "reply_to_user" in (rec["meta"].get("flags") or ())


def downsample(records: list[dict], n: int, rng: random.Random, drop_first=None) -> list[dict]:
    """n records at random; records for which drop_first(rec) is true are only taken when the rest run out."""
    if n >= len(records):
        return list(records)
    ordered = sorted(records, key=lambda r: r["record_id"])
    if drop_first is None:
        return rng.sample(ordered, n)
    keep = [r for r in ordered if not drop_first(r)]
    if n <= len(keep):
        return rng.sample(keep, n)
    return keep + rng.sample([r for r in ordered if drop_first(r)], n - len(keep))


def balance(records: list[dict], risk_type, rng: random.Random, cap: int = PRIVACY_CAP, drop_first=None) -> list[dict]:
    """Cap UNSAFE PRIVACY_LEAKAGE at `cap`, then cut SAFE to the UNSAFE count."""
    unsafe = [r for r in records if r["gold"]["risk_label"] == "UNSAFE"]
    privacy = [r for r in unsafe if risk_type(r) == "PRIVACY_LEAKAGE"]
    unsafe = [r for r in unsafe if risk_type(r) != "PRIVACY_LEAKAGE"] + downsample(privacy, cap, rng)
    safe = downsample([r for r in records if r["gold"]["risk_label"] == "SAFE"], len(unsafe), rng, drop_first)
    return sorted(safe + unsafe, key=lambda r: r["record_id"])


def start_pool(name: str) -> list[dict]:
    records = [r for r in read_jsonl(EXT_DIR / f"{name}.jsonl") if r["split"] == "train"]
    sample = SPLIT_DIR / f"{name}_train_sample300.txt"
    if sample.exists():
        ids = set(sample.read_text(encoding="utf-8").split())
        records = [r for r in records if r["record_id"] in ids]
    return records


def counts(records: list[dict], risk_type) -> dict:
    unsafe = [r for r in records if r["gold"]["risk_label"] == "UNSAFE"]
    return {"records": len(records), "safe": len(records) - len(unsafe), "unsafe": len(unsafe),
            "safe_replies": sum(is_reply(r) for r in records if r["gold"]["risk_label"] == "SAFE"),
            "risk_type": dict(Counter(risk_type(r) for r in unsafe).most_common())}


def build() -> tuple[list[dict], dict]:
    human = load_human_types()
    risk_type = lambda r: human.get(r["record_id"]) if r["source"] == "r_judge" else r["gold"]["risk_type"]  # noqa: E731
    chosen, report = [], {"privacy_cap": PRIVACY_CAP, "seed": SEED, "sources": {}}
    for i, name in enumerate(SOURCES):
        path = EXT_DIR / f"{name}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; run `make external`")
        pool = start_pool(name)
        missing = [r["record_id"] for r in pool if r["gold"]["risk_label"] == "UNSAFE" and not risk_type(r)]
        if missing:
            raise ValueError(f"{name}: UNSAFE records without a risk type: {missing[:5]}")
        picked = balance(pool, risk_type, random.Random(SEED + i), drop_first=is_reply)
        report["sources"][name] = {"before": counts(pool, risk_type), "after": counts(picked, risk_type)}
        chosen += picked
    report["total"] = counts(chosen, risk_type)
    return chosen, report


def main() -> int:
    chosen, report = build()
    OUT.write_text("".join(r["record_id"] + "\n" for r in chosen), encoding="utf-8")
    write_json(REPORT, report)
    for name, part in report["sources"].items():
        b, a = part["before"], part["after"]
        print(f"{name}: {b['records']} -> {a['records']} ({a['safe']} SAFE / {a['unsafe']} UNSAFE)")
    t = report["total"]
    print(f"phase A: {t['records']} records ({t['safe']} SAFE / {t['unsafe']} UNSAFE); UNSAFE types: "
          + ", ".join(f"{k} {v} ({100 * v / t['unsafe']:.0f}%)" for k, v in t["risk_type"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
