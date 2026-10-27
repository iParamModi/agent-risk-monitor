"""Fails if test.jsonl / ood_test.jsonl change (PLAN Step 11, decisions.md R11.3).

The hashes are in data/LOCKED_TEST.sha256 (written by python -m src.data_gen.split). A deliberate change to a
test file needs `python -m src.data_gen.split --relock` and a Changelog row in docs/decisions.md.
"""
from src.common.io import REPO_ROOT
from src.data_gen.split import LOCK, LOCKED_FILES, read_lock, sha256


def test_lock_covers_both_test_files():
    assert set(read_lock(LOCK)) == {f"data/records/{name}" for name in LOCKED_FILES}


def test_locked_files_are_unchanged():
    for rel, digest in read_lock(LOCK).items():
        assert sha256(REPO_ROOT / rel) == digest, f"{rel} changed after it was locked"
