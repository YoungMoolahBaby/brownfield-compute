"""Pass 3g step 8b (D28): a question sheet for each trade, for the installers' round.

The round sends the services set (the latest addendum's sheets, Addendum 7's, the models and their
schedules) to a plumber, an HVAC contractor, an electrician and a sprinkler contractor (Jon's
choices, 2026-11-22),
each with its own short list of questions. The questions are the design's open items the trade can
answer: the ones flagged for this round in steps 3 to 8, each pointing at the sheet or schedule it
is about and saying why we ask, with the design's own figure. Every figure comes from the designs on
the routes (`routed.summary`), the published schedules and the params, never typed in.

Then the same questions for every trade: how they would usually do this building and roughly what
it would cost (step 10's baseline, one contractor's word), what costs more than it buys, what's
missing to price it, whether they used the model, and whether we may publish what they say (by
trade and county only).

`brownfield questions` writes each trade's sheet as a letter-size PDF form to print and write on,
and all of them as Markdown (`out/pass3/round/`).
"""

from __future__ import annotations

import csv
import json
import re
import textwrap
from pathlib import Path

from . import OUT_DIR
from .servicesheets import SHEETS_REV
from .servicesifc import nominal

OUT = OUT_DIR / "pass3" / "round"
BIDSET = Path(__file__).resolve().parents[2] / "docs" / "pass3" / "bidset"
TRADES = {"P": "plumber", "M": "HVAC contractor", "E": "electrician", "FP": "sprinkler contractor"}
TITLES = {"P": "Plumbing", "M": "Heating, cooling and air", "E": "Electrical", "FP": "Sprinklers"}


def _rows(name: str, p: dict) -> list[dict]:
    """A schedule of the services model the design `p` last issued, as published."""
    from .designs import issue

    with open(BIDSET / f"services-{issue(p)}" / f"{name}.csv", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def _q(qid: str, ask: str, see: str, why: str) -> dict:
    return {"id": qid, "ask": ask, "see": see, "why": why}


def questions(p: dict, s7: dict) -> dict[str, list[dict]]:
    """Each trade's questions, then the common ones (`common`)."""
    from .designs import floors

    w, L, el, fh = s7["water"], s7.get("loop"), s7["electrical"], s7["fire"]
    edge = not floors(p)  # the edge design (Addendum 11): no floors, loop or substation; the plant on CO2 units
    hot, cold = w["paths"]["hot"], w["paths"]["cold"]
    elbows = hot["all_elbows"]["sizes"]
    gpm = [r["gpm_per_circuit"] for f in L["flats"].values() for r in f["rooms"]] if L else []
    meters = [m["l_h"] for m in L["meters"].values()] if L else []
    esp = [d["ms"]["esp"] for d in s7["ducts"].values()]
    ms_hi = s7["limits"]["ms_hi"]
    lines = [c["line_ft"] for c in s7["cooling"].values()]
    from .designs import paths

    bends = json.loads(paths(p)["7d"].read_text(encoding="utf-8"))["conduit_bends"]
    holes = _rows("holes", p)
    fire = _rows("firestop", p)
    judged = sum(int(r["count"]) for r in fire if r["F"] and "listed" in r["asks"].split(";")[0] and r["fit"] in ("partial", "none"))
    cpvc_none = sum(int(r["count"]) for r in fire if r["F"] and r["fit"] == "none" and "CPVC" in r["penetrant"])
    house = el["service"]["house"]
    element = next(r for r in house["rows"] if r["key"] == "swing_element")
    worst = fh["worst"]
    stair = next(c for c in fh["cases"] if c["kind"] == "stair")
    s = "systems.sprinkler."
    bfly = worst["need_psi"] + worst["valves_psi"] * (p[s + "butterfly_valve_el_ft"] / p[s + "shutoff_valve_el_ft"] - 1)
    up = w["upstream"]
    rpz = up["the double check valve assembly"] * (p["systems.plumbing.rpz_psi_40"] / p["systems.plumbing.dcva_psi_40"] - 1)
    upsized = sorted({c["key"] for pn in el["panels"].values() for c in pn["circuits"]
                      if c["awg"] != c["min_awg"]})
    hm = "systems.heat_meter."
    lp, c4 = w["loop"], w["c404"]

    out = {
        "P": [
            _q("P1", "Would you bend the PEX through its turns on bend supports, as drawn, or fit elbows?",
               "Addendum 5, item 4a; P-201 and P-202; the fittings schedule",
               f"The hot water reaches the worst shower ({hot['flat']}) with {hot['spare_psi']:.1f} psi to spare only bent. With an "
               f"elbow at every turn, the hot riser grows from {nominal(hot['sizes']['riser'])} to {nominal(elbows['riser'])} in. and the "
               f"branches from {nominal(hot['sizes']['branch'])} to {nominal(elbows['branch'])} in."),
            _q("P2", "The stacks and the branches above the slab are cast iron, for quiet. Would you price them so, or propose "
               "something else, and at what difference?",
               "P-201 and P-202; the lengths schedule",
               f"A neighbour's flush is heard through drywall. Enclosed in a wall, CMHC measured cast iron at "
               f"{p['systems.noise.stack_enclosed_cast_iron_dba']:g} dBA and PVC at {p['systems.noise.stack_enclosed_pvc_dba']:g}, "
               f"against the {p['systems.noise.limit_dba']:g} dBA the design holds to (trade-sponsored lab tests); no US code asks it "
               "(step 4)."),
            _q("P3", f"Each flat's lavatory, kitchen sink and washer share one {p['systems.routing.drain_branch_in']:g} in. horizontal "
               "drain, and each water closet's bend runs along its joist bay to the stack. Workable as drawn?",
               "P-102, P-201", "The joists' hole chart keeps drains out of the joists near their supports (step 7b)."),
            _q("P4", f"A {p['systems.services.vent_stack_in']:g} in. vent stack in each column's plumbing wall, not air admittance "
               "valves. What would you do?",
               "Addendum 5, item 4d; P-201 and P-202",
               "IPC 905.1 needs each dry vent to reach a vent stack, a stack vent or an AAV; AAVs must stay reachable in every flat."),
            _q("P5", f"Every hole through a stud, plate or joist is bored at the member's centre ({len(holes):,} holes in the holes "
               "schedule), the I-joists' within APA's chart. Is that how you'd work, or would you want it otherwise?",
               "Addendum 5, item 4b; the holes schedule; P-201 and P-202",
               "Bored at the centre, every pipe clears IPC 305.6 without a steel plate. Off-centre, plates come back."),
            _q("P6", "The hot-water plant: four outdoor CO2 heat pump water heaters (ECO2 Systems' SANCO2, basis of design) on stands "
               "on a pad outside the mechanical room heat two 200 gal ECO2 tanks in series; then a swing tank and a master mixing valve; "
               "a backup electric heater on its own pump circuit when the units fault. ECO2 warrants its units only on its own tanks, "
               "and voids pumped loops with secondary tees on their piping: would you pipe the backup's circuit to the storage as "
               "drawn, and would ECO2 approve it in writing? Is the pad workable (snow, service, the units' sound at the window)?",
               "Addendum 11; P-601; M-602",
               f"Four units give {w['heater']['capacity_kw']:g} kW above 5 F against Ecosizer's {w['heater']['need_kw']:.1f}; below 5 F "
               "they give less, by an amount ECO2 doesn't publish. ECO2 states 37 dBA at no distance; the nearest flat's window is "
               "under 2 m from the pad (step 11b).") if edge else
            _q("P6", "The hot-water plant takes the data center's warm water: a plate exchanger preheats, a water-to-water heat pump "
               "lifts it into two storage tanks in series, then a swing tank and a master mixing valve; a backup electric heater on "
               "the same circuit takes over when that water stops. Five pieces now stand on the mechanical room's floor. What would "
               "you change? Where would you hang its wall-hung equipment, and is the room big enough?",
               "Addendum 7, items 2 and 3; P-601; M-602",
               f"The preheat gives {w['heater']['preheat_share']:.0%} of the plant's heat. Two {p['systems.routing.tank_gal']:g} gal tanks, "
               "not one larger: the next single tank up won't pass the room's door. The exchanger, pumps, mixing valve and backflow "
               "assemblies are on the diagram only: no place in the model yet (step 9d)."),
            _q("P7", f"The street must give {w['street_need_psi']:.1f} psi at the peak; the water authority publishes none. Would you plan "
               "a booster now, or wait for the hydrant test?",
               "P-601", f"The design takes {p['systems.plumbing.street_psi']:g} psi as a placeholder; the cold path leaves "
               f"{cold['spare_psi']:.1f} psi at its worst shower."),
            _q("P8", f"The domestic service's double check valve assembly: would this authority ask for a reduced-pressure zone "
               f"assembly instead (about {rpz:.1f} psi more at the peak)?",
               "P-601", "Step 4 took the double check; the authority decides."),
            _q("P9", "No fixture is chosen: the sizes drawn are placeholders. Which would you price, and do any change the rough-ins?",
               "the fixtures schedule; P-101 to P-103", "The water closets sit in joist bays; a different rough-in moves the bend."),
            _q("P10", "Each flat's hot water is a loop of its own: its branch runs past the fixtures to the lavatory, where a "
               f"thermostatic balancing valve in the vanity (set {p['systems.hot_water.tbv_set_f']:g} F) starts a "
               f"{nominal(lp['flat_return_in'])} in. return to the return riser. Have you built flats' loops like this? Would you put the "
               "valve somewhere else, or meet the energy code another way?",
               "Addendum 7, item 1; P-601 (each flat's loop); P-201 and P-202",
               f"IECC C404.5 holds every fixture to half a gallon from circulating water: the worst here holds {c4['worst']['oz']:.0f} fl oz. "
               f"The flats' loops lose {lp['flats_loss_btuh'] / 3.412142:,.0f} W of the loop's {lp['loss_btuh'] / 3.412142:,.0f}. We weighed "
               "a manifold in each flat and heat trace instead (step 9c)."),
        ],
        "M": [
            *([_q("M1", "Each flat's mini-split is its only heat: its supplies reach the bedrooms, the study and the living room, which "
                  "the kitchen, entry, hall and passage open on; each top-floor bath has a 500 W wall heater on its own circuit (the "
                  "baths below lose no heat). Would you heat them so?", "Addendum 11; M-101 to M-103; M-601; E-602",
                  "IBC 1204.1 asks heat in every space for occupancy; the floors heated these rooms before. A duct to the bath found "
                  "no path in the back flats' soffits (step 11c)."),
               _q("M2", "On the design day each mini-split heats its flat alone, its line set's derating counted: would you choose another "
                  "unit for this climate, or add anything for its defrost?", "Addendum 11; M-601; M-602",
                  "Fujitsu's table gives the unit's capacity at the design dry bulb; the units now heat all winter (step 9a's check, now "
                  "the design).")] if edge else [
            _q("M1", f"Each room's radiant loops are balanced to {min(gpm):.3f}-{max(gpm):.3f} gpm. Can a manifold's balancing valves "
               "and flow gauges be set that fine, or would you have each room's actuator cycle its loops instead?",
               "M-601 (the flats' loops and flows)", "The low-heat rooms' loops carry very little water at the design hour (step 3)."),
            _q("M2", f"Each flat's heat meter (Kamstrup MULTICAL 403, qp {p[hm + 'qp_m3h']:g} m3/h) sees {min(meters):.0f}-{max(meters):.0f} "
               f"l/h at design; at part load the flow falls toward its {p[hm + 'cutoff_l_h']:g} l/h cut-off, under which it counts nothing. "
               "Would you choose another meter, or hold a minimum flow?",
               "M-601", "The meter bills each flat for its heat (step 3)."),
            _q("M3", f"Each ERV has an electric preheater ({p['systems.electrical.preheater_va']:,.0f} W, in its outdoor-air duct). Would you "
               "fit a hot-water coil off the building loop instead, and would Broan's warranty stand with one?",
               "M-101 to M-103; M-601", "Broan's manual names only an electric heater. A coil would use the data center's heat (step 3)."),
            ]),
            _q("M4", "The flats' ducts run in soffits below the rated ceiling, not in the joists. Buildable as drawn, at these soffits' "
               "depths?", "M-101 to M-103",
               "The joists' hole chart all but bars these ducts, and IBC 717.6.2 would ask a ceiling radiation damper at every "
               "register through a rated ceiling."),
            _q("M5", f"Each mini-split's fan is set to its ducts: {min(esp):.2f}-{max(esp):.2f} in. w.c., {sum(1 for x in esp if abs(x - ms_hi) < 1e-9)} "
               f"of {len(esp)} at the unit's highest ({ms_hi:.2f}). Would you set them so, or size the ducts up?",
               "Addendum 5, item 4e; M-601 (each flat's setting)",
               f"Fujitsu's function setting covers {s7['limits']['ms_lo']:.2f}-{ms_hi:.2f} in. w.c. (step 7c)."),
            _q("M6", "Each mini-split's condensate drains by gravity in a soffit, with a UL 508 water-level switch at its drain wired to "
               "the unit's forced stop. Would you do that, or fit a pump?",
               "Addendum 5, item 4e; M-101 to M-103", "IMC 307.2.3 asks an overflow protection over a finished ceiling (step 7c)."),
            _q("M7", f"The line sets run {min(lines):.0f}-{max(lines):.0f} ft up the plumbing walls to {len(lines)} outdoor units on stands "
               "on the roof. Anything you'd change for installing and servicing them (the roof hatch, snow, stands)?",
               "M-104", "Fujitsu's derating for the line set is in each unit's capacity (step 3)."),
            _q("M8", "The ERV's fresh air goes into the mini-split's return (Broan's kit). Have you installed it that way?",
               "M-101 to M-103", "It saves a separate supply duct to each room (step 7b)."),
            *([] if edge else [_q("M9", f"The building loop: a plate exchanger off the data center's return, {L['gpm']:.2f} gpm at {L['pump_ft']:.1f} ft of "
               f"head, a {L['header_in']:g} in. header and a riser pair a column. Comments on the loop or its pump?",
               "Addendum 7, item 4; M-601", f"The pump's curve gives {L['pump_curve_ft']:.1f} ft at that flow at its highest speed. The "
               "exchanger and pump are bases of design, not selections (step 3)."),
            _q("M10", f"When the data center's heat stops, each flat's mini-split takes the rooms: it's set to heat "
               f"{p['systems.controls.ms_offset_k']:g} K under the floor's setpoint, and the manager confirms the setting at the "
               "season's change. Workable, or would you want a building-wide signal to the units?",
               "Addendum 7, items 3 and 5; M-602",
               "Fujitsu's units take only an operation/stop and a forced-stop input, so the plant can't switch them to heat (step 9b)."),
            ]),
        ],
        "E": [
            _q("E1", "Each mini-split's outdoor unit is on a GFCI breaker (NEC 210.8(F)). Which breaker have you used on inverter "
               "units without nuisance trips?",
               "E-602 (each flat's mini-split circuit)",
               "Pennsylvania didn't amend 210.8(F), and the 2020 TIA's exception for listed HVAC equipment expired 2026-09-01. The "
               "set asks a breaker made for inverter equipment; we found no catalogue number (step 5)."),
            _q("E2", f"The feeders run in PVC straight under the slab, {min(b['degrees'] for b in bends):.0f}-"
               f"{max(b['degrees'] for b in bends):.0f}° of bends from the meter to a panel, no pull point. Would you pull them as drawn? "
               "Will the field-made sweeps fit the riser bays?",
               "Addendum 5, item 4c; E-101; E-601",
               f"NEC 352.26 allows {p['systems.services.conduit_bends_max_deg']:g}° between pull points (step 7e)."),
            _q("E3", "Every hole for NM-B cable is bored at the member's centre, with no steel plates. Is that how you work?",
               "Addendum 5, item 4b; the holes and plates schedules",
               f"NEC 300.4(A)(1) asks a plate only within {nominal(p['systems.services.nec_bore_edge_in'])} in. of the edge."),
            _q("E4", f"The meters go outdoors on the annex's wall: a stack with a {el['service']['main_a']:.0f} A main fed by "
               f"{el['service']['sets']} sets of {el['service']['size']} kcmil a phase. Has FirstEnergy approved parallel sets to a meter "
               "stack for you?", "E-601", "FirstEnergy wants meters outdoors, and approves parallel sets case by case (step 5)."),
            _q("E5", "The outlets, switches and luminaires aren't placed in the model: each circuit is drawn to its farthest outlet. Can "
               "you price from the panel schedules, or do you need a device layout?",
               "E-101 to E-103; E-602", "Step 5 designed each circuit's breaker, wire and drop; the devices' count is NEC 210.52's."),
            _q("E6", f"Each circuit is held to {s7['limits']['vd']['branch']:.0%} drop at its farthest outlet, so some are a size up "
               f"({', '.join(upsized)}). Would you wire them so?",
               "E-602", f"Feeder and branch together reach {max(el['total_drop'].values()):.1%} at worst, inside the "
               f"{s7['limits']['vd']['total']:.0%} the NEC's informational notes give."),
            _q("E7", f"The house panel is {house['breaker_a']:.0f} A: the four CO2 units on their own {p['systems.co2_plant.breaker_a']:g} A "
               f"breakers, their lines' heat trace, the swing tank's {p['systems.house.swing_element_va'] / 1000:.1f} kW element counted "
               f"as {element['kind']}, and the backup water heater counted in place of the units, never both (a wired interlock). Agree?",
               "Addendum 11; E-601; M-602",
               f"NEC 220.60 counts the larger of two loads that can't run together; the element's design day takes it "
               f"{house['element_h']:.1f} h.") if edge else
            _q("E7", f"The house panel is {house['breaker_a']:.0f} A: the swing tank's {p['systems.house.swing_element_va'] / 1000:.1f} kW "
               f"element counted as {element['kind']}, and the backup water heater counted in place of the heat pump, never both "
               "(a wired interlock). Agree?",
               "Addendum 7, item 3; E-601; M-602",
               f"The element's design day takes it {house['element_h']:.1f} h (NEC Article 100: continuous at "
               f"{p['systems.house.continuous_h']:g} h or more). NEC 220.60 counts the larger of two loads that can't run together."),
        ],
        "FP": [
            _q("F1", f"The most demanding design needs {worst['need_psi']:.1f} of the {fh['target_psi']:.0f} psi the street gives less its "
               f"margin, on a placeholder street pressure of {p['systems.plumbing.street_psi']:g} psi. Would you calculate it again, and "
               "would you size the pipe up before the hydrant test?",
               "FP-601; FP-101 to FP-103", f"{worst['flat']}'s {worst['comp']} area, {len(worst['design'])} sprinklers, {worst['q_gpm']:.0f} gpm."),
            _q("F2", "The control valves are OS&Y gate valves on each side of the backflow assembly, supervised. What would you fit?",
               "Addendum 6, item 1; FP-601",
               f"A butterfly valve's loss would put the design at {bfly:.1f} psi, "
               + ("over" if bfly > fh["target_psi"] else "within") + f" the {fh['target_psi']:.0f}."),
            _q("F3", f"The stair is calculated with all {stair['heads']} of its sprinklers flowing ({stair['q_gpm']:.0f} gpm). Would the "
               "authority hold it to 13R's four?", "FP-601", "Read the safe way until the authority says (step 6)."),
            _q("F4", "CPVC throughout, concealed, through the I-joists' webs at APA's chart; strip soffits with sprinklers on each side. "
               "Anything you'd lay out otherwise?", "FP-101 to FP-103; the holes schedule",
               "Tyco's obstruction rules (TFP490) set the soffits' sprinklers (step 7c)."),
            _q("F5", f"{cpvc_none} CPVC drops through rated ceilings have no listed firestop system we found. What do you use there?",
               "the firestop schedule (Addendum 5, item 5)", f"{judged} rated openings go by the maker's engineering judgment."),
            _q("F6", "A separate, supervised fire service with a monitoring panel, an exterior horn-strobe and a fire department "
               "connection. Anything missing?", "FP-601", "13R and IBC 903.4 (step 6)."),
        ],
    }
    out["common"] = [
        _q("C1", "How would you usually do this part of a 12-flat walk-up like this one, and roughly what would it cost?",
           "", "Step 10 prices the usual walk-up from sources. Your answer is one contractor's word, cited by trade and county "
           "only, with your OK."),
        _q("C2", "What here costs more than it should, or more than it buys?", "", ""),
        _q("C3", "What's missing that you'd need to price it?", "", ""),
        _q("C4", "Did you open the model (the IFC files) or the 3D viewer? Would you take quantities from them, or from the sheets "
           "and schedules?", "the plan room", "Whether trades use a model is an open question of the study (D27)."),
        _q("C5", "G-002 lists the tests and inspections. Anything there you'd do otherwise for your work, or price separately?",
           "G-002; Addendum 7, item 6", "Most are the codes' own tests; the rest prove the design's claims at commissioning."),
        _q("C6", "May we publish your comments, by your trade and county only (no name)?", "", ""),
    ]
    if edge:  # the M list renumbered after the network design's M1-M3 and M9-M10 left out
        out["M"] = [dict(q, id=f"M{i}") for i, q in enumerate(out["M"], 1)]
    return out


def markdown(qs: dict[str, list[dict]]) -> str:
    lines = ["# The installers' round: questions", "",
             "Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Short answers are fine.", ""]
    for t, who in TRADES.items():
        lines += [f"## {TITLES[t]}: for the {who}", ""]
        for q in qs[t] + qs["common"]:
            lines.append(f"- **{q['id']}.** {q['ask']}")
            if q["see"]:
                lines.append(f"  - See: {q['see']}.")
            if q["why"]:
                lines.append(f"  - Why we ask: {q['why']}")
        lines.append("")
    return "\n".join(lines)


PAGE_W, PAGE_H, MARGIN = 8.5, 11.0, 0.75
STUDY_REF = re.compile(r"\s*\((?:step|D)\s?[0-9][^)]*\)")  # "(step 7c)", "(D27)": ours, not the reader's


def for_the_reader(text: str) -> str:
    """A question's text as the trade gets it: without the study's own references."""
    return STUDY_REF.sub("", text)


def write_pdf(trade: str, qs: dict[str, list[dict]], path: Path, png: Path | None = None) -> int:
    """One trade's sheet as a letter-size form: each question, where it's drawn, why we ask, and
    ruled lines to answer on, and each page as a PNG in `png` if given. Returns its pages."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages

    items = qs[trade] + qs["common"]
    path.parent.mkdir(parents=True, exist_ok=True)
    pages = 0

    def new_page(pdf, first: bool):
        nonlocal pages
        fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, PAGE_W)
        ax.set_ylim(0, PAGE_H)
        ax.axis("off")
        pages += 1
        y = PAGE_H - MARGIN
        if first:
            ax.text(MARGIN, y, "12-flat walk-up: the installers' round", fontsize=15, weight="bold", va="top")
            y -= 0.35
            ax.text(MARGIN, y, f"{TITLES[trade]}: questions for the {TRADES[trade]}", fontsize=12, va="top")
            y -= 0.32
            for t in textwrap.wrap("Made up, from the brownfield-compute study: not a real project, nothing is out to bid. The set "
                                   f"({SHEETS_REV}'s sheets, the models and their schedules) was designed in full before bidding; we're "
                                   "asking the people who would install it whether it works. Short answers are fine: write on this "
                                   "sheet, mark up the drawings, or talk it through with whoever sent it.", 100):
                ax.text(MARGIN, y, t, fontsize=8.5, va="top", color="#424242")
                y -= 0.17
            y -= 0.12
        ax.text(PAGE_W - MARGIN, 0.45, f"{TITLES[trade]} {pages}", fontsize=7, ha="right", color="#757575")
        return fig, ax, y

    def save(pdf, fig):
        pdf.savefig(fig)
        if png is not None:
            png.mkdir(parents=True, exist_ok=True)
            fig.savefig(png / f"{path.stem}-{pages}.png", dpi=60, facecolor="white")

    with matplotlib.rc_context({"pdf.fonttype": 42}), PdfPages(
            path, metadata={"Title": f"walk-up installers' round: {TRADES[trade]}", "Creator": "brownfield-compute pass 3g step 8b",
                            "CreationDate": None}) as pdf:
        fig, ax, y = new_page(pdf, True)
        for q in items:
            body = textwrap.wrap(for_the_reader(q["ask"]), 92)
            notes = ((textwrap.wrap("See: " + q["see"], 104) if q["see"] else [])
                     + (textwrap.wrap("Why we ask: " + for_the_reader(q["why"]), 104) if q["why"] else []))
            need = 0.19 * len(body) + 0.15 * len(notes) + 0.95
            if y - need < MARGIN + 0.3:
                save(pdf, fig)
                plt.close(fig)
                fig, ax, y = new_page(pdf, False)
            ax.text(MARGIN, y, q["id"], fontsize=10, weight="bold", va="top")
            for t in body:
                ax.text(MARGIN + 0.45, y, t, fontsize=10, va="top")
                y -= 0.19
            for t in notes:
                ax.text(MARGIN + 0.45, y, t, fontsize=7.8, va="top", color="#616161")
                y -= 0.15
            for _ in range(3):
                y -= 0.24
                ax.plot([MARGIN + 0.45, PAGE_W - MARGIN], [y, y], color="#bdbdbd", lw=0.5)
            y -= 0.22
        save(pdf, fig)
        plt.close(fig)
    return pages


def run(apt: dict, p: dict, out: Path = OUT, s7: dict | None = None) -> dict:
    from . import routed

    if s7 is None:
        routes = routed.load(apt, p)
        if routes is None or not routes.fresh:
            raise SystemExit("no fresh routes: `brownfield routes` first")
        s7 = routed.summary(apt, p, routes)
    qs = questions(p, s7)
    out.mkdir(parents=True, exist_ok=True)
    md = out / "questions.md"
    md.write_text(markdown(qs) + "\n", encoding="utf-8")
    pdfs = {t: out / f"questions-{TRADES[t].split()[0].lower()}.pdf" for t in TRADES}
    pages = {t: write_pdf(t, qs, pdfs[t], out / "png") for t in TRADES}
    return {"questions": qs, "md": md, "pdfs": pdfs, "pages": pages}


def report(r: dict) -> str:
    qs = r["questions"]
    lines = ["Pass 3g step 8b: the installers' round, a question sheet for each trade", ""]
    for t, who in TRADES.items():
        lines.append(f"{TITLES[t]} ({who}): {len(qs[t])} questions and the {len(qs['common'])} common ones, "
                     f"{r['pages'][t]} pages ({r['pdfs'][t].name})")
        for q in qs[t]:
            lines.append(f"  {q['id']}. {q['ask']}")
    lines += ["", "For every trade:", *(f"  {q['id']}. {q['ask']}" for q in qs["common"])]
    return "\n".join(lines)
