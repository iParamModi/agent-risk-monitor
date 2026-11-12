"""RuleFakeMonitor: a CPU stand-in for the fine-tuned monitor, for tests and for building the replay UI before the
real Kaggle recordings exist. It is NOT the trained model and its logs say so (model name "fake-rules").

It reads only the prompt run_monitor builds (policies by number, conversation, proposed action, check results)
and answers in the monitor's JSON format with a few fixed rules for the demo actions:
  delete_file:        sharing known from the conversation or a check_file_sharing result? external -> BLOCK, else
                      ALLOW; unknown -> NEED_INFORMATION check_file_sharing
  delete_repository:  check_repository_status known? production -> ASK_CONFIRMATION, else ALLOW;
                      unknown -> NEED_INFORMATION check_repository_status
  anything else:      ALLOW
"""
import json
import re

from src.monitor.models import Generation

_POLICY = re.compile(r"^- \[(\d+)\] (.*)$", re.M)
_RESULT = re.compile(r"^- (\w+)\((\{.*?\})\) -> (\{.*\})$", re.M)


def _section(prompt: str, title: str) -> str:
    m = re.search(rf"^## {re.escape(title)}\n(.*?)(?=^## |\Z)", prompt, re.M | re.S)
    return m.group(1) if m else ""


def _action(prompt: str) -> tuple[str, dict]:
    m = re.match(r"\s*(\w+)\((\{.*\})\)", _section(prompt, "Proposed action"), re.S)
    return (m.group(1), json.loads(m.group(2))) if m else ("", {})


def _results(prompt: str) -> list[tuple[str, dict, dict]]:
    return [(t, json.loads(a), json.loads(r)) for t, a, r in _RESULT.findall(_section(prompt, "Check results (read-only, current state)"))]


def _cite(prompt: str, *words: str) -> list[str]:
    for ref, text in _POLICY.findall(_section(prompt, "Policies (the most relevant company rules)")):
        if all(w.lower() in text.lower() for w in words):
            return [ref]
    return []


def _decision(decision, label, rtype, facts, refs) -> str:
    return json.dumps({"type": "DECISION", "decision": decision, "risk_label": label, "risk_type": rtype,
                       "evidence": {"facts": facts, "policy_ids": refs}})


def _need(reason, fact, tool, args) -> str:
    return json.dumps({"type": "NEED_INFORMATION", "reason": reason, "missing_fact": fact,
                       "checks": [{"tool": tool, "args": args}]})


class RuleFakeMonitor:
    name = "fake-rules"

    def __init__(self):
        self.prompts: list[list[dict]] = []

    def generate(self, messages: list[dict]) -> Generation:
        self.prompts.append(messages)
        prompt = messages[-1]["content"]
        text = self.answer(prompt)
        return Generation(text, len(prompt.split()), len(text.split()))

    def answer(self, prompt: str) -> str:
        name, args = _action(prompt)
        may_check = "NEED_INFORMATION" in _section(prompt, "Output")
        results = _results(prompt)
        if name == "delete_file":
            path = args.get("file", "")
            sharing = None
            for tool, _, res in results:
                if tool == "check_file_sharing" and "sharing" in res:
                    sharing = res["sharing"]
            if sharing is None:
                m = re.search(rf'"path": "{re.escape(path)}"[^}}]*?"sharing": "([^"]+)"', _section(prompt, "Conversation"))
                sharing = m.group(1) if m else None
            if sharing is None:
                if may_check:
                    return _need("Sharing of the file is not known.", f"sharing of {path}", "check_file_sharing",
                                 {"path": path})
                return _decision("ALLOW", "SAFE", "NONE", [], [])
            if sharing.startswith("external"):
                return _decision("BLOCK", "UNSAFE", "DATA_LOSS", [f"{path} sharing = {sharing}"],
                                 _cite(prompt, "external", "deleted"))
            return _decision("ALLOW", "SAFE", "NONE", [f"{path} sharing = {sharing}"], [])
        if name == "delete_repository":
            repo = args.get("repo", "")
            status = next((res for tool, _, res in results if tool == "check_repository_status" and "production" in res), None)
            if status is None:
                if may_check:
                    return _need("Production status is not known.", f"production of {repo}", "check_repository_status",
                                 {"repo": repo})
                return _decision("ALLOW", "SAFE", "NONE", [], [])
            if status["production"]:
                return _decision("ASK_CONFIRMATION", "UNSAFE", "DATA_LOSS", [f"{repo} production = true"],
                                 _cite(prompt, "production", "approval"))
            return _decision("ALLOW", "SAFE", "NONE", [f"{repo} production = false"], [])
        return _decision("ALLOW", "SAFE", "NONE", [], [])
