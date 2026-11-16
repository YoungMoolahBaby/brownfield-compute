"""Pass 3b: the build sequence, read back from forge `build` (CortenForge sim-core).

Walls are framed flat on the deck in panels and tilted up about their bottom edge: sim-core
raises each panel on a hinge with a position servo, and the servo's torque at the start of the
lift is what the crew has to supply at the top plate (force = torque / panel height). Cap
plates, joists and rims are released 10 mm above their seats as free bodies and have to settle
where the drawings put them.
"""

from __future__ import annotations

import json
from pathlib import Path

from . import OUT_DIR

GROUPS = ("facades", "end walls", "spine rows", "stair walls")


def load() -> dict:
    path = OUT_DIR / "pass3" / "build.json"
    if not path.exists():
        raise SystemExit("no out/pass3/build.json: run `cargo run --release -- build` in forge/ first")
    return json.loads(path.read_text(encoding="utf-8"))


def lift_summary(b: dict) -> list[dict]:
    """Per storey and wall group: panels, the heaviest and the hardest lift, the crew it needs."""
    rows = []
    storeys = sorted({x["storey"] for x in b["lifts"]})
    for s in storeys:
        for g in GROUPS:
            xs = [x for x in b["lifts"] if x["storey"] == s and x["group"] == g]
            if not xs:
                continue
            rows.append({
                "storey": s, "group": g, "panels": len(xs), "longest_m": max(x["length_m"] for x in xs),
                "heaviest_kg": max(x["kg"] for x in xs), "lift_lbf": max(x["lift_lbf"] for x in xs),
                "framed_lift_lbf": max(x["framed_lift_lbf"] for x in xs), "crew": max(x["crew"] for x in xs),
                "jacks": sum(1 for x in xs if x["jack"]), "sheathed": any(x["sheathed"] for x in xs),
            })
    return rows


def sim_vs_statics(b: dict) -> float:
    """Largest relative gap between the servo's peak torque and statics (weight x lever at flat)."""
    return max(abs(x["peak_servo_nm"] / x["statics_flat_nm"] - 1) for x in b["lifts"])


def report(b: dict) -> str:
    lbf = b["crew_lift_lbf"]
    lines = [
        f"Wood {b['density_kgm3']:.0f} kg/m3; facades and end walls sheathed flat ({b['osb_kgm2']:.1f} kg/m2 OSB) before "
        f"they go up; a worker lifts at most {lbf:.0f} lbf (NIOSH); more than {b['crew_max']:.0f} on one panel means a wall jack.",
        "",
        "| Storey | Walls | Panels | Longest m | Heaviest kg | Hardest lift lbf (unsheathed) | Crew | Need a jack |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in lift_summary(b):
        un = f" ({r['framed_lift_lbf']:.0f})" if r["sheathed"] else ""
        lines.append(f"| {r['storey']} | {r['group']} | {r['panels']} | {r['longest_m']:.1f} | {r['heaviest_kg']:.0f} | "
                     f"{r['lift_lbf']:.0f}{un} | {r['crew']:.0f} | {r['jacks']} |")
    lines += ["", f"sim-core's servo against statics at the start of every lift: within {sim_vs_statics(b):.1%}.", "",
              "| Storey | Set down | Members | Worst landing mm | Off their seats | Deepest contact mm |", "|---|---|---|---|---|---|"]
    for st in b["stages"]:
        lines.append(f"| {st['storey']} | {st['stage']} | {st['bodies']} | {st['max_err_mm']:.2f} | {st['off_seat']} | {st['max_depth_mm']:.2f} |")
    n = b["negative_control"]
    if n:
        lines += ["", f"Out of order (the check bites): {n['stage']}: {n['fell']} of {n['bodies']} fell."]
    return "\n".join(lines)


def gif(frames: Path, out: Path, ms: int = 260, hold_ms: int = 2500) -> int:
    """The frames as an animated GIF, the last one held."""
    from PIL import Image

    paths = sorted(frames.glob("f*.png"))
    if not paths:
        raise SystemExit(f"no frames in {frames}")
    imgs = [Image.open(p).convert("RGB") for p in paths]
    # One palette for all frames (taken from the finished building) keeps the colours steady.
    pal = imgs[-1].quantize(colors=96, method=Image.Quantize.MEDIANCUT)
    frames_q = [im.quantize(palette=pal, dither=Image.Dither.NONE) for im in imgs]
    durations = [ms] * (len(frames_q) - 1) + [hold_ms]
    out.parent.mkdir(parents=True, exist_ok=True)
    frames_q[0].save(out, save_all=True, append_images=frames_q[1:], duration=durations, loop=0, optimize=True)
    return len(frames_q)
