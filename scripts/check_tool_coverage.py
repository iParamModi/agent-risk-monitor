"""Check every seed and every policy against the monitor check tools; write docs/check_tools_coverage.md.

Company-side tooling: it reads hidden facts, gold decisions and seed notes. Monitor and baseline code
must never import from this script.

There is no policy_logic.yaml yet: the policy store is text only ({policy_id, text}). So each policy's
action, fact, condition and decision are taken from the seeds that cite it (key_fact, hidden_pair,
t2_subtypes and the gold written in notes). Item 11 therefore checks that the seeds agree with each
other through the policies (same policy + same fact value -> same decision, and no other policy on the
same action and fact gives a stricter decision), not against an independent logic file.

Run:  python scripts/check_tool_coverage.py
"""
import importlib.util
import re
import sys
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from itertools import combinations
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lma_agent.sim import models  # noqa: E402  (simulator classes only, to check fields)
from src.common.io import read_jsonl  # noqa: E402

OUT = ROOT / "docs" / "check_tools_coverage.md"
DECISIONS = r"(ALLOW|ASK_CONFIRMATION|BLOCK|ESCALATE)"
STRICT = {"ALLOW": 0, "ASK_CONFIRMATION": 1, "BLOCK": 2}  # decisions.md: BLOCK > ASK_CONFIRMATION > ALLOW
NEW_TOOL_MIN = 3  # rule 2: a fact needed by >= 3 seeds or policies gets a proposed check tool

# docs/Policy.md "Read by" column: the check each seed fact was written for, when notes name none.
_spec = importlib.util.spec_from_file_location("gen_policy", ROOT / "scripts" / "gen_policy.py")
_gen_policy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_gen_policy)
POLICY_DOC_CHECK = {k: re.split(r" / | \+ ", v)[0].replace(" (NEW)", "") for k, v in _gen_policy.CHECK_FOR.items()}

# Old or proposed check names used in seed notes / docs/Policy.md that mean an existing check.
OLD_NAMES = {"check_retention": "check_retention_status"}

# Seed fact (key_fact.attribute) -> the existing check and returns field that give it.
# alias = the seed uses another name for the same fact (rule 1).
COVERED = {
    "sharing": ("check_file_sharing", "sharing", ""),
    "classification": ("check_file_classification", "classification", ""),
    "sensitivity": ("check_file_classification", "classification", "normal/restricted is the classification scale"),
    "owner": ("check_file_owner", "owner", ""),
    "retention_status": ("check_retention_status", "retention_hold", "active = hold, expired = no hold"),
    "retention_expired": ("check_retention_status", "retention_hold", "expired = no hold"),
    "account_type": ("check_recipient_type", "recipient_type", "employee = internal, contractor/vendor = external"),
    "kind": ("check_recipient_type", "recipient_type", "Contact.kind"),
    "recipient_class": ("check_recipient_type", "recipient_type", ""),
    "registered_vendor": ("check_recipient_type", "recipient_type", "Account.type = vendor"),
    "account_kind": ("check_recipient_type", "recipient_type", "Account.type company/personal"),
    "recipient_country": ("check_recipient_region", "domestic", ""),
    "data_region": ("check_recipient_region", "region", ""),
    "approval_limit_inr": ("check_approval_limit", "approval_limit_inr", ""),
    "balance_inr": ("check_account_balance", "balance_inr", ""),
    "production": ("check_repository_status", "production", ""),
    "is_production": ("check_repository_status", "production", ""),
    "role_eligible": ("check_user_authorization", "role", "seniority is read from role"),
    "consent": ("check_customer_consent", "export_consent", ""),
}

# Facts no existing check returns -> the check tool that would return it (proposed only, rule 2/3).
# {name, params, returns, revealed_by}; several facts of the same kind share one proposed tool.
UNCOVERED = {
    "legal_hold": ("check_legal_hold", "FILE", {"resource": "File path or customer id"}, {"legal_hold": "boolean"}, "none"),
    "authorized_financial": ("check_user_clearance", "ACC", {"user": "User id"}, {"clearances": "list[string]"}, "none"),
    "authorized_hr": ("check_user_clearance", "ACC", {"user": "User id"}, {"clearances": "list[string]"}, "none"),
    "authorized_legal": ("check_user_clearance", "ACC", {"user": "User id"}, {"clearances": "list[string]"}, "none"),
    "authorized_pii": ("check_user_clearance", "ACC", {"user": "User id"}, {"clearances": "list[string]"}, "none"),
    "clearance": ("check_user_clearance", "ACC", {"user": "User id"}, {"clearances": "list[string]"}, "none"),
    "owner_approved": ("check_owner_approval", "ACC", {"user": "User id", "resource": "Resource"}, {"owner_approved": "boolean"}, "none"),
    "is_last_admin": ("check_admin_count", "ACC", {"resource": "Resource"}, {"active_admins": "integer"}, "list_permissions.levels"),
    "archived": ("check_repository_archived", "REPO", {"repo": "Repository name"}, {"archived": "boolean"}, "get_repo.archived"),
    "locked": ("check_file_lock", "FILE", {"file": "File path"}, {"locked": "boolean"}, "none"),
    "environment": ("check_file_environment", "FILE", {"file": "File path"}, {"environment": "string"}, "none"),
    "contains_pii": ("check_file_pii", "FILE", {"file": "File path"}, {"contains_pii": "boolean"}, "none"),
    "dlp_scan": ("check_dlp_scan", "PRIV", {"file": "File path"}, {"dlp_scan": "string"}, "none"),
    "is_backup": ("check_backup_status", "FILE", {"file": "File path"}, {"is_backup": "boolean"}, "none"),
    "owner_team": ("check_owner_team", "FILE", {"resource": "File path or repository"}, {"owner_team": "string"}, "get_repo.owner_team"),
    "sanctioned": ("check_sanctions", "FIN", {"account": "Account id"}, {"sanctioned": "boolean"}, "none"),
    "kyc_status": ("check_kyc", "FIN", {"account": "Account id"}, {"kyc_status": "string"}, "none"),
    "payee_preapproved": ("check_payee_status", "FIN", {"account": "Account id"}, {"payee_preapproved": "boolean"}, "none"),
    "dual_approval_obtained": ("check_dual_approval", "FIN", {"account": "Account id"}, {"dual_approval_obtained": "boolean"}, "none"),
    "duplicate_flag": ("check_duplicate_payment", "FIN", {"account": "Account id"}, {"duplicate_flag": "boolean"}, "none"),
    "address_verified": ("check_recipient_verification", "CAL", {"recipient": "Contact id or email"}, {"address_verified": "boolean"}, "none"),
    "nda_in_place": ("check_recipient_nda", "PRIV", {"recipient": "Contact id or email"}, {"nda_in_place": "boolean"}, "none"),
    "marketing_consent": ("check_marketing_consent", "PRIV", {"recipient": "Customer or contact id"}, {"marketing_consent": "string"}, "none"),
    "contract_active": ("check_contract_status", "CAL", {"recipient": "Contact id"}, {"contract_active": "boolean"}, "none"),
    "lifecycle": ("check_repository_lifecycle", "REPO", {"repo": "Repository name"}, {"lifecycle": "string"}, "none"),
    "backup_exists": ("check_repository_backup", "REPO", {"repo": "Repository name"}, {"backup_exists": "boolean"}, "none"),
    "has_open_dependencies": ("check_repository_dependencies", "REPO", {"repo": "Repository name"}, {"has_open_dependencies": "boolean"}, "none"),
    "has_active_deploys": ("check_repository_deploys", "REPO", {"repo": "Repository name"}, {"has_active_deploys": "boolean"}, "none"),
    "has_active_incidents": ("check_repository_incidents", "REPO", {"repo": "Repository name"}, {"has_active_incidents": "boolean"}, "none"),
    "compliance_locked": ("check_repository_compliance", "REPO", {"repo": "Repository name"}, {"compliance_locked": "boolean"}, "none"),
    "modifiable": ("check_repository_compliance", "REPO", {"repo": "Repository name"}, {"compliance_locked": "boolean"}, "none"),
    "status": ("check_customer_status", "CUST", {"customer_id": "Customer id"}, {"status": "string"}, "get_customer_record.status"),
    "consent_scope": ("check_consent_scope", "CUST", {"customer_id": "Customer id"}, {"consent_scope": "string"}, "none"),
    "dnc": ("check_dnc_registry", "CUST", {"customer_id": "Customer id"}, {"dnc": "boolean"}, "none"),
    "dispute": ("check_dispute_status", "CUST", {"customer_id": "Customer id"}, {"dispute": "string"}, "none"),
    "processor_status": ("check_destination_authorized", "CUST", {"destination": "Destination address or domain"}, {"processor_status": "string"}, "none"),
}

# T5 facts_disagree: which returns field lets each named check express the disputed fact.
# A check missing here cannot take part in that disagreement.
T5_FIELDS = {
    "account_type": {"check_recipient_type": "recipient_type"},
    "recipient_class": {"check_recipient_type": "recipient_type"},
    "exposure": {"check_file_classification": "classification", "check_file_sharing": "sharing"},
    "disposable": {"check_file_classification": "classification", "check_retention_status": "retention_hold"},
    "modifiable": {"check_repository_status": "production"},
    "consent": {"check_customer_consent": "export_consent"},
    "retention_status": {"check_retention_status": "retention_hold"},
    "locked": {},
    "is_last_admin": {},
}

# Simulator field per check returns field (item 7). None = not a typed field (only generic attrs).
SIM_FIELDS = {
    "check_file_sharing": [("File", "sharing"), ("Folder", "sharing")],
    "check_file_owner": [("File", "owner")],
    "check_file_classification": [("File", "classification")],
    "check_retention_status": [("File", "retention_hold"), ("File", "retain_until"),
                               ("Customer", "retention_hold"), ("Customer", "retain_until")],
    "check_user_authorization": [("User", "role"), ("CompanyState", "permissions")],
    "check_recipient_type": [("Contact", "kind"), ("User", "is_external"), ("Account", "type")],
    "check_recipient_region": [("Contact", "region"), ("Account", "region")],
    "check_approval_limit": [("User", "approval_limit_inr")],
    "check_account_balance": [("Account", "balance_inr")],
    "check_repository_status": [("Repo", "production")],
    "check_customer_consent": [("Customer", "export_consent")],
}


# ---------------------------------------------------------------- loading

def load_yaml(rel):
    return yaml.safe_load(open(ROOT / rel, encoding="utf-8"))


CHECKS = load_yaml("configs/check_tools.yaml")
TABLE = load_yaml("configs/check_table.yaml")
AGENT = load_yaml("lma_agent/tools.yaml")
PHASES = load_yaml("configs/tool_phases.yaml")
PHASE1 = {t for g in ("phase1_in_domain", "ood_test_only") for k in ("read", "write") for t in PHASES[g][k]}
STORES = {"in_domain": {p["policy_id"]: p["text"] for p in read_jsonl(ROOT / "data/policies/policies.jsonl")},
          "ood": {p["policy_id"]: p["text"] for p in read_jsonl(ROOT / "data/policies/policies_ood.jsonl")}}


def load_seeds():
    seeds = []
    for which, pat in (("in_domain", "in_domain/IND-*.yaml"), ("ood", "ood/OOD-*.yaml")):
        for f in sorted((ROOT / "data" / "seeds").glob(pat)):
            d = yaml.safe_load(open(f, encoding="utf-8"))
            d["_set"] = which
            d["_notes"] = " ".join(d.get("notes", "").split())
            seeds.append(d)
    return seeds


# ---------------------------------------------------------------- seed parsing

def case_label(s):
    if s["case_type"] == "T5":
        return f"T5 {s.get('t5_kind', '?')}"
    return s["case_type"]


def gold(s):
    """{variant: decision} parsed from the seed notes."""
    n, ct = s["_notes"], s["case_type"]
    if ct == "T1":
        out = {}
        for v in "AB":
            m = re.search(rf"\b{v}:? [^;]*?->\s*{DECISIONS}", n)
            if m:
                out[v] = m.group(1)
        return out
    if ct == "T2":
        m = re.search(rf"a,b,d->{DECISIONS}\w*[^;]*; c .*?->{DECISIONS}", n)
        if m:
            return {"a": m.group(1), "b": m.group(1), "c": m.group(2), "d": m.group(1)}
        out = {}
        for v in "abcd":
            m = re.search(rf"\b{v}: .*?(?:->|=>)\s*{DECISIONS}", n)
            if m:
                out[v] = m.group(1)
        return out
    if ct == "T3":
        return {"-": "ALLOW"}
    if ct == "T4":
        found = re.findall(DECISIONS, n)
        return {"-": found[0] if found else "?"}
    return {"-": "ESCALATE"}


def named_checks(s):
    """Check names the seed itself states in its notes (old names kept as written)."""
    return [c for c in dict.fromkeys(re.findall(r"\b(check_[a-z_]+)", s["_notes"])) if c != "check_needed"]


def seed_check(s):
    """The check the seed names as correct: its notes first, else docs/Policy.md's Read by column."""
    named = named_checks(s)
    if named:
        return named
    kf = s.get("key_fact")
    return [POLICY_DOC_CHECK[kf["attribute"]]] if kf and kf["attribute"] in POLICY_DOC_CHECK else []


def agent_tools_named(s):
    return [t for t in dict.fromkeys(re.findall(r"\b([a-z_]+)\(", s["_notes"])) if t in AGENT]


def same(a, b):
    a, b = str(a).strip("/").lower(), str(b).strip("/").lower()
    return a == b or any(x.endswith(sep + y) for x, y in ((a, b), (b, a)) for sep in "/@")


def arg_role(s, resource):
    for k, v in s["proposed_action"]["args"].items():
        if isinstance(v, list):
            if any(same(x, resource) for x in v):
                return k
        elif same(v, resource):
            return k
    if s.get("requested_by") and same(s["requested_by"], resource):
        return "$current_user"
    return None


def norm(attr, value, s):
    """Comparable value class for a fact (so different orgs / amounts compare)."""
    if attr == "sharing":
        v = str(value)
        return "external" if v.startswith("external") else v
    amount = s["proposed_action"]["args"].get("amount_inr")
    if attr == "balance_inr" and amount is not None:
        return "covers_amount" if int(value) >= int(amount) else "below_amount"
    if attr == "approval_limit_inr" and amount is not None:
        return "within_limit" if int(amount) <= int(value) else "over_limit"
    return str(value).lower()


def variant_values(s):
    """{variant: normalized value of the key fact} where the notes/state give it."""
    kf = s.get("key_fact")
    if not kf:
        return {}
    attr = kf["attribute"]
    if s["case_type"] == "T1" and s.get("hidden_pair"):
        return {v: norm(attr, list(s["hidden_pair"][v].values())[0], s) for v in "AB"}
    if s["case_type"] == "T2":
        m = (re.search(rf"base {re.escape(attr)}[ =]([\w:\-]+)", s["_notes"])
             or re.search(r"true state: ([\w:\-,]+)", s["_notes"]))
        if m:
            base = m.group(1).replace(",", "")
            if attr == "balance_inr":
                base = int(base)
            return {v: norm(attr, base, s) for v in "abd"}
    return {}


# ---------------------------------------------------------------- inventory

def fact_check(attr):
    """(check, field, note) when an existing check returns the fact, else None."""
    return COVERED.get(attr)


def table_entry(action, check):
    for e in TABLE.get(action) or []:
        if e["check"] == check:
            return e
    return None


def seed_inventory(seeds):
    rows = []
    for s in seeds:
        kf = s.get("key_fact") or {}
        named = seed_check(s)
        rows.append({
            "id": s["seed_id"], "domain": s["domain"], "case": case_label(s), "set": s["_set"],
            "action": s["proposed_action"]["name"], "args": s["proposed_action"]["args"],
            "fact": kf.get("attribute"), "resource": kf.get("resource"),
            "values": variant_values(s), "named": named, "policies": s["gold_policy_ids"], "gold": gold(s),
        })
    return rows


def policy_inventory(seeds):
    """Per (set, policy id): actions, facts, decisions, conflict partners, all taken from the seeds."""
    pol = {}
    for which, store in STORES.items():
        for pid, text in store.items():
            twin = STORES["in_domain"].get(pid)
            wording = ("in-domain" if which == "in_domain" else
                       "OOD (new domain)" if twin is None else
                       "OOD (reworded)" if twin != text else "OOD (copy of in-domain)")
            pol[(which, pid)] = {"set": which, "id": pid, "domain": pid.split("_")[1], "text": text,
                                 "wording": wording, "actions": set(), "facts": set(), "hidden_seeds": [],
                                 "written_seeds": [], "rules": defaultdict(dict), "conflicts": set(),
                                 "seeds": []}
    for s in seeds:
        for pid in s["gold_policy_ids"]:
            p = pol.get((s["_set"], pid))
            if p is None:
                continue
            p["seeds"].append(s["seed_id"])
            p["actions"].add(s["proposed_action"]["name"])
            kf = s.get("key_fact")
            if kf and s["case_type"] in ("T1", "T2") or (s["case_type"] == "T5" and s.get("t5_kind") == "facts_disagree"):
                p["facts"].add(kf["attribute"])
                p["hidden_seeds"].append(s["seed_id"])
            else:
                p["written_seeds"].append(s["seed_id"])
            if s["case_type"] == "T5" and s.get("t5_kind") == "policy_conflict":
                p["conflicts"].update(x for x in s["gold_policy_ids"] if x != pid)
        if s["case_type"] in ("T1", "T2") and s.get("key_fact") and len(s["gold_policy_ids"]) == 1:
            p = pol.get((s["_set"], s["gold_policy_ids"][0]))
            key = (s["proposed_action"]["name"], s["key_fact"]["attribute"], arg_role(s, s["key_fact"]["resource"]))
            g = gold(s)
            for v, val in variant_values(s).items():
                if v in g:
                    p["rules"][key].setdefault(val, []).append((s["seed_id"], v, g[v]))
    for p in pol.values():
        p["kind"] = "hidden state" if p["facts"] else ("written in policy" if p["seeds"] else "unused")
        decisions = {d for vals in p["rules"].values() for lst in vals.values() for _, _, d in lst}
        p["decisions"] = decisions
    return pol


# ---------------------------------------------------------------- verification

def fact_users(seeds, pols):
    """attr -> (set of seed ids, set of policy keys) that need it."""
    users = defaultdict(lambda: (set(), set()))
    for s in seeds:
        kf = s.get("key_fact")
        if kf:
            users[kf["attribute"]][0].add(s["seed_id"])
    for key, p in pols.items():
        for f in p["facts"]:
            users[f][1].add(key)
    return users


def check_seed(s, r, pols, users, sim_missing):
    """List of (item, detail) failures for one seed."""
    fails = []
    ct, action, attr = s["case_type"], r["action"], r["fact"]
    kind = s.get("t5_kind")
    needs_check = attr is not None and ct in ("T1", "T2") or kind == "facts_disagree"
    r["resolved"] = None
    r["needs_check"] = needs_check
    if action not in PHASE1:
        r["out_of_scope"] = True
        return []

    if ct in ("T1", "T2") and attr:
        cov = fact_check(attr)
        named = [OLD_NAMES.get(c, c) for c in r["named"]]
        if cov is None:
            want = UNCOVERED.get(attr, ("?",))[0]
            fails.append((1, f"no check returns `{attr}`" + (f" (seed names `{r['named'][0]}`)" if r["named"] else "")))
            fails.append((2, f"`{attr}` is not in any check's returns"))
            fails.append((3, f"no `{want}` in the `{action}` row"))
        else:
            check, field, _ = cov
            r["resolved"] = check
            if named and named[0] != check:
                if named[0] in CHECKS:
                    fails.append((2, f"seed names `{r['named'][0]}`, which does not return `{attr}`; `{check}.{field}` does"))
            if field not in CHECKS[check]["returns"]:
                fails.append((2, f"`{check}` does not return `{field}`"))
            entry = table_entry(action, check)
            if entry is None:
                fails.append((3, f"`{check}` not in the `{action}` row"))
            else:
                param = next(iter(CHECKS[check]["params"]))
                src = entry["args"].get(param)
                want = s.get("requested_by") if src == "$current_user" else r["args"].get(src)
                if want is None or not same(want, r["resource"]):
                    fails.append((4, f"table fills `{param}` from `{src}` = `{want}`, but the fact is on `{r['resource']}`"))
            if ct == "T2":
                rev = CHECKS[check]["revealed_by"]
                tools = [x.strip().split(".")[0] for x in rev.split(",")] if rev != "none" else []
                a = (s.get("t2_subtypes") or {}).get("a") or {}
                read = (a.get("earlier_read") or {}).get("tool")
                if not tools:
                    fails.append((5, f"`{check}` has revealed_by none, so T2a cannot know `{attr}`"))
                elif read not in tools:
                    fails.append((5, f"T2a earlier read is `{read}`, but `{attr}` is shown by `{rev}`"))
            missing = sim_missing.get(check)
            if missing:
                fails.append((7, f"simulator has no typed field for `{check}` ({', '.join(missing)})"))
    if ct in ("T3", "T4") or kind == "policy_conflict":
        if r["named"] or re.search(r"check_needed=true", s["_notes"]):
            fails.append((6, f"no-check case names `{', '.join(r['named']) or 'check_needed=true'}`"))
    if kind == "facts_disagree":
        fails += check_t5_facts(s, r)
    # 12: covered by a policy
    store = STORES[s["_set"]]
    missing_p = [p for p in r["policies"] if p not in store]
    if not r["policies"] or missing_p:
        fails.append((12, f"policies not in the store: {missing_p or 'none named'}"))
    if kind == "policy_conflict":
        fails += check_t5_conflict(s, r, pols)
    r["needs_check"] = needs_check
    return fails


def check_t5_facts(s, r):
    fails = []
    attr, action = r["fact"], r["action"]
    named = [OLD_NAMES.get(c, c) for c in r["named"]]
    agent_named = agent_tools_named(s)
    fields = T5_FIELDS.get(attr, {})
    if agent_named and len(named) < 2:
        fails.append((13, f"disagreement is between agent tools `{', '.join(agent_named)}`"
                          + (f" and `{named[0]}`" if named else "") + ", not two checks"))
        return fails
    for c in named:
        if c not in CHECKS:
            fails.append((1, f"`{c}` is not a check tool"))
            continue
        if table_entry(action, c) is None:
            fails.append((3, f"`{c}` not in the `{action}` row"))
        if c not in fields:
            fails.append((13, f"`{c}` returns {list(CHECKS[c]['returns'])}, none of which is `{attr}`"))
    if len(named) < 2:
        fails.append((13, "fewer than two checks named"))
    return fails


def check_t5_conflict(s, r, pols):
    fails = []
    pids = r["policies"]
    if len(pids) < 2:
        return [(13, "policy_conflict names fewer than two policies")]
    for pid in pids[:2]:
        p = pols.get((s["_set"], pid))
        if p and r["action"] not in p["actions"]:
            fails.append((13, f"`{pid}` does not apply to `{r['action']}`"))
    dirs = []
    for pid in pids[:2]:
        p = pols.get((s["_set"], pid))
        d = {x for x in (p["decisions"] if p else set()) if x != "ESCALATE"}
        d |= {gold(x)["-"] for x in SEEDS_BY_ID.values() if pid in x["gold_policy_ids"]
              and x["case_type"] in ("T3", "T4") and x["_set"] == s["_set"]}
        dirs.append(d)
    if all(len(d) == 1 for d in dirs) and dirs[0] == dirs[1]:
        fails.append((13, f"`{pids[0]}` and `{pids[1]}` both lead to {dirs[0]} elsewhere, so they do not conflict"))
    return fails


def gold_mismatches(seeds, rows, pols):
    """Item 11: same policy + same value -> same decision; no other policy on the same action and fact is stricter."""
    out = []
    by_key = defaultdict(list)  # (set, action, attr, role) -> policy keys with a rule
    for key, p in pols.items():
        for rk in p["rules"]:
            by_key[(p["set"],) + rk].append(key)
    for s, r in zip(seeds, rows):
        if s["case_type"] not in ("T1", "T2") or not s.get("key_fact") or r.get("out_of_scope"):
            continue
        rk = (s["_set"], r["action"], r["fact"], arg_role(s, r["resource"]))
        for v, val in r["values"].items():
            g = r["gold"].get(v)
            if g is None:
                continue
            hits = []
            for pk in by_key.get(rk, []):
                for _, _, d in pols[pk]["rules"][rk[1:]].get(val, []):
                    hits.append((pk[1], d))
            if not hits:
                continue
            want = max((d for _, d in hits), key=lambda d: STRICT.get(d, 3))
            if want != g:
                involved = sorted({pid for pid, d in hits if d == want})
                own = set(r["policies"])
                if own & set(involved):
                    side = "seed gold: the same policy gives a different decision for the same value in another seed"
                else:
                    side = scope_note(s, r, involved)
                out.append({"id": r["id"], "variant": v, "value": val, "gold": g, "from_policies": want,
                            "policies": involved, "side": side})
    return out


def scope_note(s, r, involved):
    """Another policy on the same action and fact is stricter: is it scoped to a different visible argument?"""
    role = arg_role(s, r["resource"])
    mine = {k: v for k, v in r["args"].items() if k != role and not isinstance(v, list)}
    theirs = defaultdict(set)
    for sid in (x for pid in involved for x in SEEDS_BY_ID if pid in SEEDS_BY_ID[x]["gold_policy_ids"]
                and SEEDS_BY_ID[x]["_set"] == s["_set"]):
        for k, v in SEEDS_BY_ID[sid]["proposed_action"]["args"].items():
            if k in mine:
                theirs[k].add(str(v))
    diff = [k for k in mine if theirs.get(k) and str(mine[k]) not in theirs[k]]
    if diff:
        k = diff[0]
        return (f"neither, if {', '.join(involved)} only covers `{k}` = {', '.join(sorted(theirs[k]))} "
                f"(this seed: `{mine[k]}`); state that scope in the policy logic. Otherwise the seed gold")
    return f"policy overlap: {', '.join(involved)} is stricter on the same action and fact; seed gold or policy wording"


# ---------------------------------------------------------------- fixes

def propose_seed_fix(s, r, items, users):
    attr, action = r["fact"], r["action"]
    if 12 in items:
        return "Add the policy to the store or point the seed at an existing one (rule 6)"
    if s.get("t5_kind") == "facts_disagree" and ({1, 3, 13} & set(items)):
        return t5_facts_fix(s, r, items)
    if 6 in items:
        return "Remove the check mention / `check_needed=true` from the notes (no-check case)"
    if s.get("t5_kind") == "policy_conflict" and 13 in items:
        return "Pick a partner policy with the opposite decision on the same action, or relabel as T4 (rule 6)"
    if 1 in items and attr in UNCOVERED:
        tool = UNCOVERED[attr][0]
        n = len(users_of_tool(tool, users))
        if n >= NEW_TOOL_MIN:
            return f"New check `{tool}` (section 6; needed by {n})"
        return f"Change seed to a fact an existing check returns, or drop it (`{attr}` needed by {n} < {NEW_TOOL_MIN})"
    if 2 in items and r["resolved"]:
        extra = f", and add it to the `{action}` row (section 7)" if 3 in items else ""
        return f"Map: the check for `{attr}` is `{r['resolved']}`, not `{r['named'][0]}` (rule 1){extra}"
    if 3 in items and r["resolved"]:
        role = arg_role(s, r["resource"])
        param = next(iter(CHECKS[r["resolved"]]["params"]))
        return f"Add `{{check: {r['resolved']}, args: {{{param}: {role}}}}}` to `{action}` (section 7)"
    if 4 in items:
        role = arg_role(s, r["resource"])
        param = next(iter(CHECKS[r["resolved"]]["params"]))
        if role:
            return f"Add `{{check: {r['resolved']}, args: {{{param}: {role}}}}}` to `{action}` (section 7)"
        return f"Change seed: put the fact on `{action}`'s argument (fact resource `{r['resource']}` is not an argument)"
    if 5 in items:
        rev = CHECKS[r["resolved"]]["revealed_by"]
        if rev == "none":
            return f"Change seed: drop subtype a (no agent tool shows `{attr}`), keep b/c/d"
        return f"Change subtype a's earlier read to `{rev.split('.')[0]}`"
    if 7 in items:
        return "No seed change; add the simulator field (section 8)"
    return "-"


def t5_facts_fix(s, r, items):
    attr = r["fact"]
    if items == [3]:
        return f"Add the missing check to the `{r['action']}` row (section 7)"
    if attr in ("account_type", "recipient_class"):
        if r["action"] == "transfer_money":
            return ("Change seed: `check_user_authorization` takes a user, not an account; "
                    "turn into a policy_conflict T5 or drop")
        return "Add `account_type` to `check_user_authorization` returns (section 6), and add it to the action's row"
    if attr == "disposable":
        return "Name `check_retention_status` instead of `check_file_sharing` as the second check, and add it to the row"
    if attr == "modifiable":
        return "Change seed: compare `check_repository_status` with the proposed `check_repository_compliance`, or drop"
    if attr == "consent":
        return "Change seed: second check `check_dnc_registry` does not exist (needed by 2 < 3); pick a covered fact or drop"
    if attr == "retention_status":
        return "New check `check_legal_hold` (section 6) as the second check"
    if attr in ("locked", "is_last_admin"):
        return "Change seed: the disagreement is between agent tool outputs, not two checks; rewrite with two checks or relabel T2"
    return "Change seed so two existing checks return the disputed fact"


def users_of_tool(tool, users):
    out = set()
    for attr, (seeds, pols) in users.items():
        if attr in UNCOVERED and UNCOVERED[attr][0] == tool:
            out |= seeds | {f"policy:{k[1]}" for k in pols}  # one count per policy id (IND and OOD copy alike)
    return out


# ---------------------------------------------------------------- report helpers

def md_table(header, rows):
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    for row in rows:
        out.append("| " + " | ".join(str(c).replace("|", "/") for c in row) + " |")
    return "\n".join(out)


def sim_missing_fields():
    out = {}
    for check, fields in SIM_FIELDS.items():
        miss = [f"{cls}.{f}" for cls, f in fields if f not in getattr(models, cls).model_fields]
        present = [f"{cls}.{f}" for cls, f in fields if f in getattr(models, cls).model_fields]
        if miss and not present:
            out[check] = miss
        elif miss and check in ("check_retention_status", "check_customer_consent", "check_recipient_region"):
            out[check] = miss
    return out


STOP = set("a an the of to and or be may must only with by for in on from its their is are not no any has have "
           "that this it as before after under into than".split())
LOOKALIKE_MIN = 0.25  # Jaccard of content words


def word_overlap(a, b):
    wa, wb = ({x for x in re.findall(r"[a-z]+", t.lower()) if x not in STOP and len(x) > 2} for t in (a, b))
    return len(wa & wb) / len(wa | wb) if wa | wb else 0.0


def wording_overlap(text, seed):
    hint = seed.get("story_hint", "")
    return SequenceMatcher(None, text.lower(), hint.lower()).ratio()


# ---------------------------------------------------------------- main

SEEDS_BY_ID = {}


def main():
    seeds = load_seeds()
    SEEDS_BY_ID.update({s["seed_id"]: s for s in seeds})
    rows = seed_inventory(seeds)
    pols = policy_inventory(seeds)
    users = fact_users(seeds, pols)
    sim_missing = sim_missing_fields()

    seed_fails = {}
    for s, r in zip(seeds, rows):
        seed_fails[r["id"]] = check_seed(s, r, pols, users, sim_missing)
    mism = gold_mismatches(seeds, rows, pols)
    for m in mism:
        seed_fails[m["id"]].append((11, f"{m['variant']}: gold {m['gold']}, policies give {m['from_policies']}"))

    # ---- policies: items 8-10
    pol_fails = {}
    for key, p in pols.items():
        f = []
        for attr in sorted(p["facts"]):
            cov = fact_check(attr)
            t5_only = all(SEEDS_BY_ID[x]["case_type"] == "T5" for x in p["hidden_seeds"]
                          if (SEEDS_BY_ID[x].get("key_fact") or {}).get("attribute") == attr)
            if cov is None and not (t5_only and attr in T5_FIELDS):
                f.append((8, attr, f"no check returns `{attr}`"))
                continue
            if cov is None:
                continue
            for action in sorted(p["actions"] & PHASE1):
                if table_entry(action, cov[0]) is None:
                    f.append((9, attr, f"`{cov[0]}` not in the `{action}` row"))
        if p["kind"] == "written in policy":
            for sid in p["written_seeds"]:
                if named_checks(SEEDS_BY_ID[sid]):
                    f.append((10, "-", f"seed {sid} names a check for a written condition"))
        if f:
            pol_fails[key] = f

    # ---- fixes
    seed_rows, fix_count = [], Counter()
    for s, r in zip(seeds, rows):
        fails = seed_fails[r["id"]]
        if not fails:
            continue
        items = sorted({i for i, _ in fails})
        fix = propose_seed_fix(s, r, items, users)
        if 11 in items and fix == "-":
            m = next(m for m in mism if m["id"] == r["id"])
            fix = f"Gold: {m['side']}; check {', '.join(m['policies'])}"
        named = ", ".join(r["named"]) or (COVERED.get(r["fact"], ("",))[0] if r["fact"] else "") or "-"
        seed_rows.append([r["id"], r["action"], r["fact"] or "-", named, ", ".join(map(str, items)),
                          fix, "; ".join(d for _, d in fails)])
        fix_count[fix.split(" (")[0]] += 1
        if 11 in items and not fix.startswith("Gold"):
            m = next(m for m in mism if m["id"] == r["id"])
            seed_rows.append([r["id"], r["action"], r["fact"] or "-", named, "11",
                              f"Gold: {m['side']}; check {', '.join(m['policies'])}", ""])

    pol_rows = []
    for key, f in sorted(pol_fails.items()):
        p = pols[key]
        items = sorted({i for i, _, _ in f})
        attrs = sorted({a for _, a, _ in f if a != "-"})
        if 8 in items:
            a = next(a for i, a, _ in f if i == 8)
            tool = UNCOVERED.get(a, ("?",))[0]
            n = len(users_of_tool(tool, users))
            fix = (f"New check `{tool}` (section 6)" if n >= NEW_TOOL_MIN
                   else f"Change the policy's seeds to a covered fact, or drop (`{a}` needed by {n})")
        elif 9 in items:
            fix = "Table edit (section 7)"
        else:
            fix = "Remove the check from the seed notes"
        pol_rows.append([f"{p['id']} ({'OOD' if p['set'] == 'ood' else 'IND'})", ", ".join(sorted(p["actions"])),
                         ", ".join(attrs) or "-", ", ".join(map(str, items)), fix])

    # ---- proposed table edits (from item 3/4 failures with a covered fact)
    proposed_edits = defaultdict(lambda: {"args": set(), "ids": set()})  # (action, check) -> args, users

    def propose(s, action, check, ids):
        role = arg_role(s, s["key_fact"]["resource"]) if s.get("key_fact") else None
        if not role or action not in PHASE1:
            return False
        params = list(CHECKS[check]["params"])
        args = {params[0]: role}
        if check == "check_user_authorization":  # second param: the resource being accessed or sent
            other = {"send_email": "attachment", "share_file": "file", "grant_permission": "resource"}.get(action)
            if not other:
                return False
            args["resource"] = other
        proposed_edits[(action, check)]["args"].add(", ".join(f"{k}: {v}" for k, v in args.items()))
        proposed_edits[(action, check)]["ids"] |= set(ids)
        return True

    for s, r in zip(seeds, rows):
        for i, d in seed_fails[r["id"]]:
            m = re.search(r"`(check_\w+)` not in the `(\w+)` row", d)
            if i in (3, 4) and m and m.group(1) in CHECKS:
                propose(s, m.group(2), m.group(1), [r["id"]])
    for key, f in pol_fails.items():
        for i, attr, d in f:
            m = re.search(r"`(check_\w+)` not in the `(\w+)` row", d)
            if i == 9 and m:
                src = [SEEDS_BY_ID[x] for x in pols[key]["hidden_seeds"]
                       if SEEDS_BY_ID[x]["proposed_action"]["name"] == m.group(2)]
                if not any(propose(x, m.group(2), m.group(1), [key[1]]) for x in src):
                    proposed_edits[(m.group(2), m.group(1))]["ids"].add(key[1])

    # ---- coverage per check tool
    cov_rows = []
    used_checks = defaultdict(lambda: {"pol": set(), "ind": set(), "ood": set(), "T1": set(), "T2": set(), "T5": set()})
    for s, r in zip(seeds, rows):
        checks = set()
        if r["resolved"]:
            checks.add(r["resolved"])
        if s.get("t5_kind") == "facts_disagree":
            checks |= {OLD_NAMES.get(c, c) for c in r["named"] if OLD_NAMES.get(c, c) in CHECKS}
        for c in checks:
            u = used_checks[c]
            u["ind" if s["_set"] == "in_domain" else "ood"].add(r["id"])
            if s["case_type"] in ("T1", "T2", "T5"):
                u[s["case_type"]].add(r["id"])
    for key, p in pols.items():
        for attr in p["facts"]:
            cov = fact_check(attr)
            if cov:
                used_checks[cov[0]]["pol"].add(key)
    for c in CHECKS:
        u = used_checks[c]
        cov_rows.append([f"`{c}`", len(u["pol"]), len(u["ind"]), len(u["ood"]), len(u["T1"]), len(u["T2"]), len(u["T5"])])
    unused_tools = [c for c in CHECKS if not any(used_checks[c][k] for k in used_checks[c])]

    # unused table entries: no seed/policy with that action resolves to that check
    needed = set()
    for s, r in zip(seeds, rows):
        if r["resolved"]:
            needed.add((r["action"], r["resolved"]))
        if s.get("t5_kind") == "facts_disagree":
            needed |= {(r["action"], OLD_NAMES.get(c, c)) for c in r["named"]}
    for p in pols.values():
        for attr in p["facts"]:
            cov = fact_check(attr)
            if cov:
                needed |= {(a, cov[0]) for a in p["actions"]}
    unused_entries = [(a, e["check"]) for a, row in TABLE.items() for e in (row or []) if (a, e["check"]) not in needed]
    unused_pols = [p for p in pols.values() if not p["seeds"]]

    # ---- policy set health
    conflict_pairs = sorted({tuple(sorted((p["set"], p["id"], c))) for p in pols.values() for c in p["conflicts"]})
    conflict_pairs = sorted({(p["set"], *sorted((p["id"], c))) for p in pols.values() for c in p["conflicts"]})
    lookalikes = set()
    for which in STORES:
        ps = [p for p in pols.values() if p["set"] == which and p["seeds"]]
        for a, b in combinations(ps, 2):
            if a["domain"] == b["domain"] and a["actions"] & b["actions"] and \
                    {a["kind"], b["kind"]} == {"hidden state", "written in policy"} and \
                    word_overlap(a["text"], b["text"]) >= LOOKALIKE_MIN:
                lookalikes.add((which, *sorted((a["id"], b["id"]))))
    copies = []
    for p in pols.values():
        for sid in p["seeds"]:
            ratio = wording_overlap(p["text"], SEEDS_BY_ID[sid])
            if ratio >= 0.6:
                copies.append((p["set"], p["id"], sid, ratio))

    # ---- write report
    failing_seed_ids = {r[0] for r in seed_rows}
    out_scope = [r["id"] for r in rows if r.get("out_of_scope")]
    needing_check = sum(1 for r in rows if r.get("needs_check"))
    L = []
    L.append("# Check tools coverage: seeds and policies against the monitor check tools\n")
    L.append("> Generated by `python scripts/check_tool_coverage.py`. Do not edit by hand; rerun after seeds, "
             "policies or configs change.\n")
    L.append("> There is no `policy_logic.yaml` yet: the store is text only. Each policy's action, fact and "
             "decision are taken from the seeds that cite it, so item 11 checks that seeds agree with each "
             "other through the policies, not against an independent logic file.\n")
    L.append("## 1. Summary\n")
    n_ind = sum(1 for r in rows if r["set"] == "in_domain")
    L.append(md_table(["", "count"], [
        ["Seeds total", f"{len(rows)} (in-domain {n_ind}, OOD {len(rows) - n_ind})"],
        ["Policies total", f"{len(pols)} (in-domain store {len(STORES['in_domain'])}, OOD store {len(STORES['ood'])})"],
        ["Seeds that need a check (T1, T2, T5 facts_disagree)", needing_check],
        ["Seeds out of scope (action not in phase 1, not checked)",
         f"{len(out_scope)} ({', '.join(out_scope)})"],
        ["Seeds that pass every item", len(rows) - len(failing_seed_ids) - len(out_scope)],
        ["Seeds that fail", len(failing_seed_ids)],
        ["Policies that fail", len(pol_fails)],
        ["Gold mismatches (item 11)", len(mism)],
    ]))
    items_count = Counter(i for f in seed_fails.values() for i in {i for i, _ in f})
    L.append("\nSeeds failing each item: " + ", ".join(f"{i}: {items_count[i]}" for i in sorted(items_count)) + ".\n")
    L.append("Old check names mapped: " + ", ".join(f"`{a}` → `{b}`" for a, b in OLD_NAMES.items())
             + ". Seed facts read by an existing check under another name (rule 1): "
             + ", ".join(f"`{a}` → `{c}.{f}`" for a, (c, f, _) in COVERED.items() if a != f) + ".\n")
    L.append("Config fixes applied in Step 1 (the test passed after them): `check_tools.yaml` `revealed_by` "
             "fields renamed to the read tools' real output keys: `lookup_contact.organisation` → `lookup_contact.org`, "
             "`get_account.balance` → `get_account.balance_inr`, `list_permissions` → `list_permissions.levels`.\n")

    L.append("## 2. Coverage per check tool\n")
    L.append(md_table(["tool", "policies", "in-domain seeds", "OOD seeds", "T1", "T2", "T5"], cov_rows))

    L.append("\n## 3. Failing seeds\n")
    L.append("Items: 1 name, 2 fact, 3 table, 4 args, 5 T2a, 6 no-check case, 7 simulator, 11 gold, 12 policy, 13 T5.\n")
    L.append(md_table(["seed id", "action", "fact", "named check", "failed item", "proposed fix", "detail"], seed_rows))

    L.append("\n## 4. Failing policies\n")
    L.append(md_table(["policy id", "applies to", "fact", "failed item", "proposed fix"], pol_rows))
    later = sorted(f"{p['id']} ({'OOD' if p['set'] == 'ood' else 'IND'}): {', '.join(sorted(p['actions'] - PHASE1))}"
                   for p in pols.values() if p["actions"] - PHASE1)
    L.append("\nFlag: policies that apply to an action outside phase 1 (not checked, phase 2): "
             + ("; ".join(later) or "none") + ".")

    L.append("\n## 5. Gold mismatches\n")
    if mism:
        L.append(md_table(["seed id", "variant", "fact value", "seed gold", "gold from policies", "policies involved",
                           "which side looks wrong"],
                          [[m["id"], m["variant"], m["value"], m["gold"], m["from_policies"], ", ".join(m["policies"]),
                            m["side"]] for m in mism]))
    else:
        L.append("None.")

    L.append("\n## 6. Proposed new check tools\n")
    L.append(f"Only facts needed by {NEW_TOOL_MIN} or more seeds + policies (rule 2). Not applied.\n")
    tools = defaultdict(list)
    for attr, spec in UNCOVERED.items():
        tools[spec[0]].append(attr)
    proposals = []
    for tool, attrs in sorted(tools.items()):
        n_users = users_of_tool(tool, users)
        if len(n_users) < NEW_TOOL_MIN:
            continue
        spec = UNCOVERED[attrs[0]]
        params = {k: {"type": "string", "description": v} for k, v in spec[2].items()}
        block = {tool: {"domain": spec[1], "params": params, "required": list(params),
                        "returns": {**{k: "string" for k in spec[2]}, **spec[3]}, "revealed_by": spec[4]}}
        seeds_n = sorted(x for x in n_users if not x.startswith("policy:"))
        pols_n = sorted(x.split(":")[1] for x in n_users if x.startswith("policy:"))
        proposals.append(tool)
        L.append(f"### `{tool}` (facts: {', '.join(f'`{a}`' for a in attrs)})\n")
        L.append("```yaml\n" + yaml.safe_dump(block, sort_keys=False, width=200) + "```\n")
        L.append(f"Seeds ({len(seeds_n)}): {', '.join(seeds_n)}  \nPolicies ({len(pols_n)}): {', '.join(pols_n)}\n")
    L.append("### Change to an existing check: `check_user_authorization` returns `account_type`\n")
    t5_acc = [r["id"] for s, r in zip(seeds, rows) if s.get("t5_kind") == "facts_disagree"
              and r["fact"] in ("account_type", "recipient_class") and r["action"] != "transfer_money"]
    L.append("The T5 facts_disagree seeds below make `check_recipient_type` (internal) disagree with "
             "`check_user_authorization` (external_contractor). That only works if `check_user_authorization` "
             "also returns the HR account type (employee / external_contractor / external_vendor):\n")
    L.append("```yaml\ncheck_user_authorization:\n  returns:\n    account_type: string   # new\n```\n")
    L.append(f"Seeds ({len(t5_acc)}): {', '.join(t5_acc)}\n")

    L.append("## 7. Check table edits\n")
    L.append("**Applied:** none. Both configs already matched the agent tools, so only `revealed_by` field "
             "names were changed (section 1).\n")
    L.append("**Proposed** (one row per action and check; several args = the fact sits on different "
             "arguments in different seeds, add one entry per args):\n")
    if proposed_edits:
        L.append(md_table(["action", "add entry", "seeds / policies"],
                          [[a, "<br>".join(f"`{{check: {c}, args: {{{x}}}}}`" for x in sorted(e["args"])) or f"`{c}` (args: see seeds)",
                            ", ".join(sorted(e["ids"]))]
                           for (a, c), e in sorted(proposed_edits.items()) if e["args"] or e["ids"]]))
    else:
        L.append("None.")

    L.append("\n## 8. Missing simulator fields\n")
    L.append("Facts a check reads that `lma_agent/sim/models.py` has no typed field for (today only the "
             "generic `attrs` dict could hold them). Not added.\n")
    sim_rows = []
    for check, miss in sim_missing.items():
        n = sum(1 for f in seed_fails.values() for i, d in f if i == 7 and f"`{check}`" in d)
        sim_rows.append([f"`{check}`", ", ".join(miss), n])
    L.append(md_table(["check", "missing field(s)", "seeds affected"], sim_rows) if sim_rows else "None.")
    L.append("\nPresent: sharing (`File`, `Folder`), owner, classification, role, access level "
             "(`CompanyState.permissions`), recipient internal/external (`Contact.kind`, `User.is_external`, "
             "`Account.type`), approval limit, balance, repository production flag.\n")

    L.append("## 9. Unused tools, table entries and policies\n")
    L.append("**Check tools no seed and no policy uses:** " + (", ".join(f"`{c}`" for c in unused_tools) or "none") + "\n")
    L.append("**Table entries no seed or policy needs** (each one is an extra call in the always setting):\n")
    L.append(md_table(["action", "check"], [[a, f"`{c}`"] for a, c in unused_entries]) if unused_entries else "None.")
    L.append(f"\n**Policies no seed uses:** {len(unused_pols)} (fine as retrieval distractors). In-domain: "
             + (", ".join(p["id"] for p in unused_pols if p["set"] == "in_domain") or "none")
             + f". OOD store: {sum(1 for p in unused_pols if p['set'] == 'ood')} "
               "(mostly unchanged in-domain copies that no OOD seed cites).\n")

    L.append("## 10. Policy set health\n")
    dom = Counter((p["set"], p["domain"]) for p in pols.values())
    doms = sorted({d for _, d in dom})
    L.append(md_table(["store"] + doms + ["total"],
                      [[w] + [dom[(w, d)] for d in doms] + [len(STORES[w])] for w in STORES]))
    wording = Counter(p["wording"] for p in pols.values() if p["set"] == "ood")
    L.append("\nOOD store wording: " + ", ".join(f"{k} {v}" for k, v in sorted(wording.items())) + ".\n")
    L.append(f"Conflict pairs ({len(conflict_pairs)}): " + ", ".join(f"{a}/{b} ({w})" for w, a, b in conflict_pairs) + ".\n")
    L.append(f"Look-alike pairs (same domain and action, one hidden-state and one written condition, "
             f"content-word overlap ≥ {LOOKALIKE_MIN}): "
             f"{len(lookalikes)} (in-domain {sum(1 for x in lookalikes if x[0] == 'in_domain')}): "
             + ", ".join(f"{a}/{b}" for w, a, b in sorted(lookalikes) if w == "in_domain") + ". "
             f"PLAN target: 120+ in-domain rules including look-alikes and conflict pairs; "
             f"in-domain store has {len(STORES['in_domain'])}.\n")
    kinds = Counter(p["kind"] for p in pols.values() if p["set"] == "in_domain")
    L.append("In-domain policies by condition: " + ", ".join(f"{k} {v}" for k, v in kinds.items()) + ".\n")
    L.append("Policies whose text copies a citing seed's `story_hint` closely (SequenceMatcher ≥ 0.6; these "
             "make the rules baseline's job too easy):\n")
    L.append(md_table(["store", "policy", "seed", "similarity"],
                      [[w, pid, sid, f"{x:.2f}"] for w, pid, sid, x in sorted(copies)]) if copies else "None.")

    L.append("\n## 11. Messages for the team\n")
    L.append("**Param (seeds):**\n")
    msgs = Counter()
    for row in seed_rows:
        fix = row[5]
        if fix.startswith(("Change", "Remove", "Map", "Pick", "Name", "Gold", "Add the policy")):
            msgs[fix] += 1
    for fix, n in msgs.most_common():
        ids = [r[0] for r in seed_rows if r[5] == fix]
        L.append(f"- {fix}: {', '.join(ids)}")
    L.append("\n**Policy owner (Param, Step 5 store):**\n")
    pmsgs = defaultdict(list)
    for row in pol_rows:
        pmsgs[row[4]].append(row[0])
    for fix, ids in pmsgs.items():
        L.append(f"- {fix}: {', '.join(ids)}")
    L.append("- Add `policy_logic.yaml` (applies-to, condition, fact, decision) and `conflicts.yaml`, so item 11 "
             "can be checked against the logic instead of against the seeds' own notes.")
    L.append("\n**Prateek (configs / gateway):**\n")
    L.append(f"- Decide on the {len(proposals)} proposed check tools in section 6 and the `account_type` "
             "return on `check_user_authorization`, then the table edits in section 7.")
    L.append("- Add the simulator fields in section 8 when the gateway is built.")

    OUT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print(f"seeds {len(rows)}, out of scope {len(out_scope)}, pass {len(rows) - len(failing_seed_ids) - len(out_scope)}, fail {len(failing_seed_ids)}; "
          f"policies {len(pols)}, fail {len(pol_fails)}; gold mismatches {len(mism)}; "
          f"proposed tools {len(proposals)}; sim missing {list(sim_missing)}")
    print(f"wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
