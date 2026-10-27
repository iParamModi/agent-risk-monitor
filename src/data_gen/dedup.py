"""Near-duplicate check across splits (DATASET.md section 3.8 item 8, PLAN Step 11.4).

Two records of different seeds are near duplicates when the 5-gram Jaccard similarity of their user and agent
text is above 0.6. src/data_gen/split.py keeps such seeds in the same split, so no near duplicate can cross
splits; the pairs are listed in the split report.
"""
import re
from itertools import combinations

from src.data_gen.auto_checks import prose

NGRAM = 5
THRESHOLD = 0.6


def shingles(text: str, n: int = NGRAM) -> frozenset:
    words = re.findall(r"[a-z0-9_]+", text.lower())
    return frozenset(tuple(words[i:i + n]) for i in range(len(words) - n + 1))


def jaccard(a: frozenset, b: frozenset) -> float:
    return len(a & b) / len(a | b) if a or b else 0.0


def similar_pairs(records: list[dict], threshold: float = THRESHOLD) -> list[dict]:
    """[{"a", "b", "similarity"}] for records of different seeds above the threshold, most similar first."""
    sets = [(r["record_id"], r["seed_id"], shingles(prose(r["visible"]["trajectory"]))) for r in records]
    pairs = []
    for (ra, sa, a), (rb, sb, b) in combinations(sets, 2):
        if sa != sb:
            sim = jaccard(a, b)
            if sim > threshold:
                pairs.append({"a": ra, "b": rb, "similarity": round(sim, 3)})
    return sorted(pairs, key=lambda p: (-p["similarity"], p["a"], p["b"]))
