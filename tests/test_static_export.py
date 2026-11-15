"""The static copy of the replay website (scripts/export_static.py): the same answers as the replay API, live mode
left out, and only public demo data in the folder: no key, no .env, no ledger, no private path, no failed tries."""
import json
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient

from scripts import export_static as ex
from src.common.io import REPO_ROOT
from src.service.app import STATIC, create_app
from src.service.cost_guard import APPROVAL_VAR, APPROVED
from src.service.results import REPORT_PDF

LIVE_ENV = ("LIVE_MODE", "LIVE_PASSWORD", APPROVAL_VAR)


@pytest.fixture(scope="module")
def built():
    return ex.build()


@pytest.fixture
def site(tmp_path, built):
    out = tmp_path / "site"
    ex.write_site(out, built[0])
    return out


@pytest.fixture
def client(monkeypatch):
    for name in LIVE_ENV:
        monkeypatch.delenv(name, raising=False)
    return TestClient(create_app())


def load(site, name):
    return json.loads((site / name).read_text(encoding="utf-8"))


# --- the export holds what the pages read, and nothing else

def test_export_passes_its_own_check(site):
    assert ex.check_site(site) == []


def test_file_list_is_pages_api_answers_and_nothing_else(site, client):
    runs = client.get("/api/runs").json()
    assert len(runs) == 14
    expected = {"index.html", "replay.html", ".nojekyll", "health.json",
                "api/runs.json", "api/tasks.json", "api/results.json", "api/team.json"}
    for r in runs:
        base = f"api/runs/{r['source']}/{r['run_id']}"
        events = client.get("/" + base).json()["events"]
        expected.add(base + ".json")
        expected |= {f"{base}/state/{n}.json" for n in range(max(e.get("step") or 0 for e in events) + 1)}
    assert {p.relative_to(site).as_posix() for p in site.rglob("*") if p.is_file()} == expected


def test_every_json_file_is_the_api_answer(site, client):
    """Byte for byte the API's JSON, after the two changes public() makes."""
    runs = client.get("/api/runs").json()
    assert load(site, "api/runs.json") == ex.public(runs)
    assert load(site, "api/tasks.json") == client.get("/api/tasks").json()
    assert load(site, "api/team.json") == client.get("/api/team").json()
    assert load(site, "api/results.json") == {**client.get("/api/results").json(), "report": None}
    states = 0
    for r in runs:
        base = f"api/runs/{r['source']}/{r['run_id']}"
        assert load(site, base + ".json") == ex.public(client.get("/" + base).json())
        for path in sorted((site / base / "state").glob("*.json")):
            api = client.get(f"/{base}/state", params={"step": path.stem})
            assert api.status_code == 200 and json.loads(path.read_text(encoding="utf-8")) == api.json()
            states += 1
    assert states >= 3 * len(runs)


def test_every_state_the_page_asks_for_is_there(site):
    """The workspace asks for the state after each step whose state_diff changed something."""
    asked = 0
    for r in load(site, "api/runs.json"):
        base = f"api/runs/{r['source']}/{r['run_id']}"
        for e in load(site, base + ".json")["events"]:
            if e["type"] == "state_diff" and e["payload"].get("changed"):
                assert (site / ex.file_for(f"{base}/state?step={e['step']}")).is_file()
                asked += 1
    assert asked >= 3


def test_failed_tries_are_not_exported(site):
    names = [p.relative_to(site).as_posix() for p in site.rglob("*")]
    assert not any("attempts" in n for n in names)
    assert not any(n.endswith((".csv", ".jsonl", ".env", ".md")) for n in names)


def test_machine_folder_and_account_name_are_removed(site, built):
    accounts = ex.account_names()
    assert accounts and any("/" in a for a in accounts)        # the real logs do name a dataset: the check is live
    assert built[1]["folders removed"] > 0 and built[1]["fields dropped"] == 7
    real = [r for r in load(site, "api/runs.json") if r["source"] == "real"]
    assert len(real) == 7 and all(r["monitor_model"] == "Qwen/Qwen3-8B+" + ex.NO_PATH for r in real)
    assert all(r["monitor_label"] == "Qwen3-8B + LoRA (Phase B)" for r in real)       # the page's label is kept
    for path in site.rglob("*.json"):
        text = path.read_text(encoding="utf-8")
        assert "/kaggle/" not in text and "adapter_dataset" not in text
        assert not any(a in text for a in accounts)


def test_recorded_logs_are_not_touched(built):
    """The changes are made on the way out only: the committed logs still say where the adapter was."""
    raw = "".join(p.read_text(encoding="utf-8") for p in (REPO_ROOT / "outputs/live/demo").glob("*.jsonl"))
    assert "/kaggle/input/" in raw and "adapter_dataset" in raw


# --- static mode: files instead of the API, live mode hidden

def test_pages_are_the_served_pages_with_static_mode_on(site):
    for name, source in ex.PAGES.items():
        served = (STATIC / source).read_text(encoding="utf-8")
        assert 'data-static="1"' not in served.split("<head>")[0]              # the server's pages stay as they are
        assert (site / name).read_text(encoding="utf-8") == served.replace("<html", '<html data-static="1"', 1)


def test_health_says_static_and_live_off(site):
    assert load(site, "health.json") == {"status": "ok", "mode": "static", "live_mode": False,
                                         "live_available": False}


def test_static_page_hides_live_mode():
    html = (STATIC / "workspace.html").read_text(encoding="utf-8")
    assert "Live demo: available on request" in html
    live_call = html[html.index("async function liveCall"):]
    assert live_call.index("if (STATIC_SITE) throw") < live_call.index("fetch(")   # no live request can be sent
    # every other request goes through api() -> apiUrl(): the only bare fetch left is the live one
    assert re.findall(r"fetch\(([\w.]+)", html) == ["apiUrl", "path"]
    replay = (STATIC / "replay.html").read_text(encoding="utf-8")
    assert re.findall(r"fetch\(([\w.]+)", replay) == ["apiUrl", "apiUrl"]


def test_pages_use_relative_links_only(site):
    """Works under https://<user>.github.io/<repo>/: nothing starts at the host's root, nothing loads from outside."""
    for name in ex.PAGES:
        html = (site / name).read_text(encoding="utf-8")
        assert not re.search(r"""(?:fetch\(|href=|src=)\s*[`"']/""", html)
        assert not re.search(r"https?://", html)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_python_and_page_name_the_same_file():
    """file_for() (which file is written) and apiUrl() in workspace.html (which file is read) are one rule."""
    html = (STATIC / "workspace.html").read_text(encoding="utf-8")
    function = re.search(r"function apiUrl\(path\) \{.*?\n\}", html, flags=re.S).group(0)
    paths = ["health", "api/runs", "api/tasks", "api/results", "api/team", "api/runs/real/demo_a__b.1-2",
             "api/runs/fake/demo_x/state?step=0", "api/runs/real/demo_x/state?step=12"]
    script = f"const STATIC_SITE = true;\n{function}\nconsole.log(JSON.stringify({json.dumps(paths)}.map(apiUrl)));"
    out = subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True, timeout=30).stdout
    assert json.loads(out) == [ex.file_for(p) for p in paths]
    off = f"const STATIC_SITE = false;\n{function}\nconsole.log(apiUrl('api/runs/a/b/state?step=2'));"
    assert subprocess.run(["node", "-e", off], capture_output=True, text=True, check=True,
                          timeout=30).stdout.strip() == "api/runs/a/b/state?step=2"


def test_file_names():
    assert ex.file_for("api/runs") == "api/runs.json" and ex.file_for("health") == "health.json"
    assert ex.file_for("api/runs/real/x/state?step=2") == "api/runs/real/x/state/2.json"


# --- the report PDF: only on request

def test_report_is_left_out_by_default_and_copied_on_request(tmp_path, built):
    assert "report.pdf" not in built[0]
    files, _ = ex.build(with_report=True)
    assert files["report.pdf"] == (REPO_ROOT / REPORT_PDF).read_bytes()
    assert json.loads(files["api/results.json"])["report"] == REPORT_PDF
    ex.write_site(tmp_path / "site", files)
    assert ex.check_site(tmp_path / "site") == []
    (tmp_path / "site" / "report.pdf").write_bytes(b"%PDF-1.5 something else")
    assert any("report.pdf" in p for p in ex.check_site(tmp_path / "site"))


# --- the check catches what must never be published

RUN_FILE = "api/runs/fake/demo_hidden__selective__scripted__20261114T105048Z.json"
PLANTED_FILES = {
    ".env": "GROQ_API_KEY=x\n",
    "cost_ledger.csv": "date,action\n",
    "ops/cost_ledger.csv": "date,action\n",
    "api/runs/real/attempts/demo_x__groq_try1.json": "{}",
    "api/runs/real/demo_x.jsonl": "{}\n",
    "notes.txt": "hello",
    "api/secret.json": "{}",
}
PLANTED_TEXT = {
    "Groq API key": "gsk_" + "a1B2c3D4e5F6g7H8i9J0k1L2",
    "Hugging Face token": "hf_" + "abcdefghijklmnopqrstuvwxyzABCDEF",
    "real-account approval value": APPROVED,
    "approval variable": APPROVAL_VAR,
    "secret env name with a value": "LIVE_PASSWORD=" + "correcthorse",
    "path on somebody's machine": "/home/someone/Lma_major/outputs",
    "path on somebody's machine (kaggle)": "/kaggle/input/datasets/owner/adapter",
    "path on somebody's machine (mac)": "/Users/someone/project",
    "cost ledger": "see ops/cost_ledger.csv",
    ".env file": "loaded from .env at start",
    "recording account's dataset field": '"adapter_dataset": "x"',
    "email outside the fictional company": "someone@gmail.com",
    "link to another site": "https://github.com/owner/private-repo",
}


@pytest.mark.parametrize("name", PLANTED_FILES)
def test_check_catches_a_file_that_is_not_part_of_the_site(site, name):
    (site / name).parent.mkdir(parents=True, exist_ok=True)
    (site / name).write_text(PLANTED_FILES[name], encoding="utf-8")
    problems = ex.check_site(site)
    assert any(p.startswith(name + ": not a file of the static site") for p in problems), problems


@pytest.mark.parametrize("what", PLANTED_TEXT)
def test_check_catches_private_text_in_a_run_file(site, what):
    data = load(site, RUN_FILE)
    data["events"][1]["payload"]["note"] = PLANTED_TEXT[what]
    (site / RUN_FILE).write_text(json.dumps(data), encoding="utf-8")
    problems = ex.check_site(site)
    assert any(p.startswith(f"{RUN_FILE}: {what.split(' (')[0]}") for p in problems), problems


def test_check_catches_an_account_name(site):
    name = sorted(ex.account_names())[0]
    (site / "api/tasks.json").write_text(json.dumps([{"id": "t", "note": name.upper()}]), encoding="utf-8")
    assert any("account name" in p for p in ex.check_site(site))


def test_check_keeps_the_fictional_company_emails(site):
    text = "".join(p.read_text(encoding="utf-8") for p in site.rglob("*.json"))
    assert "@northwind.example" in text                      # they are there, and the check above still passed


def test_check_catches_live_mode_a_server_page_and_run_list_drift(site):
    (site / "health.json").write_text(json.dumps({**ex.HEALTH, "live_available": True}), encoding="utf-8")
    shutil.copy(STATIC / "workspace.html", site / "index.html")
    (site / RUN_FILE).unlink()
    extra = site / "api/runs/real/demo_not_listed.json"
    extra.write_text("{}", encoding="utf-8")
    problems = "\n".join(ex.check_site(site))
    assert "live mode must be off" in problems and "static mode is not switched on" in problems
    assert f"{RUN_FILE}: listed in api/runs.json but missing" in problems
    assert "demo_not_listed.json: a run that api/runs.json does not list" in problems


def test_check_catches_a_link_and_an_empty_folder(tmp_path, site):
    (site / "api/team.json").unlink()
    (site / "api/team.json").symlink_to(REPO_ROOT / "PROGRESS.md")
    assert any("a link to another file" in p for p in ex.check_site(site))
    assert ex.check_site(tmp_path / "nothing") != []


# --- writing: only its own files, and the publishing repository is kept

def test_rewrite_keeps_git_and_removes_old_runs(site, built):
    (site / ".git").mkdir()
    (site / ".git" / "config").write_text("[remote]\n", encoding="utf-8")
    old = site / "api/runs/real/demo_old_run.json"
    old.write_text("{}", encoding="utf-8")
    ex.write_site(site, built[0])
    assert (site / ".git" / "config").read_text(encoding="utf-8") == "[remote]\n" and not old.exists()
    assert ex.check_site(site) == []                          # .git is not part of the published check


def test_write_refuses_a_folder_with_other_files(tmp_path, built):
    (tmp_path / "thesis.docx").write_text("mine", encoding="utf-8")
    with pytest.raises(SystemExit, match="did not write"):
        ex.write_site(tmp_path, built[0])
    assert (tmp_path / "thesis.docx").read_text(encoding="utf-8") == "mine" and not (tmp_path / "index.html").exists()


def test_site_folder_is_never_committed_to_the_private_repo():
    ignored = subprocess.run(["git", "check-ignore", "-q", "site/index.html"], cwd=REPO_ROOT)
    assert ignored.returncode == 0
