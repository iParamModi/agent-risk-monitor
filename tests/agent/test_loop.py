import json

from lma_agent.agent.gate import allow_all, fake_gate
from lma_agent.agent.llm import FakeLLM, assistant_msg
from lma_agent.agent.user_sim import ScriptedUser
from lma_agent.agent.loop import run_agent
from lma_agent.sim.models import Task, ToolCall
from lma_agent.sim.seed_state import build_seed_state, state_hash

PATH = "/project/report_7.pdf"
TASK = Task(task_id="t_loop", domain="FILE", prompt="Delete /project/report_7.pdf.")


def calls(*specs):
    return assistant_msg(None, [ToolCall(id=f"c{i}", name=n, args=a) for i, (n, a) in enumerate(specs)])


def read_write_done():
    return FakeLLM([
        calls(("get_file_info", {"path": PATH})),
        calls(("delete_file", {"path": PATH})),
        assistant_msg("Deleted the report.", []),
    ])


def tool_results(result):
    return [json.loads(m["content"]) for m in result.messages if m["role"] == "tool"]


def test_read_write_done_with_allow_all():
    state = build_seed_state(0)
    fake = read_write_done()
    res = run_agent(TASK, state, fake, gate=allow_all)
    assert res.status == "done" and res.final_answer == "Deleted the report."
    assert res.n_llm_calls == 3 and res.n_tool_errors == 0
    assert [s.tool_type for s in res.steps] == ["read", "write"]
    assert res.steps[1].gate_decision == "ALLOW" and res.steps[1].executed
    assert res.final_state_hash != state_hash(state)
    assert PATH in state.files  # input state is never changed
    # the model saw the read result before deciding to delete
    assert fake.received[1][-1]["role"] == "tool"
    assert json.loads(fake.received[1][-1]["content"])["owner"] == "u_riya"


def test_block_does_not_execute():
    state = build_seed_state(0)
    res = run_agent(TASK, state, read_write_done(), gate=fake_gate("BLOCK"))
    assert res.status == "done"
    assert not res.steps[1].executed and res.steps[1].gate_decision == "BLOCK"
    assert tool_results(res)[1] == {"status": "blocked", "policy": "P_TEST", "reason": "fake gate"}
    assert res.final_state_hash == state_hash(state)


def test_ask_confirmation_user_confirms():
    state = build_seed_state(0)
    user = ScriptedUser(True)
    res = run_agent(TASK, state, read_write_done(), gate=fake_gate("ASK_CONFIRMATION"), user=user)
    assert res.steps[1].executed and tool_results(res)[1]["status"] == "deleted"
    assert user.asked[0].name == "delete_file"
    assert res.final_state_hash != state_hash(state)


def test_ask_confirmation_user_declines():
    state = build_seed_state(0)
    task = TASK.model_copy(update={"user_confirms": False})
    res = run_agent(task, state, read_write_done(), gate=fake_gate("ASK_CONFIRMATION"))
    assert not res.steps[1].executed and tool_results(res)[1] == {"status": "declined_by_user"}
    assert res.final_state_hash == state_hash(state)


def test_escalate_stops_episode():
    state = build_seed_state(0)
    fake = read_write_done()
    res = run_agent(TASK, state, fake, gate=fake_gate("ESCALATE"))
    assert res.status == "escalated" and res.final_answer is None
    assert fake.calls == 2 and res.n_llm_calls == 2
    assert tool_results(res)[-1] == {"status": "escalated_to_human"}
    assert res.final_state_hash == state_hash(state)


def test_unknown_tool_and_bad_args_are_returned_and_counted():
    fake = FakeLLM([
        calls(("run_command", {"cmd": "rm -rf /"})),
        calls(("delete_file", {"_raw": '{"path": '})),
        calls(("transfer_money", {"from_account": "ACC-OPS", "to_account": "ACC-VENDOR-1", "amount": "lots"})),
        calls(("get_file_info", {"path": PATH})),
        assistant_msg("ok", []),
    ])
    res = run_agent(TASK, build_seed_state(0), fake)
    assert res.status == "done" and res.n_tool_errors == 3
    errs = [r.get("error") for r in tool_results(res)]
    assert errs == ["unknown_tool", "bad_args", "bad_args", None]
    assert [s.tool_type for s in res.steps] == ["invalid", "invalid", "invalid", "read"]


def test_model_that_never_stops_hits_max_steps():
    fake = FakeLLM([calls(("list_files", {"folder": "/project"}))], repeat_last=True)
    res = run_agent(TASK, build_seed_state(0), fake, max_steps=4)
    assert res.status == "max_steps" and res.n_llm_calls == 4 and len(res.steps) == 4


def test_reads_never_call_the_gate():
    def exploding_gate(messages, call):
        raise AssertionError("gate called for a read")

    fake = FakeLLM([
        calls(("list_files", {"folder": "/project"}), ("get_file_info", {"path": PATH})),
        calls(("read_inbox", {})),
        assistant_msg("done", []),
    ])
    res = run_agent(TASK, build_seed_state(0), fake, gate=exploding_gate)
    assert res.status == "done" and len(res.steps) == 3


def test_several_calls_in_one_message_and_write_errors():
    fake = FakeLLM([
        calls(("delete_file", {"path": "/nope.pdf"}), ("delete_file", {"path": PATH})),
        assistant_msg("done", []),
    ])
    res = run_agent(TASK, build_seed_state(0), fake)
    assert [r.get("error") for r in tool_results(res)] == ["not_found", None]
    assert res.n_tool_errors == 1 and [s.executed for s in res.steps] == [False, True]


def test_llm_failure_gives_error_status_and_episode_is_saved(tmp_path):
    res = run_agent(TASK, build_seed_state(0), FakeLLM([]), out_dir=tmp_path)
    assert res.status == "error" and "FakeLLM ran out" in res.final_answer
    assert (tmp_path / f"{res.episode_id}.json").exists()


def test_ood_tools_only_for_cust_tasks():
    fake = FakeLLM([assistant_msg("ok", [])] * 2)
    run_agent(TASK, build_seed_state(0), fake)
    run_agent(Task(task_id="o", domain="CUST", prompt="x"), build_seed_state(0), fake)
    assert len(fake.tool_names[0]) == 18 and "archive_record" not in fake.tool_names[0]
    assert len(fake.tool_names[1]) == 21 and "archive_record" in fake.tool_names[1]
