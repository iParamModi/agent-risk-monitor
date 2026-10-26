"""Generate the policy store from the seeds (PLAN Step 5).

A policy is a company rule: a policy_id and its visible text. This writes just the two stores,
both from data/seeds/*.yaml via src/policies/seed_extract.py:

  data/policies/policies.jsonl       in-domain rules      {"policy_id", "text"}
  data/policies/policies_ood.jsonl   OOD rules            (reworded in-domain texts + CUST)

Text is normalized to one uniform style (fixes the 16 lowercase / no-stop texts at one point).
Re-run after the seeds change:  python scripts/gen_policy_store.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.common.io import REPO_ROOT, write_jsonl  # noqa: E402
from src.policies.seed_extract import CANON, normalize_text, pick_text, text_candidates  # noqa: E402

OUT = REPO_ROOT / "data" / "policies"

# CUST visible text from the reviewed OOD catalogue (docs/Policy_OOD.md B): the CUST seed notes are
# too free-form to parse reliably. The generator checks every seed-cited CUST id is covered.
CUST_TEXT = {
    "P_CUST_01": "Customer data may be exported only with the customer's active consent, within the consented scope.",
    "P_CUST_02": "Customer data may be exported only to a verified / authorized destination.",
    "P_CUST_03": "A customer record under legal hold must not be archived.",
    "P_CUST_04": "A customer record may be archived only after its retention period has expired.",
    "P_CUST_05": "Records flagged do-not-contact must not be exported to marketing destinations.",
    "P_CUST_06": "An archived customer record must not be exported.",
    "P_CUST_07": "Agents may archive expired records in their own queue.",
    "P_CUST_08": "Customer data must never leave the company.",
    "P_CUST_10": "Only senior support staff may export full customer records.",
    "P_CUST_12": "A customer record with an open dispute must not be archived.",
    "P_CUST_13": "Records may always be disclosed to the statutory data-protection regulator on a lawful request.",
    "P_CUST_14": "A verified customer erasure (right-to-be-forgotten) request must be honoured.",
    "P_CUST_15": "Full records must be shared with the appointed partner / insurer for active claims.",
    "P_CUST_16": "Sensitive-category data (e.g. health) must not be shared with external parties.",
}


def in_domain_text(pid: str, entry: dict) -> str:
    return normalize_text(CANON[pid]) if pid in CANON else pick_text(entry)


def check(store: list[dict], name: str) -> None:
    ids = [p["policy_id"] for p in store]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise SystemExit(f"{name}: duplicate ids {dupes}")
    bad = [p["policy_id"] for p in store
           if not p["text"] or not (p["text"][:1].isupper() and p["text"][-1] in ".!?")]
    if bad:
        raise SystemExit(f"{name}: empty or badly-styled text for {bad}")


def main() -> int:
    ind = text_candidates("in_domain")
    ood = text_candidates("ood")

    in_texts = {pid: in_domain_text(pid, ind[pid]) for pid in ind}

    # OOD store: in-domain ids keep their reworded text where an OOD seed gives one (no CANON - that
    # would erase the reword), else the in-domain text; then the new CUST ids from the catalogue.
    ood_texts = {pid: pick_text(ood[pid]) for pid in ood}
    missing = sorted(pid for pid in ood if pid.startswith("P_CUST_") and pid not in CUST_TEXT)
    if missing:
        raise SystemExit(f"CUST text missing for seed-cited ids: {missing} (add to CUST_TEXT)")
    for pid in CUST_TEXT:
        if pid in ood_texts:
            ood_texts[pid] = normalize_text(CUST_TEXT[pid])

    policies = [{"policy_id": pid, "text": in_texts[pid]} for pid in sorted(ind)]
    ood_store = [{"policy_id": pid, "text": ood_texts.get(pid) or in_texts[pid]} for pid in sorted(ind)]
    ood_store += [{"policy_id": pid, "text": ood_texts[pid]} for pid in sorted(ood) if pid not in ind]

    check(policies, "policies.jsonl")
    check(ood_store, "policies_ood.jsonl")
    OUT.mkdir(parents=True, exist_ok=True)
    write_jsonl(OUT / "policies.jsonl", policies)
    write_jsonl(OUT / "policies_ood.jsonl", ood_store)
    print(f"policies.jsonl: {len(policies)}   policies_ood.jsonl: {len(ood_store)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
