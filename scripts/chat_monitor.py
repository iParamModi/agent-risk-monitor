"""Talk to the monitor like the real system: replay one of our records, or write your own request, and watch every
pass (the model's raw answer, the checks it asks for, the gateway's answers) until its decision.

Needs a GPU for Qwen3-8B (Kaggle notebook, T4 x2): attach the code dataset and the adapter dataset, then in a cell
    import sys; sys.path.insert(0, "/tmp/repo")          # the unpacked code (see kaggle/README.md)
    from scripts.chat_monitor import Chat
    chat = Chat(adapter="/kaggle/input/agent-risk-adapter-phase-b")   # adapter=None: base model
    chat.record("IND-FIN-T1-001-B")                                    # replay a record (selective, gold policies)
    chat.record("IND-FIN-T1-001-B", setting="never", policies="retrieval")
    chat.ask("Send 3,50,000 from acct_12 to acct_77 for the supplier invoice.",
             {"name": "transfer_money", "args": {"from_account": "acct_12", "to_account": "acct_77", "amount_inr": 350000}},
             world="IND-FIN-T1-001-B")                                 # your request, in that record's company state
Or a terminal: python scripts/chat_monitor.py [--adapter <folder>]   (commands: record <id> [setting] [policies],
ask, list [prefix], quit).

A request you write gets the world's hidden state, so the gateway answers checks about it; it has no gold, so the
decision is printed without a right/wrong mark. Records come from data/records/ (train + val; test and OOD are locked
and never loaded here).
"""
import argparse
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.common.io import read_jsonl  # noqa: E402
from src.monitor.case_inputs import CaseInputs  # noqa: E402
from src.monitor.loop import run_monitor  # noqa: E402
from src.monitor.run import Recording, RecordingGateway, trace  # noqa: E402

MODEL = "Qwen/Qwen3-8B"
REVISION = "b968826d9c46dd6066d109eabc6255188de91218"
SPLITS = ("train", "val")          # never test or OOD: they are locked (R11.3)


class Chat:
    def __init__(self, adapter: str | None = None, model=None, embedder=None):
        """model: anything with generate(messages) (tests); default the transformers backend on the GPUs."""
        if model is None:
            from src.monitor.models import TransformersModel
            model = TransformersModel(MODEL, REVISION, adapter)
        self.model = Recording(model)
        self.records = {r["record_id"]: r for s in SPLITS for r in read_jsonl(ROOT / "data" / "records" / f"{s}.jsonl")}
        self.inputs = {mode: CaseInputs(embedder=embedder, policy_mode=mode) for mode in ("gold", "retrieval")}

    def list(self, prefix: str = "") -> list[str]:
        ids = sorted(i for i in self.records if i.startswith(prefix))
        print(" ".join(ids[:80]) + (f" ... ({len(ids)} in all)" if len(ids) > 80 else ""))
        return ids

    def record(self, record_id: str, setting: str = "selective", policies: str = "gold") -> dict:
        """Replay one record; prints every pass and returns its trace."""
        if record_id not in self.records:
            raise KeyError(f"{record_id} is not a train or val record (test and OOD are locked)")
        return self._run(self.records[record_id], setting, policies, show_gold=True)

    def ask(self, user: str, action: dict, world: str, setting: str = "selective", policies: str = "retrieval",
            agent: str = "Understood, doing that now.") -> dict:
        """Your own request: one user turn and the agent about to run `action`, in the company state of record
        `world`. No gold: retrieval chooses the policies by default."""
        base = self.records[world]
        rec = copy.deepcopy(base)
        rec["record_id"] = f"ASK-{world}"
        rec["visible"] = {"trajectory": [{"role": "user", "text": user, "tool_call": None, "action_text": None},
                                         {"role": "agent", "text": agent, "tool_call": None, "action_text": None}],
                          "proposed_action": action}
        return self._run(rec, setting, policies, show_gold=False)

    def _run(self, rec: dict, setting: str, policies: str, show_gold: bool) -> dict:
        from scripts.show_traces import show
        inputs = self.inputs[policies]
        kwargs = inputs.for_record(rec, setting)
        kwargs["gateway"] = RecordingGateway(kwargs["gateway"])
        self.model.texts, self.model.passes = [], []
        row = run_monitor(rec, setting, self.model, **kwargs)
        t = trace(rec, setting, kwargs, self.model.passes, kwargs["gateway"].calls, row, policies)
        if not show_gold:
            t["gold"] = {k: None for k in t["gold"]}
            t["correct"] = True
        show(t, with_prompt=False)
        if not show_gold:
            print("  (your own request: no gold, so no right/wrong mark)")
        return t


def repl(chat: Chat) -> None:
    print("commands: record <id> [setting] [gold|retrieval] | ask | list [prefix] | quit")
    while True:
        try:
            line = input("monitor> ").strip()
        except EOFError:
            return
        if not line:
            continue
        cmd, *rest = line.split()
        try:
            if cmd in ("quit", "exit", "q"):
                return
            if cmd == "list":
                chat.list(rest[0] if rest else "")
            elif cmd == "record":
                chat.record(*rest)
            elif cmd == "ask":
                world = input("  world record id (its company state is used): ").strip()
                user = input("  user says: ").strip()
                action = json.loads(input('  proposed action JSON, e.g. {"name": "delete_file", "args": {"file": "a.pdf"}}: '))
                setting = input("  setting [selective]: ").strip() or "selective"
                chat.ask(user, action, world, setting=setting)
            else:
                print("unknown command")
        except Exception as e:      # keep the session alive on a typo
            print(f"error: {e}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--adapter", help="LoRA adapter folder; leave out for the base model")
    args = ap.parse_args(argv)
    repl(Chat(adapter=args.adapter))
    return 0


if __name__ == "__main__":
    sys.exit(main())
