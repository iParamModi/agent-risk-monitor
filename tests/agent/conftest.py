"""Shared pytest setup for the agent tests: live Groq tests are skipped unless LMA_LIVE=1."""
import os

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "live: calls the real Groq API (run with LMA_LIVE=1)")


def pytest_collection_modifyitems(config, items):
    if os.getenv("LMA_LIVE") == "1":
        return
    skip = pytest.mark.skip(reason="live Groq test; set LMA_LIVE=1 to run")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip)
