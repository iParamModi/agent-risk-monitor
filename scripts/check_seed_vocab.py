"""Checks every seed's actions and read tools against the shared company vocabulary.

Run: python scripts/check_seed_vocab.py
Prints one line per mismatch and exits 1 if any are left. The list below is the contract
lma_agent (the demo company) is being changed to follow; see docs/seed_cleanup.md.
"""
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

# action -> (required args, optional args)
ACTIONS = {
    "delete_file": ({"file"}, set()),
    "edit_file": ({"file"}, {"content"}),
    "move_file": ({"file", "to"}, set()),
    "share_file": ({"file", "with"}, set()),
    "write_cells": ({"file", "cells", "content"}, set()),
    "send_email": ({"to", "subject"}, {"body", "attachment"}),
    "grant_permission": ({"user", "resource", "level"}, set()),
    "revoke_permission": ({"user", "resource"}, {"level"}),
    "transfer_money": ({"from_account", "to_account", "amount_inr"}, set()),
    "delete_repository": ({"repo"}, set()),
    "archive_repository": ({"repo"}, set()),
    "create_event": ({"title", "attendees"}, set()),
    "archive_record": ({"customer_id"}, set()),
    "export_customer_data": ({"customer_id", "destination"}, set()),
    # phase 2 write tools
    "cancel_event": ({"event_id"}, set()),
    "forward_email": ({"email_id", "to"}, set()),
    "delete_folder": ({"folder"}, set()),
    "upload_file": ({"file"}, {"content"}),
    "unshare_file": ({"file"}, {"with"}),
    "create_share_link": ({"file"}, set()),
    "delete_user": ({"user"}, set()),
    "reset_password": ({"user"}, set()),
    "pay_bill": ({"account", "payee", "amount_inr"}, set()),
    "send_message": ({"to", "body"}, set()),
}
READS = {
    "list_files": {"folder"},
    "get_file_info": {"file"},
    "read_file": {"file"},
    "lookup_contact": {"contact"},
    "get_user": {"user"},
    "list_permissions": {"resource"},
    "get_account": {"account"},
    "get_repo": {"repo"},
    "read_inbox": set(),
    "get_customer_record": {"customer_id"},
    # phase 2 read tools
    "search_files": {"query"},
    "list_repos": set(),
    "list_transactions": {"account"},
}


def check_action(where: str, action: dict) -> list[str]:
    name, args = action["name"], set((action.get("args") or {}).keys())
    if name not in ACTIONS:
        return [f"{where}: unknown action `{name}`"]
    out = []
    if "requested_by" in args:
        out.append(f"{where}: `requested_by` is not a tool argument")
        args.discard("requested_by")
    required, optional = ACTIONS[name]
    if not required <= args or not args <= required | optional:
        want = sorted(required) + [f"{o}?" for o in sorted(optional)]
        out.append(f"{where}: `{name}` args {sorted(args)} -> {want}")
    return out


def check_seed(seed: dict) -> list[str]:
    out = check_action("proposed_action", seed["proposed_action"])
    for key, sub in (seed.get("t2_subtypes") or {}).items():
        if not sub:
            continue
        if sub.get("later_write"):
            out += check_action(f"t2.{key}.later_write", sub["later_write"])
        read = sub.get("earlier_read")
        if read:
            args = set(read) - {"tool"}
            if read["tool"] not in READS:
                out.append(f"t2.{key}.earlier_read: unknown read tool `{read['tool']}`")
            elif args != READS[read["tool"]]:
                out.append(f"t2.{key}.earlier_read: `{read['tool']}` args {sorted(args)} -> {sorted(READS[read['tool']])}")
    return out


def main() -> int:
    n_bad = 0
    for path in sorted((ROOT / "data" / "seeds").glob("*/*.yaml")):
        seed = yaml.safe_load(path.read_text(encoding="utf-8"))
        problems = check_seed(seed)
        n_bad += bool(problems)
        for p in problems:
            print(f"{seed['seed_id']} | {p}")
    print(f"{n_bad} seeds with problems")
    return 1 if n_bad else 0


if __name__ == "__main__":
    sys.exit(main())
