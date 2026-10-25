"""Embeddings + BM25, top-3 (PLAN Step 6).

score = w * meaning + (1 - w) * keywords, where each part is min-max scaled to 0..1 within the query:
  keywords = BM25 over the policy text
  meaning  = cosine similarity of bge-base-en-v1.5 embeddings
w = 0 is BM25 only, w = 1 embeddings only. w is tuned on validation only (never test or OOD).
Only the visible policy text is indexed (R8.1); hidden logic (actions, facts, decisions) is never read.

Query (PLAN 6.2): the proposed action's name and arguments + the last user request.
"""
import re

EMBED_MODEL = "BAAI/bge-base-en-v1.5"
EMBED_REVISION = "a5beb1e3e68b9ab74eb54cfd186867f64f240e1a"
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "     # bge v1.5, short query -> passage
DEFAULT_W = 0.5     # until tuned on validation
TOP_K = 3

STOPWORDS = frozenset("""a an the and or of to in on at for by with from as is are be been was were it its this that
these those any all may must not no only if than then can do does into their they them his her our your""".split())


def tokenize(text: str) -> list[str]:
    """Lowercase words; snake_case and IDs are split (transfer_money -> transfer, money); plural 's' dropped."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    out = []
    for w in words:
        if w in STOPWORDS:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


def action_text(action: dict) -> str:
    """transfer_money {amount_inr: 350000} -> 'transfer money. amount inr: 350000'."""
    args = "; ".join(f"{k.replace('_', ' ')}: {v}" for k, v in (action.get("args") or {}).items())
    name = action["name"].replace("_", " ")
    return f"{name}. {args}" if args else name


def build_query(action: dict, user_request: str | None = None) -> str:
    return f"{action_text(action)}. {user_request.strip()}" if user_request else action_text(action)


def min_max(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    return [0.0] * len(values) if hi == lo else [(v - lo) / (hi - lo) for v in values]


def combine(keyword: list[float], meaning: list[float], w: float) -> list[float]:
    return [w * m + (1 - w) * k for k, m in zip(min_max(keyword), min_max(meaning))]


def top_indices(scores: list[float], k: int) -> list[int]:
    """Highest first; ties keep store order, so results are stable."""
    return sorted(range(len(scores)), key=lambda i: (-scores[i], i))[:k]


class BgeEmbedder:
    """bge-base-en-v1.5 on CPU via sentence-transformers; vectors are L2-normalized."""

    def __init__(self, model: str = EMBED_MODEL, revision: str = EMBED_REVISION, device: str = "cpu"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model, revision=revision, device=device)

    def encode(self, texts: list[str], is_query: bool = False) -> list[list[float]]:
        if is_query:
            texts = [QUERY_PREFIX + t for t in texts]
        return self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True).tolist()


class Retriever:
    def __init__(self, policies: list[dict], embedder=None, w: float = DEFAULT_W):
        from rank_bm25 import BM25Okapi
        self.policies = policies
        self.w = w
        self.bm25 = BM25Okapi([tokenize(p["text"]) for p in policies])
        self.embedder = embedder if embedder is not None else BgeEmbedder()
        self.vectors = self.embedder.encode([p["text"] for p in policies])

    def raw_scores(self, query: str) -> tuple[list[float], list[float]]:
        """(BM25, cosine) per policy, before scaling. Kept apart so many w values can reuse them."""
        keyword = [float(s) for s in self.bm25.get_scores(tokenize(query))]
        q = self.embedder.encode([query], is_query=True)[0]
        meaning = [sum(a * b for a, b in zip(q, v)) for v in self.vectors]
        return keyword, meaning

    def rank(self, query: str, k: int = TOP_K, w: float | None = None) -> list[int]:
        keyword, meaning = self.raw_scores(query)
        return top_indices(combine(keyword, meaning, self.w if w is None else w), k)

    def search(self, query: str, k: int = TOP_K, w: float | None = None) -> list[dict]:
        """Top k as [{"policy_id", "text"}]: the input src.monitor.loop.run_monitor expects."""
        return [{"policy_id": self.policies[i]["policy_id"], "text": self.policies[i]["text"]}
                for i in self.rank(query, k, w)]

    def for_action(self, action: dict, user_request: str | None = None, k: int = TOP_K) -> list[dict]:
        return self.search(build_query(action, user_request), k)
