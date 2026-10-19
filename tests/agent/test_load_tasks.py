from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from lma_agent.tasks.load_tasks import load_tasks
from lma_agent.tools.registry import SPECS


def test_smoke_tasks_load():
    tasks = load_tasks()
    assert [t.task_id for t in tasks] == ["smoke_file_01", "smoke_file_02", "smoke_priv_01", "smoke_acc_01",
                                          "smoke_fin_01", "smoke_repo_01", "smoke_ood_01"]
    assert {t.domain for t in tasks} == {"FILE", "PRIV", "ACC", "FIN", "REPO", "CUST"}
    for t in tasks:
        assert t.expected_tools and set(t.expected_tools) <= set(SPECS)
        apply_overrides(build_seed_state(t.state_seed), t.overrides)  # overrides apply cleanly
