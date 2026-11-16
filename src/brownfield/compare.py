"""Pass 3b: the walk-up's three structural systems side by side, from their sizing (frame.py,
steel.py, masonry.py), their CortenForge models (forge `framing`, `framing steel`, `masonry`) and
their builds in sim-core (forge `build`, `build steel`, `build masonry`)."""

from __future__ import annotations

import json

from . import OUT_DIR, frame, house, masonry, steel
from .params import load_params, values


def _read(name: str) -> dict | None:
    path = OUT_DIR / "pass3" / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def gather() -> dict:
    p = values(load_params())
    apt = house.apartment()
    wd, sd, md = frame.design(apt, p), steel.design(apt, p), masonry.design(apt, p)
    density = frame.wood_density(p["pass3.build.wood_g"], p["pass3.build.wood_mc"])
    wf, sf, mm = _read("framing.json"), _read("framing_steel.json"), _read("masonry_model.json")
    wb, sb, mb = _read("build.json"), _read("build_steel.json"), _read("build_masonry.json")

    def lifts(b):
        if not b:
            return None
        x = max(b["lifts"], key=lambda r: r["lift_lbf"])
        return {"kg": max(r["kg"] for r in b["lifts"]), "lbf": x["lift_lbf"], "crew": max(r["crew"] for r in b["lifts"]),
                "jacks": sum(1 for r in b["lifts"] if r["jack"]), "panels": len(b["lifts"]),
                "landing_mm": max(st["max_err_mm"] for st in b["stages"])}

    return {
        "wood": {
            "floor": f"{frame.member_name(wd['floor_joist'])} at 16 in.", "floor_in": wd["floor_depth_in"],
            "walls": "2x6 studs at 16 in. (facades), double 2x4 rows (spine)",
            "structure_t": wf["wood_m3"] * density / 1e3 if wf else None, "pieces": wf["members"] if wf else None,
            "foundation_m3": wf["concrete_m3"] if wf else None,
            "footings_in": (max(wd["footings"]["facade_width_in"], 12), max(wd["footings"]["spine_width_in"], 12)),
            "lift": lifts(wb), "combustible": True,
            "known": "SFPA lumber spans to 0.4 in.; APA I-joist spans within 2%",
        },
        "steel": {
            "floor": f"{sd['floor_joist'][0]} C-joists at 16 in.", "floor_in": sd["floor_depth_in"],
            "walls": f"{sd['studs'][1]['exterior']['name']} studs at 16 in. (ground-floor facades)",
            "structure_t": sf["steel_kg"] / 1e3 if sf else None, "pieces": sf["members"] if sf else None,
            "foundation_m3": sf["concrete_m3"] if sf else None,
            "footings_in": (max(sd["footings"]["facade_width_in"], 12), max(sd["footings"]["spine_width_in"], 12)),
            "lift": lifts(sb), "combustible": False,
            "known": "SFIA joist spans to 0.5 in. (16 cases)",
        },
        "masonry": {
            "floor": f"8 in. hollow-core planks ({md['floor_plank'].split(' ')[0]})", "floor_in": 8.0,
            "walls": "8 in. concrete block, partly grouted",
            "structure_t": (mm["block_t"] + mm["lintel_t"] + mm["plank_t"]) if mm else None, "pieces": mm["pieces"] if mm else None,
            "foundation_m3": mm["foundation_concrete_m3"] if mm else None,
            "footings_in": (md["footings"]["facade_width_in"], md["footings"]["spine_width_in"]),
            "plank_kg": md["plank_kg"], "block_kg": p["pass3.masonry.block_lb"] * 0.453592,
            "planks": mm["planks"] if mm else None, "blocks": mm["blocks_full_equivalent"] if mm else None,
            "landing_mm": max(lv["max_err_mm"] for lv in mb["levels"]) if mb else None,
            "worst_support": mm["worst_support"] if mm else None, "combustible": False,
            "known": "TMS ASD worked example to 0.09%",
        },
    }


def report(g: dict) -> str:
    w, s, m = g["wood"], g["steel"], g["masonry"]
    f = lambda v, fmt="{:,.0f}": "-" if v is None else fmt.format(v)
    lift = lambda x: "-" if not x["lift"] else (f"{x['lift']['kg']:.0f} kg wall panel, {x['lift']['lbf']:.0f} lbf at the top: "
                                                 f"a crew of {x['lift']['crew']:.0f}, {x['lift']['jacks']} wall jacks")
    rows = [
        ("Floors", w["floor"], s["floor"], m["floor"]),
        ("Floor structure depth (in.)", f(w["floor_in"], "{:.1f}"), f(s["floor_in"], "{:.1f}"), f(m["floor_in"], "{:.1f}") + " (no ceiling needed below)"),
        ("Bearing walls", w["walls"], s["walls"], m["walls"]),
        ("Structure above the foundation (t)", f(w["structure_t"]), f(s["structure_t"]), f(m["structure_t"])),
        ("Pieces placed", f(w["pieces"]), f(s["pieces"]), f(m["pieces"])),
        ("Footings, facades / spine (in. wide)", "{:.0f} / {:.0f}".format(*w["footings_in"]), "{:.0f} / {:.0f}".format(*s["footings_in"]),
         "{:.0f} / {:.0f}".format(*m["footings_in"])),
        ("Foundation concrete (m3)", f(w["foundation_m3"], "{:.0f}"), f(s["foundation_m3"], "{:.0f}"), f(m["foundation_m3"], "{:.0f}")),
        ("Heaviest lift, and how", lift(w), lift(s),
         f"{m['plank_kg']:,.0f} kg plank by crane ({f(m['planks'])} of them); {m['block_kg']:.0f} kg blocks by hand (~{f(m['blocks'])})"),
        ("Placed members land within (mm)", f(w["lift"]["landing_mm"] if w["lift"] else None, "{:.2f}"),
         f(s["lift"]["landing_mm"] if s["lift"] else None, "{:.2f}"), f(m["landing_mm"], "{:.2f}")),
        ("Combustible structure", "yes" if w["combustible"] else "no", "yes" if s["combustible"] else "no", "yes" if m["combustible"] else "no"),
        ("Sizing checked against", w["known"], s["known"], m["known"]),
    ]
    out = ["| | Wood platform frame | Light steel frame | Block walls + precast planks |", "|---|---|---|---|"]
    out += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    return "\n".join(out)
