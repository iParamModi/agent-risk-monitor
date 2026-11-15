"""The container files of the public site (deploy/, requirements-server.txt): replay only, no secret, not root.

Static checks plus one run of the app from the image's own file tree (the Dockerfile's COPY lines replayed into a
temp folder), so a new file the replay site starts to read cannot be forgotten in the image. Nothing here builds or
runs a container, and nothing touches a real account.
"""
import inspect
import json
import os
import re
import shutil
import subprocess
import sys

import yaml
from fastapi.testclient import TestClient

from src.common.io import REPO_ROOT
from src.common.secret_scan import find_secrets
from src.service.app import create_app
from src.service.cost_guard import APPROVAL_VAR, APPROVED

DEPLOY = REPO_ROOT / "deploy"
DOCKERFILE = DEPLOY / "Dockerfile"
IGNORE = DEPLOY / "Dockerfile.dockerignore"
COMPOSE = DEPLOY / "docker-compose.yml"
CADDYFILE = DEPLOY / "Caddyfile"
ENV_EXAMPLE = DEPLOY / ".env.example"
REQUIREMENTS = REPO_ROOT / "requirements-server.txt"
ENV_NAMES = {"DOMAIN", "LIVE_MODE", "LIVE_PASSWORD", APPROVAL_VAR, "GROQ_API_KEY", "MODAL_URL", "MODAL_TOKEN"}
LIVE_ONLY = {"LIVE_PASSWORD", APPROVAL_VAR, "GROQ_API_KEY", "MODAL_URL", "MODAL_TOKEN"}
NEVER_IN_IMAGE = ("torch", "vllm", "transformers", "sentence-transformers", "bitsandbytes", "nvidia", "cuda",
                  "accelerate", "peft", "modal")
LIVE_ENV = ("LIVE_MODE", "LIVE_PASSWORD", APPROVAL_VAR)


def copies() -> list[tuple[str, str]]:
    return re.findall(r"^COPY (\S+) (\S+)$", DOCKERFILE.read_text(encoding="utf-8"), flags=re.MULTILINE)


def compose() -> dict:
    return yaml.safe_load(COMPOSE.read_text(encoding="utf-8"))


# --- Dockerfile

def test_image_does_not_run_as_root():
    users = re.findall(r"^USER (\S+)$", DOCKERFILE.read_text(encoding="utf-8"), flags=re.MULTILINE)
    assert users, "the Dockerfile sets no USER"
    uid = users[-1].split(":")[0]
    assert uid.isdigit() and int(uid) > 0, f"the last USER must be a numeric non-root id, got {users[-1]}"


def test_base_image_is_pinned_and_multi_arch():
    text = DOCKERFILE.read_text(encoding="utf-8")
    bases = re.findall(r"^FROM (\S+)", text, flags=re.MULTILINE)
    assert bases and all(":" in b and not b.endswith(":latest") for b in bases)
    assert "--platform" not in text, "no fixed platform: the same file builds arm64 on the VM and amd64 on a laptop"
    assert "--only-binary=:all:" in text, "wheels only: the image has no compiler"


def test_image_copies_only_tracked_replay_files():
    tracked = subprocess.run(["git", "ls-files"], cwd=REPO_ROOT, capture_output=True, text=True, check=True).stdout
    tracked = tracked.splitlines()
    assert copies()
    for source, _ in copies():
        assert not source.startswith((".", "/", "ops", "data")) and ".env" not in source, source
        name = source.rstrip("/")
        assert name in tracked or any(t.startswith(name + "/") for t in tracked), f"COPY {source}: not in git"


def test_build_context_is_an_allow_list_that_lets_the_copies_in():
    lines = [x.strip() for x in IGNORE.read_text(encoding="utf-8").splitlines() if x.strip() and not x.startswith("#")]
    assert lines[0] == "*", "the ignore file must start by excluding everything"
    allowed = {x[1:].rstrip("/") for x in lines if x.startswith("!")}
    assert "**/.env" in lines and "ops" not in allowed and "data" not in allowed and ".git" not in allowed
    for source, _ in copies():
        assert source.rstrip("/") in allowed, f"COPY {source} is not let through by {IGNORE.name}"


def test_server_requirements_are_pinned_and_have_no_model_stack():
    lines = [x.split("#")[0].strip() for x in REQUIREMENTS.read_text(encoding="utf-8").splitlines()]
    packages = [x for x in lines if x]
    assert packages and all(re.fullmatch(r"[A-Za-z0-9_.-]+==[0-9][A-Za-z0-9.]*", p) for p in packages), packages
    names = {p.split("==")[0].lower() for p in packages}
    assert not [n for n in names if any(bad in n for bad in NEVER_IN_IMAGE)]
    assert {"fastapi", "uvicorn"} <= names


# --- docker-compose.yml

def test_compose_has_the_app_and_caddy_and_both_restart():
    services = compose()["services"]
    assert set(services) == {"app", "caddy"}
    assert all(s["restart"] == "unless-stopped" for s in services.values())
    assert services["app"]["build"] == {"context": "..", "dockerfile": "deploy/Dockerfile"}
    assert services["caddy"]["depends_on"]["app"]["condition"] == "service_healthy"


def test_only_caddy_is_public():
    services = compose()["services"]
    assert services["app"]["ports"] == ["127.0.0.1:8000:8000"]
    assert [p.rsplit(":", 1)[1] for p in services["caddy"]["ports"]] == ["80", "443"]


def test_app_container_is_locked_down():
    app = compose()["services"]["app"]
    assert app["read_only"] is True and app["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in app["security_opt"]
    assert not str(app["user"]).startswith(("0:", "root"))
    targets = {v.split(":")[1] for v in app["volumes"]}
    assert targets == {"/app/outputs/live", "/app/ops"}


def test_replay_compose_passes_no_live_variable_and_no_value():
    """Replay only: the app container gets LIVE_MODE (default off) and nothing else. Part G changes this test."""
    services = compose()["services"]
    assert services["app"]["environment"] == {"LIVE_MODE": "${LIVE_MODE:-off}"}
    assert "env_file" not in services["app"] and "env_file" not in services["caddy"]
    assert set(services["caddy"]["environment"]) == {"DOMAIN"}
    text = COMPOSE.read_text(encoding="utf-8")
    code = "\n".join(line.split("#")[0] for line in text.splitlines())
    assert not [name for name in LIVE_ONLY if name in code]


# --- Caddyfile

def test_caddy_serves_the_domain_and_does_not_buffer_the_sse_route():
    text = CADDYFILE.read_text(encoding="utf-8")
    assert re.search(r"^\{\$DOMAIN\} \{$", text, flags=re.MULTILINE), "the site address must be {$DOMAIN}"
    matcher = re.search(r"^\t@sse path (\S+)$", text, flags=re.MULTILINE)
    assert matcher, "no @sse matcher"
    routes = {route.path for route in create_app().routes}
    assert matcher.group(1) in routes, f"{matcher.group(1)} is not a route of the app"
    block = re.search(r"^\thandle @sse \{\n(.*?)^\t\}$", text, flags=re.MULTILINE | re.DOTALL)
    assert block and "flush_interval -1" in block.group(1) and "encode" not in block.group(1)
    assert text.count("reverse_proxy app:8000") == 2


# --- .env.example and secrets

def test_env_example_has_every_name_and_no_value():
    lines = [x.strip() for x in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines()]
    pairs = [x for x in lines if x and not x.startswith("#")]
    assert all(re.fullmatch(r"[A-Z][A-Z0-9_]*=", x) for x in pairs), "names only: every line must end with ="
    assert ENV_NAMES <= {x[:-1] for x in pairs}


def test_deploy_files_hold_no_secret_and_never_the_approval_value():
    # tracked files only: the real deploy/.env on the VM is never opened, not even by a test
    tracked = subprocess.run(["git", "ls-files", "deploy", REQUIREMENTS.name], cwd=REPO_ROOT, capture_output=True,
                             text=True, check=True).stdout.split()
    assert {"deploy/.env.example", "deploy/Dockerfile", "deploy/docker-compose.yml", "deploy/Caddyfile"} <= set(tracked)
    assert "deploy/.env" not in tracked
    for path in [REPO_ROOT / name for name in tracked]:
        text = path.read_text(encoding="utf-8")
        assert not find_secrets(text), path.name
        assert APPROVED not in text, f"{path.name} must never hold the approval value"
    ignored = subprocess.run(["git", "check-ignore", "deploy/.env"], cwd=REPO_ROOT, capture_output=True, text=True)
    assert ignored.returncode == 0, "deploy/.env must be git-ignored"


# --- the app from the image's file tree

def answers(client) -> dict:
    paths = ["/health", "/api/tasks", "/api/runs", "/api/results", "/api/team"]
    for r in client.get("/api/runs").json():
        paths += [f"/api/runs/{r['source']}/{r['run_id']}", f"/api/runs/{r['source']}/{r['run_id']}/state"]
    out = {p: client.get(p).json() for p in paths}
    out["pages"] = [client.get(p).status_code for p in ("/", "/replay", "/report.pdf")]
    out["live"] = [client.post("/api/live/run", json={}).status_code, client.get("/api/live/events").status_code]
    return out


IN_IMAGE = """
import json
from fastapi.testclient import TestClient
from src.service.app import create_app
from tests_helper import answers
print(json.dumps(answers(TestClient(create_app()))))
"""


def test_replay_site_works_from_the_image_file_tree(tmp_path, monkeypatch):
    for name in LIVE_ENV:
        monkeypatch.delenv(name, raising=False)
    image = tmp_path / "app"
    for source, target in copies():
        src, dst = REPO_ROOT / source, image / target
        if src.is_dir():
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
        else:
            folder = dst if target.endswith("/") else dst.parent
            folder.mkdir(parents=True, exist_ok=True)
            shutil.copy(src, folder / src.name)
    assert not list(image.rglob(".env*")), "an env file reached the image tree"
    (image / "tests_helper.py").write_text(inspect.getsource(answers), encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k not in LIVE_ENV and k != "PYTHONPATH"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    done = subprocess.run([sys.executable, "-c", IN_IMAGE], cwd=image, env=env, capture_output=True, text=True,
                          timeout=180)
    assert done.returncode == 0, done.stderr[-2000:]
    from_image = json.loads(done.stdout.splitlines()[-1])
    here = answers(TestClient(create_app()))
    assert from_image["/health"] == {"status": "ok", "mode": "replay", "live_mode": False, "live_available": False}
    assert from_image["pages"] == [200, 200, 200] and from_image["live"] == [403, 403]
    assert len(from_image["/api/runs"]) == len(here["/api/runs"]) >= 14
    assert from_image == json.loads(json.dumps(here))
