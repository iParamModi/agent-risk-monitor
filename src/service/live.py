"""Live mode of the workspace: one agent run per session, its events streamed while it runs. BUILT, KEPT OFF.

Nothing here is reachable in the deployed site: `src.service.app.create_app()` is built without a backend, so
`/health` says live_available false and every live route answers 403 (CLAUDE.md, Cost safety). A backend is only
ever passed in by tests:

    app = create_app(live=local_fake_backend())      # RuleFakeMonitor + scripted agent, CPU, no API

A session is one run of the agent loop (lma_agent.agent.loop.run_agent) in a thread, on its OWN fresh simulator
state (seed state + the preset task's overrides), with every write going through the monitor gate. Its events are
the same Event objects a recorded run writes to its log (src/live/events.py), kept in memory:

    LiveSessions.start(task, setting)   -> LiveSession      a fresh state, the run starts
    LiveSession.stream(after)           -> events as they arrive, until final_response has been sent
    LiveSession.answer(yes)             -> answers the pending ASK_CONFIRMATION (the page's Approve / Deny)
    LiveSessions.reset(session_id)      -> drops the session; a pending confirmation is denied

A confirmation nobody answers within confirm_timeout_s is DENIED (the action does not run).

Limits (the hosted monitor has one container, so the site must not queue work on it):
  one live run at a time    a second start while a run is active raises LiveBusy ("monitor busy, try in a minute")
  LIVE_MAX_STEPS            at most 15 agent steps per task
  SESSION_TTL_S             a session is dropped 30 minutes after it started; a pending confirmation is denied
  RateLimit                 per-address request limits on the live routes (src/service/app.py uses two of them)

`LiveBackend.paid` says whether the backend reaches a real account (Groq, Modal). The only backend in this repo is
the local fake (paid = False). A paid backend is Step 2 under the cost rules: src.service.app asks the cost guard
with Tier C for it, which always refuses.
"""
import threading
import time
import uuid
from collections import deque
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone

from lma_agent.agent.gate import monitor_gate
from lma_agent.agent.llm import FakeLLM, assistant_msg
from lma_agent.agent.loop import run_agent
from lma_agent.sim.models import Task, ToolCall
from lma_agent.sim.seed_state import apply_overrides, build_seed_state
from src.live.company import company_snapshot
from src.live.events import Event, make_event, new_run_id

SETTINGS = ("selective", "always")
LIVE_MAX_STEPS = 15              # agent steps per live task
SESSION_TTL_S = 30 * 60          # a live session expires after 30 minutes
BUSY = "monitor busy, try in a minute"
LIVE_REQUESTS_PER_MINUTE = 120   # per address, all live routes together
BAD_PASSWORDS_PER_10_MIN = 10    # per address; after that the address is refused until the window has passed
FREE_TEXT_ID = "live_free_text"
MAX_PROMPT_CHARS = 600
NO_SCRIPT = ("The local fake agent only knows the preset tasks, so it took no action on this free-text task. "
             "A real agent LLM is not connected (live mode against real accounts is not built).")


@dataclass
class LiveBackend:
    """What a live run uses. agent_for(task) -> (client for lma_agent's call_llm, agent name for the run log)."""
    name: str
    model: object                                  # the monitor model: generate(messages)
    embedder: object
    agent_for: Callable[[Task], tuple[object, str]]
    paid: bool                                     # True = reaches a real account: Step 2, refused by the cost guard
    version: str = "v2"
    meta: dict = field(default_factory=dict)       # goes into every run's instruction meta (e.g. fake_monitor)


def local_fake_backend() -> LiveBackend:
    """CPU only, no API, no real account: the rule-based fake monitor and the scripted agent (tests, localhost)."""
    from src.live.fake_monitor import RuleFakeMonitor
    from src.live.monitor_gate import KeywordOnlyEmbedder
    from src.live.scripted_agent import SCRIPTS, scripted_agent

    def agent_for(task: Task):
        if task.task_id in SCRIPTS:
            return scripted_agent(task.task_id), "scripted"
        return FakeLLM([assistant_msg(NO_SCRIPT, [])]), "scripted"

    return LiveBackend(name="local fake (CPU)", model=RuleFakeMonitor(), embedder=KeywordOnlyEmbedder(),
                       agent_for=agent_for, paid=False,
                       meta={"fake_monitor": True, "recorded_on": "live, local CPU", "embedder": "keyword"})


def free_text_task(prompt: str) -> Task:
    """A task typed into the live task box: the plain seed company, nothing expected."""
    text = " ".join(str(prompt).split())
    if not text:
        raise ValueError("the task is empty")
    if len(text) > MAX_PROMPT_CHARS:
        raise ValueError(f"the task is longer than {MAX_PROMPT_CHARS} characters")
    return Task(task_id=FREE_TEXT_ID, domain="LIVE", prompt=text, title="Free-text task")


class LiveBusy(RuntimeError):
    """A live run is already active (the monitor serves one run at a time)."""


class RateLimit:
    """At most `limit` hits per `window_s` seconds for one key (an address), counted in a sliding window."""

    def __init__(self, limit: int, window_s: float, clock: Callable[[], float] = time.monotonic):
        self.limit, self.window_s, self.clock = int(limit), float(window_s), clock
        self._hits: dict[str, deque] = {}
        self._lock = threading.Lock()

    def _recent(self, key: str) -> deque:
        now = self.clock()
        for k in [k for k, q in self._hits.items() if not q or now - q[-1] > self.window_s]:
            del self._hits[k]                       # forget addresses that went quiet
        q = self._hits.setdefault(key, deque())
        while q and now - q[0] > self.window_s:
            q.popleft()
        return q

    def count(self, key: str) -> int:
        with self._lock:
            return len(self._recent(key))

    def hit(self, key: str) -> bool:
        """Record one hit; False when the key is over its limit (the hit is not recorded then)."""
        with self._lock:
            q = self._recent(key)
            if len(q) >= self.limit:
                return False
            q.append(self.clock())
            return True


class WebUser:
    """The person at the page, in place of lma_agent's ScriptedUser: confirm() waits for Approve / Deny."""

    def __init__(self, timeout_s: float):
        self.timeout_s = timeout_s
        self.asked: list[ToolCall] = []
        self.waiting = False
        self._yes = False
        self._answered = threading.Event()
        self._lock = threading.Lock()

    def confirm(self, call: ToolCall) -> bool:
        with self._lock:
            self.asked.append(call)
            self._yes = False
            self._answered.clear()
            self.waiting = True
        self._answered.wait(self.timeout_s)           # no answer in time = denied
        with self._lock:
            self.waiting = False
            return self._yes

    def answer(self, yes: bool) -> bool:
        """False when no confirmation is pending (nothing to answer)."""
        with self._lock:
            if not self.waiting or self._answered.is_set():
                return False
            self._yes = bool(yes)
            self._answered.set()
            return True


class LiveSession:
    def __init__(self, backend: LiveBackend, task: Task, setting: str, confirm_timeout_s: float,
                 max_steps: int = LIVE_MAX_STEPS, started: float = 0.0):
        self.id = uuid.uuid4().hex
        self.task, self.setting, self.backend = task, setting, backend
        self.max_steps, self.started = max_steps, started
        self.run_id = new_run_id(task.task_id, setting, "live")
        self.user = WebUser(confirm_timeout_s)
        self.events: list[dict] = []
        self.done = False
        self._cond = threading.Condition()
        self._thread = threading.Thread(target=self._run, name=f"live-{self.id[:8]}", daemon=True)

    def start(self) -> "LiveSession":
        self._thread.start()
        return self

    def _emit(self, event: Event) -> None:
        with self._cond:
            self.events.append(event.model_dump(mode="json"))
            self._cond.notify_all()

    def _run(self) -> None:
        backend, task = self.backend, self.task
        try:
            state = apply_overrides(build_seed_state(task.state_seed), task.overrides)      # fresh, this session only
            gate = monitor_gate(backend.model, setting=self.setting, version=backend.version,
                                embedder=backend.embedder, task=task, run_id=self.run_id)
            client, agent = backend.agent_for(task)
            meta = {"monitor_model": getattr(backend.model, "name", backend.name), "agent": agent,
                    "setting": self.setting, **gate.settings, "confirm": "live", "expected": task.expected,
                    "recorded_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "live": True,
                    "backend": backend.name, **backend.meta}
            run_agent(task, state, client, gate=gate, user=self.user, on_event=self._emit, run_id=self.run_id,
                      meta=meta, max_steps=self.max_steps)
        except Exception as err:        # a broken run must still end its stream; the page shows the error text
            if not any(e["type"] == "final_response" for e in self.events):
                self._emit(make_event(self.run_id, 0, "final_response",
                                      {"status": "error", "text": f"live run failed: {type(err).__name__}: {err}"}))
        finally:
            with self._cond:
                self.done = True
                self._cond.notify_all()

    def wait_for(self, type: str, timeout_s: float = 5.0) -> bool:
        """Block until an event of this type exists (tests, and the page's first paint)."""
        with self._cond:
            return self._cond.wait_for(lambda: any(e["type"] == type for e in self.events) or self.done, timeout_s) \
                and any(e["type"] == type for e in self.events)

    def stream(self, after: int = 0, heartbeat_s: float = 15.0) -> Iterator[dict | None]:
        """Events with index >= after, in order, as they arrive; None is a heartbeat. Ends when the run is over
        and everything has been sent."""
        sent = max(0, int(after))
        while True:
            with self._cond:
                self._cond.wait_for(lambda: len(self.events) > sent or self.done, heartbeat_s)
                batch, over = self.events[sent:], self.done
            if not batch and not over:
                yield None
                continue
            for event in batch:
                yield event
            sent += len(batch)
            if over and sent >= len(self.events):
                return

    def answer(self, yes: bool) -> bool:
        return self.user.answer(yes)

    def cancel(self) -> None:
        self.user.answer(False)         # a pending confirmation is denied, so the run can end


class LiveSessions:
    """The sessions of one app. One run at a time; a finished session is kept (for its stream and state) until it
    is reset, expires, or max_kept newer ones exist."""

    def __init__(self, backend: LiveBackend, max_running: int = 1, max_kept: int = 8, confirm_timeout_s: float = 300,
                 ttl_s: float = SESSION_TTL_S, max_steps: int = LIVE_MAX_STEPS,
                 clock: Callable[[], float] = time.monotonic):
        self.backend, self.max_running, self.max_kept = backend, max_running, max_kept
        self.confirm_timeout_s, self.ttl_s, self.max_steps, self.clock = confirm_timeout_s, ttl_s, max_steps, clock
        self._sessions: dict[str, LiveSession] = {}
        self._active: list[LiveSession] = []        # started and not finished, even after a reset or an expiry
        self._lock = threading.Lock()

    def _sweep(self) -> None:
        """Drop expired sessions (their pending confirmation is denied). Called with the lock held."""
        now = self.clock()
        for key in [k for k, s in self._sessions.items() if now - s.started > self.ttl_s]:
            self._sessions.pop(key).cancel()
        self._active = [s for s in self._active if not s.done]

    @property
    def busy(self) -> bool:
        with self._lock:
            self._sweep()
            return len(self._active) >= self.max_running

    def start(self, task: Task, setting: str) -> LiveSession:
        if setting not in SETTINGS:
            raise ValueError(f"setting must be one of {SETTINGS}")
        with self._lock:
            self._sweep()
            if len(self._active) >= self.max_running:
                raise LiveBusy(BUSY)
            for old in list(self._sessions)[:max(0, len(self._sessions) - self.max_kept + 1)]:
                del self._sessions[old]              # the oldest finished ones (nothing is running here)
            session = LiveSession(self.backend, task, setting, self.confirm_timeout_s, self.max_steps, self.clock())
            self._sessions[session.id] = session
            self._active.append(session)
        return session.start()

    def get(self, session_id: str) -> LiveSession | None:
        with self._lock:
            self._sweep()
            return self._sessions.get(str(session_id))

    def reset(self, session_id: str | None) -> bool:
        with self._lock:
            self._sweep()
            session = self._sessions.pop(str(session_id), None) if session_id else None
        if session is not None:
            session.cancel()
        return session is not None

    def fresh_company(self) -> dict:
        """One company_snapshot event of the untouched seed company (what "Reset company" shows)."""
        task = Task(task_id="live_reset", domain="LIVE", prompt="")
        snapshot = company_snapshot(task, build_seed_state(task.state_seed))
        return make_event(new_run_id(task.task_id, "none", "live"), 0, "company_snapshot", snapshot).model_dump(mode="json")
