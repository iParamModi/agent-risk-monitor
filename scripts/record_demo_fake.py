"""Record the demo PLAN on CPU with the rule-based FAKE monitor and the scripted agent: logs to build and test the
replay website before the real Kaggle runs arrive. No GPU, no API, no real account.

    python scripts/record_demo_fake.py            # -> outputs/live/demo/fake/

Every log says meta.fake_monitor = true and agent = scripted; the website shows a FAKE MONITOR banner on them.
The real runs (kaggle/demo_record/demo_record.ipynb) are unpacked into outputs/live/demo/ itself.
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from lma_agent.tasks.load_tasks import load_tasks  # noqa: E402
from src.live.demo_record import PLAN, record_plan  # noqa: E402
from src.live.fake_monitor import RuleFakeMonitor  # noqa: E402
from src.live.monitor_gate import KeywordOnlyEmbedder  # noqa: E402

FAKE_DIR = ROOT / "outputs" / "live" / "demo" / "fake"


def main(argv=None) -> list[dict]:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(FAKE_DIR))
    args = ap.parse_args(argv)
    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)                       # one consistent set of fake runs
    tasks = {t.task_id: t for t in load_tasks(ROOT / "lma_agent" / "tasks" / "demo_tasks.yaml")}
    rows = record_plan(PLAN, tasks, out_dir=out, model=RuleFakeMonitor(), embedder=KeywordOnlyEmbedder(), groq=None,
                       base_meta={"fake_monitor": True, "recorded_on": "local CPU", "embedder": "keyword"},
                       log=lambda m: None)
    for r in rows:
        print(f"{r['task']:13s} {r['setting']:9s} confirm {r['confirm']:3s} {r['decision']:16s} "
              f"checks {r['checks_used']} | {'reused ' + r['reused_trajectory_from'] if r.get('reused_trajectory_from') else 'own episode'}")
    return rows


if __name__ == "__main__":
    main()
