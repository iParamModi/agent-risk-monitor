"""Static copy of the replay website: a public link with no server (GitHub Pages), while the Oracle VM waits.

    python scripts/export_static.py                  # writes site/ and checks it
    python scripts/export_static.py --with-report    # also copies the final report PDF (see below)
    python scripts/export_static.py --check-only     # only checks the site/ that is already there
    cd site && python -m http.server 8000            # then open http://127.0.0.1:8000/

It asks the replay app (src/service/app.py, in this process, no network) for every answer the pages read and writes
each one as a JSON file. The pages are the same two files the server sends, with data-static="1" on <html>; with it
they read the files instead of the API (apiUrl() in workspace.html), using only relative links, so the site also
works under a path such as https://<user>.github.io/<repo>/.

    index.html, replay.html                       the workspace and the event timeline
    health.json                                   mode "static", live_available false
    api/runs.json, api/tasks.json, api/results.json, api/team.json
    api/runs/<source>/<run>.json                  one run's summary and events
    api/runs/<source>/<run>/state/<N>.json        the company after step N, for every step of the run
    report.pdf                                    only with --with-report
    .nojekyll                                     tells GitHub Pages to publish the files as they are

Live mode is not in the static site: there is no server to run it, the pages show "Live demo: available on
request", and they never send a live request. No real account is touched here (CLAUDE.md, Cost safety: Tier A).

What is changed on the way out (the logs in outputs/live/demo/ stay as recorded):
    - the adapter's folder on the recording machine (/kaggle/input/...) is replaced by "(private adapter folder)";
    - the field adapter_dataset (the recording account's dataset name) is dropped.
The report PDF is left out unless --with-report is given: it names the team's private repository.

check_site() then reads every file of the folder and reports anything that is not public demo data: a file that
is not in the list above (.env, a ledger, a log of a failed try), a key or token, the approval variable, a path on
somebody's machine, an account name, an email outside the fictional company, a link to another site.
tests/test_static_export.py runs the export and this check, and plants each kind of problem to see it caught.

To publish again after a change: rerun this script, then commit and push the publishing repository. A `.git`
folder inside site/ is kept, so site/ itself can be that repository's working copy.
"""
import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import parse_qs

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.common.secret_scan import find_secrets  # noqa: E402
from src.service.app import RUN_ID, STATIC, create_app, default_sources, read_log  # noqa: E402
from src.service.cost_guard import APPROVAL_VAR, APPROVED  # noqa: E402
from src.service.results import REPORT_PDF  # noqa: E402

OUT = ROOT / "site"
PAGES = {"index.html": "workspace.html", "replay.html": "replay.html"}
HEALTH = {"status": "ok", "mode": "static", "live_mode": False, "live_available": False}
OWNED = ("index.html", "replay.html", "report.pdf", "health.json", ".nojekyll", "api")   # all this script writes
KEPT = (".git",)                                    # the publishing repository, when site/ is its working copy
MAX_BYTES = 5_000_000

# --- what is changed on the way out
KAGGLE_PATH = re.compile(r"/kaggle/[^\s\"'+,;)]*")
NO_PATH = "(private adapter folder)"
DROPPED_KEYS = ("adapter_dataset",)


def public(value, counts: dict | None = None):
    """The same JSON value without the recording machine's folders and the recording account's dataset name."""
    counts = counts if counts is not None else {}
    if isinstance(value, dict):
        counts["fields dropped"] = counts.get("fields dropped", 0) + sum(k in DROPPED_KEYS for k in value)
        return {k: public(v, counts) for k, v in value.items() if k not in DROPPED_KEYS}
    if isinstance(value, list):
        return [public(v, counts) for v in value]
    if isinstance(value, str):
        clean, n = KAGGLE_PATH.subn(NO_PATH, value)
        counts["folders removed"] = counts.get("folders removed", 0) + n
        return clean
    return value


def file_for(api_path: str) -> str:
    """The file that answers an API path in the static site. The same rule as apiUrl() in workspace.html."""
    path, _, query = api_path.partition("?")
    step = parse_qs(query).get("step")
    return (f"{path}/{step[0]}" if step else path) + ".json"


def static_page(html: str) -> str:
    out, n = re.subn(r"<html\b", '<html data-static="1"', html, count=1)
    if n != 1 or "dataset.static" not in html:
        raise SystemExit("a page has no <html> tag or no static mode (document.documentElement.dataset.static)")
    return out


def build(with_report: bool = False, sources: dict[str, Path] | None = None) -> tuple[dict[str, bytes], dict]:
    """{file name: content} of the whole site, and how many values were changed on the way out."""
    from fastapi.testclient import TestClient
    client, counts, files = TestClient(create_app(sources)), {}, {}

    def get(path: str):
        res = client.get("/" + path)
        if res.status_code != 200:
            raise SystemExit(f"GET /{path} answered {res.status_code}: {res.text[:200]}")
        return res.json()

    def put(path: str, value):
        files[file_for(path)] = json.dumps(public(value, counts), ensure_ascii=False).encode("utf-8")

    for name, source in PAGES.items():
        files[name] = static_page((STATIC / source).read_text(encoding="utf-8")).encode("utf-8")
    files[".nojekyll"] = b""
    files["health.json"] = json.dumps(HEALTH).encode("utf-8")
    put("api/tasks", get("api/tasks"))
    put("api/team", get("api/team"))
    results = get("api/results")
    report = ROOT / REPORT_PDF
    if with_report:
        if not report.is_file():
            raise SystemExit(f"--with-report: {REPORT_PDF} is not in this checkout")
        files["report.pdf"] = report.read_bytes()
    else:
        results["report"] = None                    # the Results page shows the PDF link only when this is set
    put("api/results", results)
    runs = get("api/runs")
    put("api/runs", runs)
    for run in runs:
        base = f"api/runs/{run['source']}/{run['run_id']}"
        data = get(base)
        put(base, data)
        if not any(e["type"] == "company_snapshot" for e in data["events"]):
            continue                                # a log from before 13 Nov has no company to show
        for step in range(max((e.get("step") or 0) for e in data["events"]) + 1):
            put(f"{base}/state?step={step}", get(f"{base}/state?step={step}"))
    return files, counts


def write_site(out: Path, files: dict[str, bytes]) -> None:
    """Replaces what this script wrote before. Stops if the folder holds anything else, so nothing foreign is
    deleted and nothing foreign is published."""
    out.mkdir(parents=True, exist_ok=True)
    foreign = sorted(p.name for p in out.iterdir() if p.name not in OWNED + KEPT)
    if foreign:
        raise SystemExit(f"{out} holds files this script did not write: {foreign}. Use an empty folder.")
    for name in OWNED:
        path = out / name
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path)
        elif path.exists() or path.is_symlink():
            path.unlink()
    for name, content in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


# --- the check: only public demo data

_NAME = RUN_ID.pattern.strip("^$")
ALLOWED = tuple(re.compile(p) for p in (
    r"index\.html", r"replay\.html", r"report\.pdf", r"\.nojekyll", r"health\.json",
    r"api/(runs|tasks|results|team)\.json",
    rf"api/runs/[a-z]+/{_NAME}\.json",
    rf"api/runs/[a-z]+/{_NAME}/state/\d+\.json",
))
PRIVATE = {
    "real-account approval value": re.compile(re.escape(APPROVED)),
    "approval variable": re.compile(re.escape(APPROVAL_VAR)),
    "secret env name with a value": re.compile(r"(GROQ_API_KEY|MODAL_TOKEN_\w+|LIVE_PASSWORD|HF_TOKEN|KAGGLE_KEY)\W+\w{8,}"),
    "path on somebody's machine": re.compile(
        r"/(?:home|Users|root|kaggle|tmp|mnt|content|workspace)/[A-Za-z0-9_.-]+|\b[A-Za-z]:\\\\?(?:Users|Documents)\b"),
    "cost ledger": re.compile(r"(?i)cost_ledger|ledger\.csv"),
    ".env file": re.compile(r"(?<![\w.])\.env\b"),
    "recording account's dataset field": re.compile(r"adapter_dataset"),
    "email outside the fictional company": re.compile(
        r"[A-Za-z0-9._%+-]+@(?:[A-Za-z0-9-]+\.)+(?!example\b)[A-Za-z]{2,}\b"),
    "link to another site": re.compile(r"https?://[^\s\"'<>)]+"),
}


def account_names(sources: dict[str, Path] | None = None) -> set[str]:
    """Names that point at a teammate's account: the adapter dataset of every recorded run and its owner."""
    names = set()
    for folder in (sources if sources is not None else default_sources()).values():
        for path in sorted(Path(folder).glob("*.jsonl")):
            for event in read_log(path):
                dataset = (event.get("payload") or {}).get("meta", {}).get("adapter_dataset") if event.get("type") == "instruction" else None
                if dataset:
                    names |= {str(dataset), str(dataset).split("/")[0]}
    return {n for n in names if len(n) >= 4}


def check_site(out: Path, sources: dict[str, Path] | None = None) -> list[str]:
    """Every reason the folder is not safe to publish; [] when it holds only public demo data."""
    out, problems = Path(out), []
    if not (out / "index.html").is_file():
        return [f"{out}: no index.html, this is not an exported site"]
    names = account_names(sources)
    files = sorted(p for p in out.rglob("*") if p.relative_to(out).parts[0] not in KEPT and not p.is_dir())
    for path in files:
        rel = path.relative_to(out).as_posix()
        if path.is_symlink():
            problems.append(f"{rel}: a link to another file, not a file")
            continue
        if not any(p.fullmatch(rel) for p in ALLOWED):
            problems.append(f"{rel}: not a file of the static site")
            continue
        if path.stat().st_size > MAX_BYTES:
            problems.append(f"{rel}: larger than {MAX_BYTES} bytes")
        if path.suffix == ".pdf":
            report = ROOT / REPORT_PDF
            if not path.read_bytes().startswith(b"%PDF") or not report.is_file() or path.read_bytes() != report.read_bytes():
                problems.append(f"{rel}: not the report in {REPORT_PDF}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        problems += [f"{rel}: {what} ({found})" for what, found in find_secrets(text, extra=PRIVATE)]
        problems += [f"{rel}: account name {name}" for name in sorted(names) if name.lower() in text.lower()]
        if path.suffix == ".json":
            try:
                json.loads(text)
            except ValueError:
                problems.append(f"{rel}: not valid JSON")
    for name in PAGES:
        page = out / name
        if page.is_file() and 'data-static="1"' not in page.read_text(encoding="utf-8", errors="replace")[:400]:
            problems.append(f"{name}: static mode is not switched on (it would call a server that is not there)")
    try:
        health = json.loads((out / "health.json").read_text(encoding="utf-8"))
        listed = {f"api/runs/{r['source']}/{r['run_id']}.json" for r in json.loads((out / "api/runs.json").read_text(encoding="utf-8"))}
    except (OSError, ValueError, KeyError, TypeError) as err:
        return problems + [f"health.json or api/runs.json cannot be read: {err}"]
    if health.get("live_available") or health.get("live_mode"):
        problems.append("health.json: live mode must be off in the static site")
    there = {p.relative_to(out).as_posix() for p in files if re.fullmatch(rf"api/runs/[a-z]+/{_NAME}\.json", p.relative_to(out).as_posix())}
    problems += [f"{f}: listed in api/runs.json but missing" for f in sorted(listed - there)]
    problems += [f"{f}: a run that api/runs.json does not list" for f in sorted(there - listed)]
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, default=OUT, help="folder to write (default: site/)")
    parser.add_argument("--with-report", action="store_true", help=f"also copy {REPORT_PDF} as report.pdf")
    parser.add_argument("--check-only", action="store_true", help="do not write, only check the folder")
    args = parser.parse_args()
    out = args.out.resolve()
    if not args.check_only:
        files, counts = build(with_report=args.with_report)
        write_site(out, files)
        runs = sum(1 for f in files if re.fullmatch(rf"api/runs/[a-z]+/{_NAME}\.json", f))
        print(f"wrote {len(files)} files, {sum(map(len, files.values())):,} bytes, {runs} runs -> {out}")
        print(f"changed on the way out: {counts.get('folders removed', 0)} machine folders removed, "
              f"{counts.get('fields dropped', 0)} adapter_dataset fields dropped")
        print("report.pdf: " + ("copied" if args.with_report else "left out (add --with-report to publish it)"))
    problems = check_site(out)
    if problems:
        print(f"NOT SAFE TO PUBLISH: {len(problems)} problem(s)")
        for line in problems:
            print("  " + line)
        raise SystemExit(1)
    print("check passed: only public demo data, no key, no .env, no ledger, no private path")


if __name__ == "__main__":
    main()
