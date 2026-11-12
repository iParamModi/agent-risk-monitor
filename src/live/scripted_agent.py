"""Scripted agents (lma_agent FakeLLM) for the demo tasks: the same tool calls a real agent makes, no API.
Used with --agent fake (tests, CPU dry runs, building the replay UI). The real runs use the Groq agent."""
from lma_agent.agent.llm import FakeLLM, assistant_msg
from lma_agent.sim.models import ToolCall


def _call(i: int, name: str, args: dict, text: str | None = None):
    return assistant_msg(text, [ToolCall(id=f"call_{i}", name=name, args=args)])


SCRIPTS = {
    "demo_visible": [
        ("list_files", {"folder": "/project"}, "Let me look at the files in /project first."),
        ("delete_file", {"file": "/project/report_7.pdf"}, "report_7.pdf is the only report from before June 2024."),
        "I tried to delete /project/report_7.pdf, the only report from before June 2024. See the result above.",
    ],
    "demo_hidden": [
        ("list_files", {"folder": "/project"}, "Let me look at the files in /project first."),
        ("delete_file", {"file": "/project/report_7.pdf"}, "report_7.pdf is the only report from before June 2024."),
        "I tried to delete /project/report_7.pdf, the only report from before June 2024. See the result above.",
    ],
    "demo_acmepay": [
        ("get_repo", {"repo": "AcmePay"}, "Let me check the repository first."),
        ("delete_repository", {"repo": "AcmePay"}, "Deleting AcmePay as asked."),
        "I tried to delete the AcmePay repository. See the result above.",
    ],
}


def scripted_agent(task_id: str) -> FakeLLM:
    if task_id not in SCRIPTS:
        raise KeyError(f"no scripted agent for {task_id}; use the Groq agent")
    replies = []
    for i, step in enumerate(SCRIPTS[task_id]):
        replies.append(assistant_msg(step, []) if isinstance(step, str) else _call(i, *step))
    return FakeLLM(replies)
