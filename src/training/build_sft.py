"""Makes the SFT files (PLAN Step 16). Phase A has only kind (c): risk examples from the external records.

    python -m src.training.build_sft                 -> data/training/sft_train.jsonl, sft_val.jsonl, stats.json

- train: the records in data/external/splits/phase_a_train.txt (src.external.phase_a); val: every external
  val record
- input: exactly the monitor's prompt (prompt_builder.build_risk_prompt, as chat messages), so training and
  inference see the same text
- target: built by code from the gold fields (never by an LLM), in the parser's RISK format
Our own records (kinds a and b) are added when Step 9 has made them. The SFT files hold record text, so they
are git-ignored (AgentRisk has no licence). Length filtering happens in train_lora.py, with the real tokenizer.
"""
import json
import sys
from collections import Counter

from src.common.io import REPO_ROOT, read_jsonl, write_json, write_jsonl
from src.monitor.prompt_builder import RISK_TEMPLATE, as_messages, build_risk_prompt

EXT = REPO_ROOT / "data" / "external"
OUT = REPO_ROOT / "data" / "training"
SOURCES = ("r_judge", "atbench", "agentrisk")


def risk_target(gold: dict) -> str:
    """The answer the model must give, in the RISK format of prompts/monitor_risk_v1.txt."""
    if gold["risk_label"] not in ("SAFE", "UNSAFE") or not gold["risk_type"]:
        raise ValueError(f"no final label: {gold['risk_label']!r} / {gold['risk_type']!r}")
    return json.dumps({"type": "RISK", "risk_label": gold["risk_label"], "risk_type": gold["risk_type"]})


def example(rec: dict) -> dict:
    return {"record_id": rec["record_id"], "source": rec["source"], "kind": "risk",
            "messages": as_messages(build_risk_prompt(rec["visible"])), "target": risk_target(rec["gold"])}


def build(train_ids: set[str]) -> tuple[list[dict], list[dict], dict]:
    train, val = [], []
    for name in SOURCES:
        for rec in read_jsonl(EXT / f"{name}.jsonl"):
            if rec["record_id"] in train_ids:
                train.append(example(rec))
            elif rec["split"] == "val":
                val.append(example(rec))
    missing = train_ids - {e["record_id"] for e in train}
    if missing:
        raise ValueError(f"{len(missing)} Phase A ids not found, e.g. {sorted(missing)[:3]}")

    def counts(rows):
        return {"examples": len(rows), "by_source": dict(Counter(r["source"] for r in rows)),
                "by_target": dict(Counter(r["target"] for r in rows).most_common())}
    stats = {"kind": "risk (c) only, Phase A", "prompt": RISK_TEMPLATE, "train": counts(train), "val": counts(val)}
    return train, val, stats


def main() -> int:
    ids = set((EXT / "splits" / "phase_a_train.txt").read_text(encoding="utf-8").split())
    train, val, stats = build(ids)
    write_jsonl(OUT / "sft_train.jsonl", train)
    write_jsonl(OUT / "sft_val.jsonl", val)
    write_json(OUT / "stats.json", stats)
    print(f"sft_train {len(train)}, sft_val {len(val)} -> {OUT.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
