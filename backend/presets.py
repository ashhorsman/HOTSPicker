from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class WeightPreset:
    name: str
    reliability_weight: float
    gate_penalty_weight: float
    early_pick_dependency_cap: int  # max dependency allowed when "simple comps"
    weakness_stack_2_penalty: int
    weakness_stack_3_penalty: int


RANK_PRESETS: Dict[str, WeightPreset] = {
    "Bronze": WeightPreset(
        name="Bronze",
        reliability_weight=1.4,
        gate_penalty_weight=1.3,
        early_pick_dependency_cap=3,
        weakness_stack_2_penalty=10,
        weakness_stack_3_penalty=20,
    ),
    "Silver": WeightPreset(
        name="Silver",
        reliability_weight=1.25,
        gate_penalty_weight=1.2,
        early_pick_dependency_cap=4,
        weakness_stack_2_penalty=10,
        weakness_stack_3_penalty=18,
    ),
    "Gold": WeightPreset(
        name="Gold",
        reliability_weight=1.1,
        gate_penalty_weight=1.0,
        early_pick_dependency_cap=5,
        weakness_stack_2_penalty=9,
        weakness_stack_3_penalty=16,
    ),
    "Plat+": WeightPreset(
        name="Plat+",
        reliability_weight=1.0,
        gate_penalty_weight=0.9,
        early_pick_dependency_cap=6,
        weakness_stack_2_penalty=8,
        weakness_stack_3_penalty=14,
    ),
}
