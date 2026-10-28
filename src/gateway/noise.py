"""A6: noisy check results. Off by default; never on when building training data.

With NoiseConfig(rate, seed), each boolean and each category field (configs/check_tools.yaml `enums`) of a
successful result is flipped with probability `rate`: a boolean is negated, a category value is replaced by a
different allowed one. Ints, names, paths and ids are left alone; errors are never changed. The random draws
are seeded per (seed, case_id, call_index), so the same run gives the same flips.
"""
import random
from dataclasses import dataclass

from src.gateway.registry import Tool


@dataclass(frozen=True)
class NoiseConfig:
    rate: float
    seed: int

    def __post_init__(self):
        if not 0.0 <= self.rate <= 1.0:
            raise ValueError(f"noise rate must be in [0, 1], got {self.rate}")


def apply_noise(noise: NoiseConfig, tool: Tool, facts: dict, case_id: str, call_index: int) -> tuple[dict, bool]:
    """(the facts the monitor sees, whether any value was flipped)."""
    rng = random.Random(f"{noise.seed}|{case_id}|{call_index}")
    out, flipped = dict(facts), False
    for field, type_name in tool.returns.items():
        value = out[field]
        if type_name == "boolean":
            others = [not value]
        elif field in tool.enums and value is not None:
            others = [v for v in tool.enums[field] if v != value]
        else:
            continue
        if rng.random() < noise.rate and others:     # one draw per flippable field, so flips stay stable
            out[field], flipped = rng.choice(others), True
    return out, flipped
