"""Cost guard for anything that can reach a real account (Modal, Oracle, Groq). Rules: docs/DEPLOYMENT_RULES.md.

    require_paid_ok("groq agent: demo_hidden", "B", 0.0, service="groq", command="python scripts/run_live.py ...")

- raises PaidCallBlocked unless ALLOW_PAID_CALLS is exactly PRATEEK_APPROVED in the environment (only Prateek sets
  it, on his own machine; code never sets it),
- always raises for Tier C ("ask Prateek"),
- for Tier B: raises if the action's estimated max is above $0.50 or the month's ledger total including it would be
  above $10, otherwise appends the row to ops/cost_ledger.csv (git-ignored) BEFORE the action runs.
Tier A (local, free) needs no guard.
"""
import csv
import os
from datetime import datetime, timezone
from pathlib import Path

from src.common.io import REPO_ROOT

APPROVAL_VAR = "ALLOW_PAID_CALLS"
APPROVED = "PRATEEK_APPROVED"
MAX_ACTION_USD = 0.50
MAX_MONTH_USD = 10.0
LEDGER = REPO_ROOT / "ops" / "cost_ledger.csv"
FIELDS = ["date", "action", "command", "service", "unit_price", "price_source", "max_runtime_s", "est_max_usd",
          "month_total_usd", "tier", "actual_usd"]


class PaidCallBlocked(RuntimeError):
    pass


def approved() -> bool:
    return os.environ.get(APPROVAL_VAR) == APPROVED


def month_total(month: str, ledger: Path = LEDGER) -> float:
    """Sum of est_max_usd (or actual_usd when filled) of the ledger rows of month YYYY-MM."""
    if not Path(ledger).exists():
        return 0.0
    total = 0.0
    with open(ledger, newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if (row.get("date") or "").startswith(month):
                value = row.get("actual_usd") or row.get("est_max_usd") or "0"
                try:
                    total += float(value)
                except ValueError:
                    raise PaidCallBlocked(f"ledger row with an unreadable cost: {row}; fix {ledger} first")
    return total


def require_paid_ok(action: str, tier: str, est_usd: float, *, command: str = "", service: str = "",
                    unit_price: str = "", price_source: str = "", max_runtime_s: float | str = "",
                    ledger: Path = LEDGER, now: datetime | None = None) -> dict:
    """Allow a real-account action or raise PaidCallBlocked. Returns the ledger row it wrote."""
    if not approved():
        raise PaidCallBlocked(f"{action}: real accounts are off ({APPROVAL_VAR} is not approved). Ask Prateek.")
    tier = str(tier).upper()
    if tier == "C":
        raise PaidCallBlocked(f"{action}: Tier C, ask Prateek first (command, reason, estimated cost).")
    if tier != "B":
        raise PaidCallBlocked(f"{action}: unknown tier {tier!r}; real-account actions are Tier B or C")
    try:
        est = float(est_usd)
    except (TypeError, ValueError):
        raise PaidCallBlocked(f"{action}: no cost estimate, so it is Tier C. Ask Prateek.")
    if est < 0:
        raise PaidCallBlocked(f"{action}: negative cost estimate {est}")
    if est > MAX_ACTION_USD:
        raise PaidCallBlocked(f"{action}: estimated ${est:.2f} is above the ${MAX_ACTION_USD:.2f} cap. Ask Prateek.")
    now = now or datetime.now(timezone.utc)
    total = month_total(now.strftime("%Y-%m"), ledger) + est
    if total > MAX_MONTH_USD:
        raise PaidCallBlocked(f"{action}: month total would be ${total:.2f}, above ${MAX_MONTH_USD:.2f}. Ask Prateek.")
    row = {"date": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "action": action, "command": command, "service": service,
           "unit_price": unit_price, "price_source": price_source, "max_runtime_s": max_runtime_s,
           "est_max_usd": f"{est:.4f}", "month_total_usd": f"{total:.4f}", "tier": tier, "actual_usd": ""}
    ledger = Path(ledger)
    ledger.parent.mkdir(parents=True, exist_ok=True)
    new = not ledger.exists() or ledger.stat().st_size == 0
    with open(ledger, "a", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        if new:
            writer.writeheader()
        writer.writerow(row)
    return row
