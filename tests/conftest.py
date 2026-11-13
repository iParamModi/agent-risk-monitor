"""Test-wide safety (CLAUDE.md, Cost safety): pytest never touches a real account.

- If ALLOW_PAID_CALLS is set in the shell that runs pytest, every test fails: unset it before running the tests.
  (Single tests may still monkeypatch it to test the cost guard; that never leaves the test.)
- Real network is blocked in every test: only loopback addresses and Unix sockets may connect, and name lookups
  of anything but localhost fail. Real-account checks go only through scripts/smoke_deployed.py, never pytest.
"""
import ipaddress
import os
import socket

import pytest

APPROVAL_VAR = "ALLOW_PAID_CALLS"
LOCAL_NAMES = {"localhost", "localhost.localdomain", "testserver", "ip6-localhost", "ip6-loopback"}


class NetworkBlocked(RuntimeError):
    pass


def is_local(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode()
    host = str(host).strip("[]")
    if host in LOCAL_NAMES or host == "":
        return True
    try:
        return ipaddress.ip_address(host.split("%")[0]).is_loopback
    except ValueError:
        return False


def approval_problem(env=os.environ) -> str | None:
    if env.get(APPROVAL_VAR):
        return (f"{APPROVAL_VAR} is set in the shell running pytest. Tests must never run with real-account "
                f"approval: unset {APPROVAL_VAR} and run pytest again.")
    return None


_SHELL_PROBLEM = approval_problem()          # read once, before any test can monkeypatch the variable


@pytest.fixture(autouse=True, scope="session")
def _no_real_account_approval():
    if _SHELL_PROBLEM:
        pytest.fail(_SHELL_PROBLEM, pytrace=False)


@pytest.fixture(autouse=True)
def _block_real_network(monkeypatch):
    real_connect, real_connect_ex = socket.socket.connect, socket.socket.connect_ex
    real_getaddrinfo = socket.getaddrinfo

    def check(sock, address):
        if sock.family == getattr(socket, "AF_UNIX", object()):
            return
        host = address[0] if isinstance(address, tuple) else address
        if not is_local(host):
            raise NetworkBlocked(f"pytest blocks real network access (connect to {address!r}); see tests/conftest.py")

    def connect(self, address):
        check(self, address)
        return real_connect(self, address)

    def connect_ex(self, address):
        check(self, address)
        return real_connect_ex(self, address)

    def getaddrinfo(host, *args, **kwargs):
        if not is_local(host):
            raise NetworkBlocked(f"pytest blocks real network access (lookup of {host!r}); see tests/conftest.py")
        return real_getaddrinfo(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(socket.socket, "connect_ex", connect_ex)
    monkeypatch.setattr(socket, "getaddrinfo", getaddrinfo)
    yield
