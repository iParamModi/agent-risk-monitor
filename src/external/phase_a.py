"""Phase A external training list: the records the monitor learns risk_label / risk_type from.

Run: python -m src.external.phase_a   (after src.external.agentrisk)
From the FULL train split of each source (Meet, 2026-10-26: the 300-samples of R12.2 were set when
less data was expected; they stay as they are and still mark which records needed a human type):
- UNSAFE: every record of every risk type, except CAPPED_TYPE (PRIVACY_LEAKAGE), which is randomly cut
  to the size of the largest other type (all sources together), split as evenly as possible over the
  sources; inside a source, AgentRisk privacy records are spread evenly over risk_cause
- no size limit per source (Meet: ATBench may pass 450 so every source stays 50/50)
- SAFE: randomly cut to the source's UNSAFE count, so every source is 50/50; AgentRisk drops replies to
  the user (meta.flags reply_to_user, a SAFE shortcut) first
- UNSAFE records without a final risk type are never used: R-Judge records the re-check did not cover,
  ATBench mixed-harm records without a per-record label (R3.6)
R-Judge risk types come from the finished re-check (map_risk.load_human_types), the same values
map_risk writes into r_judge.jsonl.
Writes data/external/splits/phase_a_train.txt and data/external/phase_a_report.json.
"""
import random
import sys
from collections import Counter

from src.common.io import REPO_ROOT, read_jsonl, write_json
from src.external.map_risk import load_human_types
from src.external.sample import atbench_type_stratum, even_allocation, stratified_sample

EXT_DIR = REPO_ROOT / "data" / "external"
SPLIT_DIR = EXT_DIR / "splits"
OUT = SPLIT_DIR / "phase_a_train.txt"
REPORT = EXT_DIR / "phase_a_report.json"
CAPPED_TYPE = "PRIVACY_LEAKAGE"    # the only type that is downsampled
SEED = 20261026
SOURCES = ("r_judge", "atbench", "agentrisk")
CAUSE_SOURCES = {"agentrisk"}     # sources whose records carry a risk_cause


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


def pick_unsafe(by_source: dict[str, list[dict]], risk_type, rng: random.Random, capped: str = CAPPED_TYPE,
                cause_sources=CAUSE_SOURCES) -> tuple[dict[str, list[dict]], int]:
    """All records of every type but `capped`, which is cut to the largest other type's size, spread evenly
    over the sources (and over causes inside a cause source). Returns (chosen per source, cap)."""
    sizes = Counter(risk_type(r) for rs in by_source.values() for r in rs)
    cap = max((n for t, n in sizes.items() if t != capped), default=0)
    chosen = {s: [] for s in by_source}
    for t in sorted(sizes):
        pools = {s: [r for r in rs if risk_type(r) == t] for s, rs in by_source.items()}
        pools = {s: p for s, p in pools.items() if p}
        n = min(cap, sizes[t]) if t == capped else sizes[t]
        take = even_allocation({s: len(p) for s, p in pools.items()}, n)
        for s, n in take.items():
            stratum = (lambda r: r["gold"]["risk_cause"]) if s in cause_sources else (lambda r: "all")
            chosen[s] += stratified_sample(pools[s], n, stratum, rng)
    return chosen, cap


def risk_type_fn():
    human, atbench = load_human_types(), atbench_type_stratum()

    def risk_type(rec: dict) -> str | None:
        if rec["source"] == "r_judge":
            return human.get(rec["record_id"])
        if rec["source"] == "atbench":
            return atbench(rec)
        return rec["gold"]["risk_type"]
    return risk_type


def counts(records: list[dict], risk_type) -> dict:
    unsafe = [r for r in records if r["gold"]["risk_label"] == "UNSAFE"]
    out = {"records": len(records), "safe": len(records) - len(unsafe), "unsafe": len(unsafe),
           "safe_replies": sum(is_reply(r) for r in records if r["gold"]["risk_label"] == "SAFE"),
           "risk_type": dict(Counter(risk_type(r) for r in unsafe).most_common())}
    causes = Counter(r["gold"]["risk_cause"] for r in unsafe if r["gold"]["risk_cause"])
    if causes:
        out["risk_cause"] = dict(causes.most_common())
    return out


def build() -> tuple[list[dict], dict]:
    risk_type = risk_type_fn()
    train = {}
    for name in SOURCES:
        path = EXT_DIR / f"{name}.jsonl"
        if not path.exists():
            raise FileNotFoundError(f"{path} missing; run `make external`")
        train[name] = [r for r in read_jsonl(path) if r["split"] == "train"]
    rng = random.Random(SEED)
    typed = {s: [r for r in rs if r["gold"]["risk_label"] == "UNSAFE" and risk_type(r)] for s, rs in train.items()}
    unsafe, cap = pick_unsafe(typed, risk_type, rng)
    chosen, report = [], {"capped_type": CAPPED_TYPE, "cap": cap, "seed": SEED, "sources": {}}
    for name in SOURCES:
        safe = downsample([r for r in train[name] if r["gold"]["risk_label"] == "SAFE"], len(unsafe[name]), rng,
                          drop_first=is_reply)
        picked = sorted(safe + unsafe[name], key=lambda r: r["record_id"])
        untyped = sum(r["gold"]["risk_label"] == "UNSAFE" for r in train[name]) - len(typed[name])
        report["sources"][name] = {"train_split": counts(train[name], risk_type), "unsafe_without_final_type": untyped,
                                   "phase_a": counts(picked, risk_type)}
        chosen += picked
    report["total"] = counts(chosen, risk_type)
    return chosen, report


def main() -> int:
    chosen, report = build()
    OUT.write_text("".join(r["record_id"] + "\n" for r in chosen), encoding="utf-8")
    write_json(REPORT, report)
    for name, part in report["sources"].items():
        b, a = part["train_split"], part["phase_a"]
        print(f"{name}: train {b['records']} -> {a['records']} ({a['safe']} SAFE / {a['unsafe']} UNSAFE)")
    t = report["total"]
    print(f"phase A: {t['records']} records ({t['safe']} SAFE / {t['unsafe']} UNSAFE); {CAPPED_TYPE} capped at {report['cap']}")
    print("  risk_type: " + ", ".join(f"{k} {v} ({100 * v / t['unsafe']:.0f}%)" for k, v in t["risk_type"].items()))
    print("  risk_cause (AgentRisk): " + ", ".join(f"{k} {v}" for k, v in t.get("risk_cause", {}).items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
