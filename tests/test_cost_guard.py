"""Cost guard (docs/DEPLOYMENT_RULES.md): real accounts only with Prateek's approval, Tier C never, caps hold."""
import csv
from datetime import datetime, timezone

import pytest

from src.service.cost_guard import APPROVAL_VAR, PaidCallBlocked, month_total, require_paid_ok

NOW = datetime(2026, 11, 12, tzinfo=timezone.utc)


@pytest.fixture
def approved(monkeypatch):
    monkeypatch.setenv(APPROVAL_VAR, "PRATEEK_APPROVED")


def test_blocks_when_the_variable_is_unset_or_wrong(tmp_path, monkeypatch):
    monkeypatch.delenv(APPROVAL_VAR, raising=False)
    with pytest.raises(PaidCallBlocked):
        require_paid_ok("x", "B", 0.0, ledger=tmp_path / "l.csv", now=NOW)
    monkeypatch.setenv(APPROVAL_VAR, "yes")
    with pytest.raises(PaidCallBlocked):
        require_paid_ok("x", "B", 0.0, ledger=tmp_path / "l.csv", now=NOW)
    assert not (tmp_path / "l.csv").exists()


def test_tier_c_always_blocks(tmp_path, approved):
    with pytest.raises(PaidCallBlocked, match="ask Prateek"):
        require_paid_ok("new VM", "C", 0.0, ledger=tmp_path / "l.csv", now=NOW)


def test_unknown_cost_blocks(tmp_path, approved):
    with pytest.raises(PaidCallBlocked):
        require_paid_ok("x", "B", None, ledger=tmp_path / "l.csv", now=NOW)


def test_action_cap(tmp_path, approved):
    with pytest.raises(PaidCallBlocked, match="0.50"):
        require_paid_ok("x", "B", 0.51, ledger=tmp_path / "l.csv", now=NOW)
    require_paid_ok("x", "B", 0.50, ledger=tmp_path / "l.csv", now=NOW)


def test_month_cap_counts_the_ledger(tmp_path, approved):
    ledger = tmp_path / "l.csv"
    for _ in range(19):
        require_paid_ok("modal run", "B", 0.50, ledger=ledger, now=NOW)
    assert month_total("2026-11", ledger) == pytest.approx(9.5)
    require_paid_ok("modal run", "B", 0.50, ledger=ledger, now=NOW)          # exactly 10.00
    with pytest.raises(PaidCallBlocked, match="month total"):
        require_paid_ok("modal run", "B", 0.01, ledger=ledger, now=NOW)
    # a new month starts from zero
    require_paid_ok("modal run", "B", 0.50, ledger=ledger, now=datetime(2026, 12, 1, tzinfo=timezone.utc))


def test_row_is_written_before_and_holds_the_fields(tmp_path, approved):
    ledger = tmp_path / "l.csv"
    require_paid_ok("groq task", "B", 0.0, command="python x.py", service="groq", unit_price="free",
                    price_source="https://example", max_runtime_s=60, ledger=ledger, now=NOW)
    (row,) = list(csv.DictReader(open(ledger)))
    assert row["action"] == "groq task" and row["tier"] == "B" and row["service"] == "groq"
    assert row["est_max_usd"] == "0.0000" and row["month_total_usd"] == "0.0000"
