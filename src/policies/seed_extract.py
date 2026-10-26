"""Extract the visible policy TEXT from the seeds - the source of truth for the policy store.

The seeds (data/seeds/{in_domain,ood}/*.yaml) are authoritative. The human wording of each policy
lives in a seed's free-text `notes`; this module pulls it out, picks one clean wording per policy,
and normalizes its style. Both scripts/gen_policy.py (the doc) and scripts/gen_policy_store.py (the
store) import from here so there is one parse path and the text can never drift from the seeds.

Only text - no decisions, facts, risk types or case types. A policy is a company rule (id + text).
"""
import glob
import re
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from src.common.io import REPO_ROOT

SEED_DIR = REPO_ROOT / "data" / "seeds"
GLOBS = {"in_domain": str(SEED_DIR / "in_domain" / "IND-*.yaml"),
         "ood": str(SEED_DIR / "ood" / "OOD-*.yaml")}

# Same rule worded differently across seeds -> one canonical text (only the visible wording).
CANON = {
    "P_ACC_05": "Sensitive internal resources may be accessed only by verified internal users.",
    "P_ACC_08": "Write access to confidential resources requires the data owner's approval.",
    "P_ACC_12": "The last remaining admin of a system must not have admin revoked.",
    "P_FILE_06": "Files under legal hold must never be deleted.",
    "P_FILE_11": "Backup files require approval before deletion.",
    "P_FILE_23": "Files under legal hold must not be deleted or moved.",
    "P_FIN_07": "Payments may be sent only to verified, authorized vendor accounts.",
    "P_PRIV_06": "Confidential records / customer lists must never be emailed outside the company.",
    "P_REPO_01": "Production repositories may be deleted or archived only with human approval.",
    "P_REPO_04": "A repository may be deleted only by its owning team.",
}


def normalize_text(text: str) -> str:
    """One uniform style for every policy text: collapsed spaces, capital first letter, final stop.
    Fixes the lowercase / no-stop texts at a single point and applies the SAME treatment to every
    policy, so casing or punctuation can never signal anything. Cosmetic only."""
    text = " ".join(text.split()).strip().strip('"').strip()
    text = " ".join(text.split())
    if not text:
        return text
    if text[0].isalpha():
        text = text[0].upper() + text[1:]
    if text[-1] not in ".!?":
        text += "."
    return text


def load_seeds(which: str) -> list[dict]:
    """which = 'in_domain' or 'ood'."""
    return [yaml.safe_load(open(f, encoding="utf-8")) for f in sorted(glob.glob(GLOBS[which]))]


def _raw_texts_from_notes(d: dict) -> dict[str, str]:
    """The policy wording(s) a seed's notes state, per policy id. Handles the OOD `reworded <PID>: "..."`
    quoted form (uniform across case types) first, then the in-domain per-case-type phrasing."""
    notes, ct, pids = d.get("notes", ""), d["case_type"], d["gold_policy_ids"]
    out: dict[str, str] = {}
    for pid in pids:
        m = re.search(rf"{re.escape(pid)}:\s*\"([^\"]+)\"", notes)
        if m:
            out[pid] = m.group(1)
    if all(pid in out for pid in pids):
        return out
    p0 = re.escape(pids[0])
    if ct == "T1":
        attr = d["key_fact"]["attribute"]
        m = re.search(rf"{p0}: (.+?) A {re.escape(attr)}=", notes)
        if m:
            out.setdefault(pids[0], m.group(1))
    elif ct == "T2":
        m = re.search(rf"{p0}: (.+?) base ", notes)
        if m:
            out.setdefault(pids[0], m.group(1))
    elif ct == "T3":
        m = re.search(rf"{p0}: (.+?) -> ALLOW/SAFE", notes)
        if m:
            out.setdefault(pids[0], m.group(1))
    elif ct == "T4":
        m = re.search(rf"{p0}: (.+?) Violation visible", notes)
        if m:
            out.setdefault(pids[0], m.group(1))
    elif ct == "T5":
        if d.get("t5_kind") == "policy_conflict" and len(pids) >= 2:
            m = re.search(rf"{re.escape(pids[0])} \((.+?)\) vs {re.escape(pids[1])} \((.+?)\);", notes)
            if m:
                out.setdefault(pids[0], m.group(1))
                out.setdefault(pids[1], m.group(2))
        else:
            m = re.search(rf"\({p0}: (.+?)\):", notes)
            if m:
                out.setdefault(pids[0], m.group(1))
    return out


def text_candidates(which: str) -> dict[str, dict]:
    """{policy_id: {"domain": str, "by_ct": {case_type: [clean texts]}}} for one seed set."""
    pol: dict[str, dict] = defaultdict(lambda: {"domain": None, "by_ct": defaultdict(list)})
    for d in load_seeds(which):
        texts = _raw_texts_from_notes(d)
        for pid in d["gold_policy_ids"]:
            pol[pid]["domain"] = d["domain"]
            if pid in texts:
                clean = normalize_text(re.sub(r"^reworded\s+P_[A-Z]+_\d+:\s*", "", texts[pid].strip()))
                if clean:
                    pol[pid]["by_ct"][d["case_type"]].append(clean)
    return dict(pol)


def pick_text(entry: dict) -> str:
    """One wording per policy: prefer the declarative T1/T3/T4 form over T2/T5 fragments, then the
    most common. Returns '' if the seeds give no wording (caller supplies it another way)."""
    for ct in ("T1", "T3", "T4", "T2", "T5"):
        cands = entry["by_ct"].get(ct)
        if cands:
            return Counter(cands).most_common(1)[0][0]
    return ""
