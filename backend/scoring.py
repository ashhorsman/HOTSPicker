from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set, Tuple

from hero_loader import HeroProfile
from presets import WeightPreset


CORE_PROVIDES = {"Frontline", "Engage", "Waveclear", "Peel", "Save", "Disengage"}


@dataclass
class TeamState:
    picks: List[str] = field(default_factory=list)
    roles: Dict[str, int] = field(default_factory=dict)
    provides: Dict[str, int] = field(default_factory=dict)
    weaknesses: Dict[str, int] = field(default_factory=dict)
    damage_counts: Dict[str, int] = field(default_factory=dict)
    has_reveal: bool = False


def _inc(d: Dict[str, int], k: str, n: int = 1) -> None:
    d[k] = d.get(k, 0) + n


def build_team_state(hero_by_id: Dict[str, HeroProfile], picks: List[str]) -> TeamState:
    ts = TeamState(picks=list(picks))
    for hid in picks:
        h = hero_by_id.get(hid)
        if not h:
            continue

        for r in h.role:
            _inc(ts.roles, r)
        for p in h.provides:
            _inc(ts.provides, p)
        for w in h.weaknesses:
            _inc(ts.weaknesses, w)

        if h.dmg:
            _inc(ts.damage_counts, h.dmg)

        if h.reveal == "Y":
            ts.has_reveal = True

        if h.stealth == "Y":
            _inc(ts.provides, "Stealth")

    return ts


def infer_missing_essentials(team: TeamState) -> Set[str]:
    missing = set()
    pick_count = len(team.picks)

    # HARD requirements only after early draft
    if pick_count >= 3:
        if team.roles.get("Tank", 0) == 0:
            missing.add("Tank")
        if team.roles.get("Healer", 0) == 0:
            missing.add("Healer")

    # Offlane later still
    if pick_count >= 4:
        if team.roles.get("Bruiser", 0) == 0 and team.roles.get("Tank", 0) < 2:
            missing.add("Offlane")

    # Always evaluate functional needs
    if team.provides.get("Waveclear", 0) == 0:
        missing.add("Waveclear")
    if team.provides.get("Engage", 0) == 0:
        missing.add("Engage")
    if team.provides.get("Peel", 0) == 0:
        missing.add("Peel")

    return missing



def composition_score(team: TeamState) -> float:
    # Simple 0-100 team completeness score for UI
    missing = infer_missing_essentials(team)
    score = 100.0

    if "Tank" in missing:
        score -= 18
    if "Healer" in missing:
        score -= 18
    if "Offlane" in missing:
        score -= 10

    if "Waveclear" in missing:
        score -= 12
    if "Engage" in missing:
        score -= 10
    if "Peel" in missing:
        score -= 10

    for _, c in team.weaknesses.items():
        if c >= 3:
            score -= 8
        elif c == 2:
            score -= 4

    if score < 0:
        score = 0
    if score > 100:
        score = 100

    return score


def dependency_index(hero: HeroProfile) -> int:
    needs_count = len(hero.needs)
    needs_setup = 1 if "NeedsSetup" in hero.weaknesses else 0
    gated_core = 0

    if hero.cleanse in ("S", "Y") and hero.gate_cleanse != "B":
        gated_core += 1
    if "Engage" in hero.provides and hero.gate_engage != "B":
        gated_core += 1
    if "Global" in hero.provides and hero.gate_global != "B":
        gated_core += 1

    return needs_count + needs_setup + gated_core


def _quality_score(reliability: str) -> int:
    if reliability == "H":
        return 10
    if reliability == "M":
        return 5
    return 0


def pick_score(
    hero: HeroProfile,
    our: TeamState,
    enemy: TeamState,
    missing: Set[str],
    preset: WeightPreset,
    simple_comps: bool,
    early_pick_window: bool,
    map_weights: Dict[str, float] | None = None,
) -> Tuple[float, List[Tuple[str, float]]]:

    contribs: List[Tuple[str, float]] = []
    score = 0.0

    pick_count = len(our.picks)

    # -------------------------
    # ROLE IMPORTANCE RAMP
    # -------------------------
    # Picks 0–2: no role forcing
    # Picks 3–4: partial pressure
    # Picks 5+: full pressure
    if pick_count <= 2:
        role_mult = 0.0
    elif pick_count <= 4:
        role_mult = 0.6
    else:
        role_mult = 1.0

    # -------------------------
    # ROLE FIT (NON-DOMINANT)
    # -------------------------
    if "Tank" in missing and "Tank" in hero.role:
        add = 45 * role_mult
        score += add
        if add:
            contribs.append(("Fills Tank", add))

    if "Healer" in missing and "Healer" in hero.role:
        healer_mult = role_mult if pick_count <= 4 else 1.15
        add = 45 * healer_mult
        score += add
        if add:
            contribs.append(("Fills Healer", add))

    if "Offlane" in missing and (
        hero.role_detail == "Offlane"
        or ("Bruiser" in hero.role and hero.lane == "Offlane")
    ):
        offlane_mult = 0.0 if pick_count <= 2 else 0.6 if pick_count <= 4 else 1.0
        add = 25 * offlane_mult
        score += add
        if add:
            contribs.append(("Fills Offlane", add))

    # -------------------------
    # FUNCTIONAL CONTRIBUTIONS
    # -------------------------
    for tag in ("Waveclear", "Engage", "Peel", "Disengage", "Save", "CampClear", "Macro"):
        if tag in hero.provides:
            base = 18 if tag in ("Waveclear", "Engage", "Peel") else 12
            mult = 1.0

            if map_weights:
                mult *= float(map_weights.get(tag, 1.0))

            # Missing functions matter more after early draft
            if tag in missing:
                mult *= 1.25 if pick_count >= 3 else 0.9

            add = base * mult
            score += add
            contribs.append((f"Provides {tag}", add))

    # -------------------------
    # HERO NEEDS SYNERGY
    # -------------------------
    for need in hero.needs:
        if our.provides.get(need, 0) > 0:
            score += 8
            contribs.append((f"Synergy with team {need}", 8))

    # -------------------------
    # CORE PROVIDES (ANTI MULTI-DIP)
    # -------------------------
    for p in hero.provides:
        if p in CORE_PROVIDES and our.provides.get(p, 0) == 0:
            add = 6 if pick_count <= 2 else 10
            score += add
            contribs.append((f"Adds core {p}", add))

    # -------------------------
    # RELIABILITY (RANK AWARE)
    # -------------------------
    reliability_bonus = 0

    if "Engage" in hero.provides:
        reliability_bonus += _quality_score(hero.quality_eng.reliability)
    if "Peel" in hero.provides:
        reliability_bonus += _quality_score(hero.quality_cc.reliability)
    if "Save" in hero.provides:
        reliability_bonus += _quality_score(hero.quality_save.reliability)

    reliability_bonus *= preset.reliability_weight
    if reliability_bonus:
        score += reliability_bonus
        contribs.append(("Reliable execution", reliability_bonus))

    # -------------------------
    # WEAKNESS STACKING
    # -------------------------
    for w in hero.weaknesses:
        count = our.weaknesses.get(w, 0)
        if count >= 2:
            pen = (
                preset.weakness_stack_3_penalty
                if count >= 3
                else preset.weakness_stack_2_penalty
            )
            score -= pen
            contribs.append((f"Stacks weakness {w}", -pen))

    # -------------------------
    # GATED TOOLS PENALTY
    # -------------------------
    if pick_count >= 3:
        if "Cleanse" in missing and hero.cleanse in ("S", "Y") and hero.gate_cleanse != "B":
            pen = 8 * preset.gate_penalty_weight
            score -= pen
            contribs.append(("Cleanse gated", -pen))

        if "Engage" in missing and "Engage" in hero.provides and hero.gate_engage != "B":
            pen = 8 * preset.gate_penalty_weight
            score -= pen
            contribs.append(("Engage gated", -pen))

    # -------------------------
    # EARLY PICK DEPENDENCY CHECK
    # -------------------------
    if simple_comps and early_pick_window:
        dep = dependency_index(hero)
        if dep > preset.early_pick_dependency_cap:
            pen = (dep - preset.early_pick_dependency_cap) * 12
            score -= pen
            contribs.append(("Too dependent early", -pen))

    # -------------------------
    # ENEMY CONTEXT
    # -------------------------
    enemy_dive = enemy.provides.get("DiveEnable", 0) + enemy.provides.get("Engage", 0)
    if enemy_dive >= 2:
        if "AntiDive" in hero.provides:
            score += 10
            contribs.append(("Answers dive", 10))
        if "Peel" in hero.provides:
            score += 8
            contribs.append(("Extra peel vs dive", 8))

    # -------------------------
    # MAP FIT (LATE WEIGHT)
    # -------------------------
    if map_weights:
        map_bonus = 0.0
        for k, mult in map_weights.items():
            if mult > 1.0 and k in hero.provides:
                map_bonus += (mult - 1.0) * (15 if pick_count <= 2 else 22)

        if map_bonus:
            score += map_bonus
            contribs.append(("Map fit", map_bonus))

    return score, contribs



def ban_score(
    hero: HeroProfile,
    our: TeamState,
    preset: WeightPreset,
    we_lack_reveal: bool,
    map_weights: Dict[str, float] | None = None,
) -> Tuple[float, List[Tuple[str, float]]]:


    contribs: List[Tuple[str, float]] = []
    score = 0.0

    if hero.stealth == "Y" and we_lack_reveal:
        score += 30
        contribs.append(("Stealth threat and you lack Reveal", 30))

    if our.weaknesses.get("LowMobility", 0) >= 2 and ("DiveEnable" in hero.provides or "Engage" in hero.provides):
        score += 15
        contribs.append(("Punishes LowMobility stack", 15))

        # Map threat: if the map values something highly, ban heroes who bring it.
    map_bonus = 0.0
    if map_weights:
        for k, mult in map_weights.items():
            if mult <= 1.0:
                continue
            if k in hero.provides:
                map_bonus += (mult - 1.0) * 18.0

    if map_bonus:
        score += map_bonus
        contribs.append(("Strong on this map", map_bonus))

        # Map threat: if the map values something highly, ban heroes who bring it.
    map_bonus = 0.0
    if map_weights:
        for k, mult in map_weights.items():
            if mult <= 1.0:
                continue
            if k in hero.provides:
                map_bonus += (mult - 1.0) * 18.0

    if map_bonus:
        score += map_bonus
        contribs.append(("Strong on this map", map_bonus))

    # Meta pressure (reduced so map and matchup can matter)
    if hero.contested == "H":
        score += 6
        contribs.append(("Highly contested", 6))
    elif hero.contested == "M":
        score += 3
        contribs.append(("Contested", 3))



    return score, contribs


def build_warnings(our: TeamState, enemy: TeamState) -> List[str]:
    warnings: List[str] = []
    missing = infer_missing_essentials(our)

    if "Waveclear" in missing:
        warnings.append("No waveclear")
    if "Engage" in missing:
        warnings.append("No engage")
    if "Peel" in missing:
        warnings.append("No peel")
    pick_count = len(our.picks)

    if pick_count >= 3:
        if "Tank" in missing:
            warnings.append("No tank")
        if "Healer" in missing:
            warnings.append("No healer")

    if pick_count >= 4:
        if "Offlane" in missing:
            warnings.append("No offlane")


    if our.weaknesses.get("LowMobility", 0) >= 2 and our.provides.get("Peel", 0) == 0:
        warnings.append("Backline low mobility with no peel")

    if enemy.provides.get("Stealth", 0) > 0 and not our.has_reveal:
        warnings.append("Enemy stealth threat and no reveal")

    aa = our.damage_counts.get("AA", 0)
    spell = our.damage_counts.get("Spell", 0)
    if aa >= 3 and spell == 0:
        warnings.append("Damage skew: mostly AA")
    if spell >= 3 and aa == 0:
        warnings.append("Damage skew: mostly Spell")

    return warnings
