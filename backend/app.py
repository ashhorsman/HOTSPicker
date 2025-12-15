from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from hero_loader import HeroProfile, hero_to_dict, load_heroes_from_txt
from presets import RANK_PRESETS
from scoring import (
    build_team_state,
    infer_missing_essentials,
    pick_score,
    ban_score,
    build_warnings,
    composition_score,
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
HERO_TXT = os.path.join(DATA_DIR, "heroes.txt")

MAPS_JSON = Path(DATA_DIR) / "maps.json"

app = Flask(__name__, static_folder="../frontend", static_url_path="/")
CORS(app)

# Load heroes once on startup, keep in memory
HEROES: List[HeroProfile] = load_heroes_from_txt(HERO_TXT)
HERO_BY_ID: Dict[str, HeroProfile] = {h.hero_id: h for h in HEROES}

# Load maps once on startup (optional)
if MAPS_JSON.exists():
    MAPS: Dict[str, Dict[str, float]] = json.loads(MAPS_JSON.read_text(encoding="utf-8"))
else:
    MAPS = {}


@app.get("/api/heroes")
def api_heroes():
    return jsonify([hero_to_dict(h) for h in HEROES])


@app.get("/api/maps")
def api_maps():
    return jsonify({"maps": sorted(MAPS.keys())})


def normalize_score(score: float, s_min: float, s_max: float) -> float:
    if s_max <= s_min:
        return 50.0
    return 100.0 * (score - s_min) / (s_max - s_min)


def norm_to_grade(norm: float) -> str:
    # norm is 0..100 relative to this request's candidate pool
    if norm >= 90:
        return "S"
    if norm >= 75:
        return "A"
    if norm >= 60:
        return "B"
    if norm >= 45:
        return "C"
    if norm >= 30:
        return "D"
    return "E"


@app.post("/api/recommendations")
def api_recommendations():
    payload = request.get_json(force=True) or {}
    draft = payload.get("draft", {}) or {}
    settings = payload.get("settings", {}) or {}

    rank = settings.get("rankPreset", "Silver")
    preset = RANK_PRESETS.get(rank, RANK_PRESETS["Silver"])

    simple = bool(settings.get("simpleComps", True))
    phase = draft.get("phase", "pick")  # pick or ban
    side_to_act = draft.get("sideToAct", "ally")  # ally or enemy
    early_pick_window = bool(draft.get("earlyPickWindow", True))

    map_name = (settings.get("mapName") or "").strip()
    map_weights: Dict[str, float] = MAPS.get(map_name, {}) if map_name else {}

    # Debug print (optional)
    print(
        "MAP:",
        map_name,
        "WEIGHTS_KEYS:",
        list(map_weights.keys())[:5],
        "COUNT:",
        len(map_weights),
    )

    our_picks = draft.get("ourPicks", []) or []
    enemy_picks = draft.get("enemyPicks", []) or []
    bans = set(draft.get("bans", []) or [])

    our = build_team_state(HERO_BY_ID, our_picks)
    enemy = build_team_state(HERO_BY_ID, enemy_picks)

    # Team scores for UI
    our_team_score = round(composition_score(our), 1)
    enemy_team_score = round(composition_score(enemy), 1)

    missing = infer_missing_essentials(our)

    # Build candidate list
    unavailable = set(our_picks) | set(enemy_picks) | bans
    candidates = [h for h in HEROES if h.hero_id not in unavailable]

    # Recommend for the side that is about to act.
    acting_team = our if side_to_act == "ally" else enemy
    opposing_team = enemy if side_to_act == "ally" else our
    acting_missing = infer_missing_essentials(acting_team)

    recs: List[Dict[str, Any]] = []

    if phase == "pick":
        base_team_score = composition_score(acting_team)

        scored = []
        for h in candidates:
            s, contribs = pick_score(
                h,
                acting_team,
                opposing_team,
                acting_missing,
                preset,
                simple,
                early_pick_window,
                map_weights,
            )
            scored.append((s, h, contribs))

        scored.sort(key=lambda x: x[0], reverse=True)

        all_scores = [x[0] for x in scored] if scored else [0.0]
        s_min, s_max = min(all_scores), max(all_scores)

        top = []
        seen_roles = set()

        for s, h, contribs in scored:
            role_key = ",".join(sorted(h.role))

            top.append((s, h, contribs))
            seen_roles.add(role_key)

            # Stop when we have 5 OR at least 3 different roles represented
            if len(top) >= 5 and len(seen_roles) >= 3:
                break

        for s, h, contribs in top:
            tags = []
            if early_pick_window and simple:
                tags.append("safe early")
            if h.contested == "H":
                tags.append("must lock now")
            if side_to_act == "enemy":
                tags.append("enemy likely")

            # Team score delta if we add this hero
            new_team = build_team_state(HERO_BY_ID, acting_team.picks + [h.hero_id])
            team_after = composition_score(new_team)
            team_delta = team_after - base_team_score

            reason = _reason_from_contribs(contribs)

            norm = normalize_score(s, s_min, s_max)
            grade = norm_to_grade(norm)

            recs.append(
                {
                    "hero_id": h.hero_id,
                    "hero_name": h.hero_name,
                    "score": round(s, 1),              # keep raw for debugging
                    "scoreNorm": round(norm, 1),       # 0..100 relative scale
                    "grade": grade,                    # S..E
                    "teamScoreAfter": round(team_after, 1),
                    "teamScoreDelta": round(team_delta, 1),
                    "tags": tags,
                    "reason": reason,
                }
            )

    if phase == "ban":
        enemy_has_stealth = opposing_team.provides.get("Stealth", 0) > 0
    we_lack_reveal = (not acting_team.has_reveal) and enemy_has_stealth

    scored = []
    for h in candidates:
        s, contribs = ban_score(
            h,
            acting_team,
            preset,
            we_lack_reveal,
            map_weights,
        )
        scored.append((s, h, contribs))

    scored.sort(key=lambda x: x[0], reverse=True)

    all_scores = [x[0] for x in scored] if scored else [0.0]
    s_min, s_max = min(all_scores), max(all_scores)

    for s, h, contribs in scored[:5]:
        norm = normalize_score(s, s_min, s_max)
        grade = norm_to_grade(norm)

        recs.append(
            {
                "hero_id": h.hero_id,
                "hero_name": h.hero_name,
                "score": round(s, 1),
                "scoreNorm": round(norm, 1),
                "grade": grade,
                "reason": _reason_from_contribs(contribs),
            }
        )


    


    warnings = build_warnings(our, enemy)
    plan = build_plan_lines(our)

    return jsonify(
        {
            "phase": phase,
            "sideToAct": side_to_act,
            "recommendations": recs,
            "warnings": warnings,
            "endPlan": plan,
            "missing": sorted(list(missing)),
            "ourTeamScore": our_team_score,
            "enemyTeamScore": enemy_team_score,
            "mapName": map_name,
        }
    )


def _reason_from_contribs(contribs):
    # pick top 2 positives and top 1 negative
    pos = sorted([c for c in contribs if c[1] > 0], key=lambda x: x[1], reverse=True)[:2]
    neg = sorted([c for c in contribs if c[1] < 0], key=lambda x: x[1])[:1]

    parts = []

    if pos:
        seen = set()
        pos_labels = []
        for label, _val in pos:
            if label in seen:
                continue
            seen.add(label)
            pos_labels.append(label)
        parts.append(" + ".join(pos_labels))

    if neg:
        parts.append(f"Warning: {neg[0][0]}")

    return " | ".join(parts) if parts else "No strong signal"


def build_plan_lines(our):
    who_starts = "Start fights with your engage"
    if our.provides.get("Engage", 0) == 0:
        who_starts = "Look for picks, avoid hard 5v5 starts"

    kill_pattern = "Burst the first target caught by CC"
    if our.provides.get("SustainDmg", 0) > our.provides.get("Burst", 0):
        kill_pattern = "Wear down frontline then collapse"
    if our.provides.get("Pick", 0) > 0:
        kill_pattern = "Play for picks, then convert to objective"

    macro_rule = "Keep lanes soaked and take camps on cooldown"
    if our.provides.get("Macro", 0) == 0:
        macro_rule = "Group earlier and avoid losing soak"

    return [who_starts, kill_pattern, macro_rule]


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/<path:path>")
def static_proxy(path: str):
    return send_from_directory(app.static_folder, path)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
