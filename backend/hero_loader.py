from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Quality:
    delivery: str
    reliability: str  # L, M, H


@dataclass
class HeroProfile:
    hero_id: str
    hero_name: str

    # Scalars
    role: List[str] = field(default_factory=list)
    role_detail: str = ""
    lane: str = ""

    dmg: str = ""
    rng: str = ""

    wc: str = ""
    camp: str = ""
    eng: str = ""
    peel: str = ""
    macro: str = ""

    global_: str = "N"
    cleanse: str = "N"
    reveal: str = "N"
    stealth: str = "N"
    antiheal: str = "N"

    contested: str = "M"

    # Arrays
    cc: List[str] = field(default_factory=list)
    styles: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    needs: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    power_curve: List[str] = field(default_factory=list)

    # Quality blocks
    quality_eng: Quality = field(default_factory=lambda: Quality("None", "L"))
    quality_cc: Quality = field(default_factory=lambda: Quality("None", "L"))
    quality_save: Quality = field(default_factory=lambda: Quality("None", "L"))
    quality_int: Quality = field(default_factory=lambda: Quality("None", "L"))

    # Gates
    gate_cleanse: str = "N"
    gate_antiheal: str = "N"
    gate_reveal: str = "N"
    gate_interrupt: str = "N"
    gate_engage: str = "N"
    gate_global: str = "N"

    raw: Dict[str, str] = field(default_factory=dict)


def hero_id_from_name(name: str) -> str:
    n = unicodedata.normalize("NFKD", name).lower()
    n = re.sub(r"[’'`]", "", n)
    n = re.sub(r"[^a-z0-9]+", "_", n).strip("_")
    return n


def _normalize_key(k: str) -> str:
    return k.strip().lower().replace(" ", "")


def _split_any(val: str) -> List[str]:
    return [p.strip() for p in re.split(r"[,\|]", val) if p.strip()]


def _parse_quality(val: str) -> Quality:
    parts = val.strip().split()
    if not parts:
        return Quality("None", "L")
    if len(parts) == 1:
        return Quality(parts[0], "L")
    delivery = " ".join(parts[:-1])
    reliability = parts[-1]

    dkey = _normalize_key(delivery).replace("-", "")
    delivery_map = {
        "pointclick": "PointClick",
        "skillshot": "Skillshot",
        "targetarea": "TargetArea",
        "conditional": "Conditional",
        "channel": "Channel",
        "none": "None",
        "heroic": "Heroic",
        "self": "Self",
    }
    return Quality(delivery_map.get(dkey, delivery), reliability)


def parse_hero_line(line: str) -> Optional[HeroProfile]:
    if ":" not in line:
        return None
    name, rest = line.split(":", 1)
    hero_name = name.strip()
    hero_id = hero_id_from_name(hero_name)

    hp = HeroProfile(hero_id=hero_id, hero_name=hero_name)

    segments = [s.strip() for s in rest.split(";") if s.strip()]
    for seg in segments:
        if " " not in seg:
            continue
        key, val = seg.split(" ", 1)
        keyn = _normalize_key(key)
        val = val.strip().strip(".")

        hp.raw[keyn] = val

        if keyn == "role":
            tmp = val.replace("/", " or ")
            roles = []
            for part in re.split(r"\bor\b|,", tmp):
                p = part.strip()
                if p:
                    roles.append(p)
            hp.role = roles
            continue

        if keyn == "roledetail":
            hp.role_detail = val
            continue

        if keyn in ("cc", "styles", "provides", "needs", "weaknesses", "powercurve", "power_curve"):
            arr = _split_any(val)
            if keyn == "powercurve":
                hp.power_curve = arr
            else:
                setattr(hp, keyn, arr)
            continue

        if keyn == "lane":
            hp.lane = val
            continue

        if keyn in ("dmg", "rng", "wc", "camp", "eng", "peel", "macro", "global", "cleanse", "reveal", "stealth", "antiheal", "contested"):
            if keyn == "global":
                hp.global_ = val
            else:
                setattr(hp, keyn, val)
            continue

        if keyn == "eng-q":
            hp.quality_eng = _parse_quality(val)
            continue
        if keyn == "cc-q":
            hp.quality_cc = _parse_quality(val)
            continue
        if keyn == "save-q":
            hp.quality_save = _parse_quality(val)
            continue
        if keyn == "int-q":
            hp.quality_int = _parse_quality(val)
            continue

        if keyn == "cleansegate":
            hp.gate_cleanse = val
            continue
        if keyn == "antihealgate":
            hp.gate_antiheal = val
            continue
        if keyn == "revealgate":
            hp.gate_reveal = val
            continue
        if keyn == "interruptgate":
            hp.gate_interrupt = val
            continue
        if keyn == "engagegate":
            hp.gate_engage = val
            continue
        if keyn == "globalgate":
            hp.gate_global = val
            continue

    return hp


def load_heroes_from_txt(path: str) -> List[HeroProfile]:
    heroes: List[HeroProfile] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            h = parse_hero_line(line)
            if h:
                heroes.append(h)
    return heroes


def hero_to_dict(h: HeroProfile) -> Dict[str, Any]:
    return {
        "hero_id": h.hero_id,
        "hero_name": h.hero_name,
        "role": h.role,
        "role_detail": h.role_detail,
        "lane": h.lane,
        "dmg": h.dmg,
        "rng": h.rng,
        "wc": h.wc,
        "camp": h.camp,
        "eng": h.eng,
        "peel": h.peel,
        "macro": h.macro,
        "global": h.global_,
        "cleanse": h.cleanse,
        "reveal": h.reveal,
        "stealth": h.stealth,
        "antiheal": h.antiheal,
        "contested": h.contested,
        "cc": h.cc,
        "styles": h.styles,
        "provides": h.provides,
        "needs": h.needs,
        "weaknesses": h.weaknesses,
        "power_curve": h.power_curve,
        "quality": {
            "eng": {"delivery": h.quality_eng.delivery, "reliability": h.quality_eng.reliability},
            "cc": {"delivery": h.quality_cc.delivery, "reliability": h.quality_cc.reliability},
            "save": {"delivery": h.quality_save.delivery, "reliability": h.quality_save.reliability},
            "int": {"delivery": h.quality_int.delivery, "reliability": h.quality_int.reliability},
        },
        "gates": {
            "cleanse": h.gate_cleanse,
            "antiheal": h.gate_antiheal,
            "reveal": h.gate_reveal,
            "interrupt": h.gate_interrupt,
            "engage": h.gate_engage,
            "global": h.gate_global,
        },
        "raw": h.raw,
    }
