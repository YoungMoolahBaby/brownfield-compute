"""Pass 3g step 9c (D28): the walk-up's tests and inspections, for Addendum 7.

Each item says what is tested, who does it, when, what passes and on what it rests: a code's own
test, quoted from the copy saved under `data/raw/` (`checks` finds every quotation there), or one of
the design's claims, with its figure from the design itself. Written as specification section
01 45 00 (`out/pass3/acceptance.md`)."""

from __future__ import annotations

import re
from pathlib import Path

from . import ROOT

RAW = ROOT / "data" / "raw" / "pass3g"
SRC = {
    "IPC": (RAW / "step7" / "ipc3" / "ipc3_pa.txt", "PA 2021 IPC (UpCodes), chapter 3"),
    "IMC3": (RAW / "step7" / "imc" / "imc3_pa.txt", "PA 2021 IMC (UpCodes), chapter 3"),
    "IMC11": (RAW / "step9" / "imc" / "imc11.txt", "PA 2021 IMC (UpCodes), chapter 11"),
    "IMC12": (RAW / "step9" / "imc" / "imc12.txt", "PA 2021 IMC (UpCodes), chapter 12"),
    "IECC-R": (RAW / "dl" / "upc" / "iecc_re4.txt", "PA 2021 IECC (UpCodes), chapter RE 4"),
    "IECC-C": (RAW / "step9" / "iecc" / "iecc_ce4.txt", "PA 2021 IECC (UpCodes), chapter CE 4"),
    "13R": (RAW / "raw" / "sprinkler" / "13R_A2021_SDR.txt", "NFPA 13R, the 2022 edition's second draft (NFPA's public report)"),
    "USFA": (RAW / "raw" / "sprinkler" / "USFA_sm_0263.txt", "USFA/NFA, Commercial Fire Sprinkler System Plans Review (2023)"),
    "UCC": (RAW / "step9" / "pa" / "s403_45.txt", "34 Pa. Code 403.45 (Inspections, commercial construction)"),
}


def _norm(s: str) -> str:
    s = s.replace("–", "-").replace("—", "-").replace("’", "'").replace("“", '"').replace("”", '"')
    s = re.sub(r"[^\x20-\x7e]", " ", s)
    return re.sub(r"\s+", " ", s).strip().lower()


def items(p: dict, s7: dict) -> list[dict]:
    """The schedule, area by area. Each: id, area, what, who, when, passes, basis, quotes [(src, text)]."""
    from .loads import ventilation
    from .systems import latest_model, load

    h, c, pl = "systems.hot_water.", "systems.controls.", "systems.plumbing."
    w, L, fh, ducts = s7["water"], s7["loop"], s7["fire"], s7["ducts"]
    apt = load(latest_model())
    v = ventilation(apt, p)
    cfm = max(x["design_cfm"] for x in v.values())
    imc = max(x["imc_cfm"] for x in v.values())
    esp = sorted(d["ms"]["esp"] for d in ducts.values())
    flat_gpm = [f["gpm"] for f in L["flats"].values()]
    c4 = w["c404"]
    plumber, hvac_, elec, fire_ = "the plumber (the permit holder)", "the HVAC contractor", "the electrician", "the sprinkler contractor"
    cx = "the balancing contractor, witnessed by the engineer"
    official = "the construction code official"
    rough, cover = "at rough-in, before the walls and ceilings close", "before it is covered"
    out = [
        # -- Plumbing: IPC 312's own tests.
        {"id": "P-1", "area": "Plumbing", "what": "drainage and vent piping, water test", "who": plumber, "when": rough,
         "passes": "each section filled to at least a 10 ft head of water and held 15 min, tight at all points (cast iron: the air test "
                   "of 312.3 is the alternative)",
         "basis": "IPC 312.2", "quotes": [("IPC", "sections shall not be tested with less than a 10-foot (3048 mm) head of water"),
                                          ("IPC", "This pressure shall be held for not less than 15 minutes. The system shall then be tight at all points")]},
        {"id": "P-2", "area": "Plumbing", "what": "drainage and vent, final test", "who": plumber,
         "when": "with the fixtures set and their traps filled",
         "passes": "seen complete and to the code; a smoke test, if used, holds 1 in. w.c. for 15 min", "basis": "IPC 312.4",
         "quotes": [("IPC", "The final test of the completed drainage and vent systems shall be visual")]},
        {"id": "P-3", "area": "Plumbing", "what": "water supply piping, cold and hot and the flats' loops", "who": plumber, "when": rough,
         "passes": f"tight under water at not less than its working pressure ({p[pl + 'max_static_psi']:g} psi, the most static the building's "
                   "piping sees) for 15 min; with water, not air: the pipe is PEX",
         "basis": "IPC 312.5", "quotes": [("IPC", "tested and proved tight under a water pressure not less than the working pressure of the system"),
                                          ("IPC", "for piping systems other than plastic, by an air test")]},
        {"id": "P-4", "area": "Plumbing", "what": "each backflow prevention assembly (the domestic and the fire service's double checks)",
         "who": "a tester to one of the ASSE 5000-series or CSA B64.10 procedures", "when": "at installation, after any repair, then yearly",
         "passes": "the procedure's own criteria; yearly inspection that each is operable", "basis": "IPC 312.10.1-312.10.2",
         "quotes": [("IPC", "shall be tested at the time of installation, immediately after repairs or relocation and at least annually")]},
        {"id": "P-5", "area": "Plumbing", "what": "the building sewer, where it is in the contract", "who": plumber, "when": "before backfill",
         "passes": "filled to a 10 ft head of water, held 15 min", "basis": "IPC 312.6",
         "quotes": [("IPC", "testing with not less than a 10-foot (3048 mm) head of water and maintaining such pressure for 15 minutes")]},
        # -- Hot water: the energy code and the design (Addendum 7).
        {"id": "HW-1", "area": "Hot water", "what": "the flats' hot pipe's insulation", "who": official, "when": "at the energy inspection, " + cover,
         "passes": f"{p['systems.routing.branch_insulation_in']:g} in. on the flats' hot pipe and their loops' returns, continuous but "
                   "where it passes a plate or joist; the bored holes for the bare pipe",
         "basis": "IECC C404.4, Table C403.12.3", "quotes": [("IECC-C", "Pipe insulation shall be continuous except where the piping passes through a framing member")]},
        {"id": "HW-2", "area": "Hot water", "what": "each hot fixture's pipe off its flat's loop, as built", "who": official, "when": rough,
         "passes": f"the sizes and runs drawn: each fixture's own pipe at its size, no fixture more than {c4['limit_oz']:g} fl oz from "
                   f"circulating water (the design's worst {c4['worst']['oz']:.0f}, {c4['worst']['flat']}'s {c4['worst']['fixture']})",
         "basis": "IECC C404.5.2", "quotes": [("IECC-C", "For other plumbing fixtures or plumbing appliances; not more than 0.5 gallon")]},
        {"id": "HW-3", "area": "Hot water", "what": "each flat's loop, balanced", "who": cx, "when": "at commissioning, before occupancy",
         "passes": f"each flat's balancing valve set at {p[h + 'tbv_set_f']:g} F; with the plant in normal running and P-3 on, each flat's "
                   f"return at its valve's gauge at or over {p[h + 'return_min_f']:g} F (the design: {w['loop']['gpm']:.2f} gpm in all, "
                   f"{w['recirc']['flat_gpm']:.2f} a flat)",
         "basis": "the design (Addendum 7); WHO's 50 C return", "quotes": []},
        {"id": "HW-4", "area": "Hot water", "what": "the recirculation pump's control", "who": cx, "when": "at commissioning",
         "passes": f"P-3 stops when TS-5 reads {p[c + 'recirc_stop_f']:g} F and starts under {p[h + 'return_min_f']:g} F",
         "basis": "IECC C404.6.1; the sequence (23 09 93)",
         "quotes": [("IECC-C", "shall automatically turn off the pump when the water in the circulation loop is at the desired temperature")]},
        {"id": "HW-5", "area": "Hot water", "what": "the plant: its setpoints, its interlock and its fallback", "who": cx, "when": "at commissioning",
         "passes": f"ST-1 held at {p[h + 'storage_f']:g} F; MV-1 sends {p[h + 'distribution_f']:g} F; P-2 runs only with the heating cycle; "
                   "BK-1 can't be energized while HP-1 is enabled (the wired interlock); with the data center's water cut, the plant "
                   f"goes to its fallback after {p[c + 'fallback_enter_min']:g} min and back {p[c + 'fallback_exit_min']:g} min after it returns",
         "basis": "the sequence (23 09 93); IECC C404.6.3",
         "quotes": [("IECC-C", "shall limit operation of the pump from heating cycle startup to not greater than 5 minutes after the end of the cycle")]},
        # -- The building loop (radiant floors).
        {"id": "H-1", "area": "Building loop", "what": "each flat's radiant tubing, before its topping", "who": hvac_,
         "when": "before the topping is poured, and through the pour",
         "passes": "hydrostatic at 1.5 times the loop's design pressure, not less than 100 psi, for 15 min; held at its operating "
                   "pressure while the topping is poured",
         "basis": "IMC 1209.2, 1208.1",
         "quotes": [("IMC12", "Piping to be embedded in concrete shall be pressure tested prior to pouring concrete"),
                    ("IMC12", "at one and one-half times the maximum system design pressure, but not less than 100 psi")]},
        {"id": "H-2", "area": "Building loop", "what": "the loop's mains, risers and tails", "who": hvac_, "when": cover,
         "passes": "hydrostatic at 1.5 times the design pressure, not less than 100 psi, for 15 min", "basis": "IMC 1208.1",
         "quotes": [("IMC12", "The duration of each test shall be not less than 15 minutes")]},
        {"id": "H-3", "area": "Building loop", "what": "the loop's balance and its pump", "who": cx, "when": "at commissioning",
         "passes": f"each flat's flow at its design ({min(flat_gpm):.2f}-{max(flat_gpm):.2f} gpm), read on its heat meter; "
                   f"{L['gpm']:.2f} gpm in all with P-1 at its setting (the design: {L['pump_ft']:.1f} ft at the worst flat, "
                   f"{L['pump_path']}, against its curve's {L['pump_curve_ft']:.1f} ft at its highest fixed speed)",
         "basis": "the design (step 3; 9c)", "quotes": []},
        {"id": "H-4", "area": "Building loop", "what": "the outdoor reset", "who": cx, "when": "at commissioning",
         "passes": f"the supply follows the reset (the design's {L['supply_c']:.1f} C at the heating design temperature, a straight line "
                   f"to the room's) and the loop stops above {p[c + 'wwsd_c']:g} C outdoors",
         "basis": "the sequence (23 09 93)", "quotes": []},
        # -- The mini-splits and their refrigerant.
        {"id": "R-1", "area": "Mini-splits", "what": "each line set", "who": hvac_, "when": cover + ", and before it runs",
         "passes": "pressurized with nitrogen (or helium or argon) for at least 60 min at the outdoor unit's nameplate design pressure "
                   "with no loss; then a 500-micron vacuum that, isolated, stays under 1,500 microns for 10 min",
         "basis": "IMC 1110.2, 1110.5",
         "quotes": [("IMC11", "Refrigerant pipe and joints installed in the field shall be exposed for visual inspection and testing prior to being covered"),
                    ("IMC11", "The system shall be pressurized for a period of not less than 60 minutes"),
                    ("IMC11", "A vacuum of 500 microns shall be achieved"),
                    ("IMC11", "The system pressure shall not rise above 1,500 microns for a period of not less than 10 minutes")]},
        {"id": "R-2", "area": "Mini-splits", "what": "each unit's static pressure", "who": hvac_, "when": "at start-up",
         "passes": f"set by Fujitsu's function setting to its own ducts' need: {esp[0]:.2f}-{esp[-1]:.2f} in. w.c. by flat (the schedule)",
         "basis": "the design (7c)", "quotes": []},
        {"id": "R-3", "area": "Mini-splits", "what": "each unit's water-level switch", "who": hvac_, "when": "at start-up",
         "passes": "water in the drain pan stops the unit (Fujitsu's forced stop, function 46-02)",
         "basis": "IMC 307.2.3; the sequence", "quotes": [("IMC3", "one of the following auxiliary protection methods shall be provided")]},
        # -- Ventilation and the envelope: the energy code's own tests.
        {"id": "V-1", "area": "Ventilation", "what": "each ERV's flows", "who": cx + " (an approved third party where the code official asks)",
         "when": "at commissioning, before occupancy",
         "passes": f"supply and exhaust each at least {cfm:g} cfm (the design; the code's floor {imc:.1f}, the kitchen's and the bath's "
                   f"exhaust {p['systems.code.vent.kitchen_cfm']:g} and {p['systems.code.vent.bath_cfm']:g}), within 10% of each other "
                   "(Phius); a signed report to the code official",
         "basis": "IECC R403.6.3", "quotes": [("IECC-R", "Mechanical ventilation systems shall be tested and verified to provide the minimum ventilation flow rates")]},
        {"id": "V-2", "area": "Ventilation", "what": "duct leakage", "who": "-", "when": "-",
         "passes": "not required: every flat's ducts and units are inside the building's thermal envelope",
         "basis": "IECC R403.3.5, exception 1",
         "quotes": [("IECC-R", "A duct air-leakage test shall not be required where the ducts and air handlers are located entirely within the building thermal envelope")]},
        {"id": "E-1", "area": "Envelope", "what": "each flat's air leakage (blower door)", "who": "an approved third party where the code official asks",
         "when": "with the flat's envelope complete, before occupancy",
         "passes": f"at most {p['pass3.air.ach50']:g} air changes an hour at 50 Pa, by ANSI/RESNET/ICC 380, ASTM E779 or E1827, a signed report "
                   "to the code official. The heat loads assume it; the code's 0.30 cfm/ft2 for attached flats would pass a leakier one",
         "basis": "IECC R402.4.1.2, R402.4.1.3",
         "quotes": [("IECC-R", "3.0 air changes per hour in Climate Zones 3 through 8"),
                    ("IECC-R", "reported at a pressure of 0.2 inch w.g. (50 Pascals)")]},
        # -- Fire protection: NFPA 13R's acceptance.
        {"id": "F-1", "area": "Fire protection", "what": "the underground supply, flushed", "who": fire_, "when": "before it is connected to the sprinkler piping",
         "passes": f"at the system's demand rate ({fh['worst']['q_gpm']:.0f} gpm, the governing design) until the water runs clear",
         "basis": "NFPA 13R 10.2.1", "quotes": [("13R", "The flushing operation shall be continued until the water issuing from the main is clear")]},
        {"id": "F-2", "area": "Fire protection", "what": "the sprinkler piping, hydrostatic", "who": fire_, "when": cover,
         "passes": "NFPA 13's test (the system has more than 20 sprinklers): 200 psi, for NFPA 13's period (not read here)",
         "basis": "NFPA 13R 10.2.2.1; USFA on NFPA 13",
         "quotes": [("13R", "Systems having more than 20 sprinklers or having a fire department connection shall pass a"),
                    ("USFA", "hydrostatic test pressure of 200 psi")]},
        {"id": "F-3", "area": "Fire protection", "what": "the waterflow alarm", "who": fire_ + " and the alarm contractor", "when": "at acceptance",
         "passes": "flow through the inspector's test connection sounds the alarm on the premises within 5 min, and the monitoring "
                   "panel signals the supervising station",
         "basis": "NFPA 13R 10.2.3.1", "quotes": [("13R", "The flow test shall result in an audible alarm on the premises within 5 minutes")]},
        {"id": "F-4", "area": "Fire protection", "what": "the main drain", "who": fire_, "when": "at acceptance",
         "passes": f"static and residual pressures recorded on the contractor's certificate: the design takes the street at "
                   f"{p[pl + 'street_psi']:g} psi static and needs {fh['worst']['need_psi']:.1f} psi at {fh['worst']['q_gpm']:.0f} gpm",
         "basis": "NFPA 13R 10.2.4", "quotes": [("13R", "shall be opened and remain open until the system pressure stabilizes")]},
        {"id": "F-5", "area": "Fire protection", "what": "the contractor's material and test certificate", "who": fire_,
         "when": "before asking for approval",
         "passes": "completed and sent to the authority having jurisdiction", "basis": "NFPA 13R 10.1.2-10.1.3",
         "quotes": [("13R", "The installer shall forward the certificate(s) to the authority having jurisdiction")]},
        # -- The code official's inspections (Pennsylvania's).
        {"id": "G-1", "area": "General", "what": "the work, open for inspection", "who": "the permit holder", "when": "at each stage",
         "passes": "the code official told when it is ready, the work left accessible and exposed", "basis": "34 Pa. Code 403.45(c)",
         "quotes": [("UCC", "The work shall remain accessible and exposed for inspection")]},
        {"id": "G-2", "area": "General", "what": "the final inspection", "who": official, "when": "before occupancy",
         "passes": "a final report finding the general building, electrical, plumbing, accessibility, fire protection, mechanical and "
                   "energy work to the Uniform Construction Code", "basis": "34 Pa. Code 403.45(e)",
         "quotes": [("UCC", "shall conduct a final inspection of the completed construction work")]},
        {"id": "EL-1", "area": "Electrical", "what": "the wiring, rough and final", "who": official + ", with " + elec, "when": rough + "; and final",
         "passes": "to the code (the house panel's BK-1/HP-1 interlock proved in HW-5)", "basis": "34 Pa. Code 403.45(a), (e)(2)",
         "quotes": [("UCC", "shall perform inspections to insure that the construction complies with the approved permit")]},
    ]
    return out


def checks(p: dict, s7: dict, its: list[dict] | None = None) -> list[tuple[str, bool, str]]:
    its = its if its is not None else items(p, s7)
    texts, missing, absent = {}, [], []
    for key, (path, _) in SRC.items():
        texts[key] = _norm(path.read_text(encoding="utf-8", errors="replace")) if path.exists() else None
    for it in its:
        for src, q in it["quotes"]:
            if texts[src] is None:
                absent.append(f"{it['id']} ({src})")
            elif _norm(q) not in texts[src]:
                missing.append(f"{it['id']}: {q[:50]}")
    ids = [it["id"] for it in its]
    whole = all(it[k] for it in its for k in ("what", "who", "when", "passes", "basis"))
    return [
        ("every quotation found word for word in its saved source", not missing and not absent,
         f"{sum(len(it['quotes']) for it in its)} quotations" + (f"; not found: {missing}" if missing else "")
         + (f"; sources not on disk: {absent}" if absent else "")),
        ("every item says what, who, when, what passes and on what it rests; ids unique", whole and len(set(ids)) == len(ids), f"{len(its)} items"),
        ("every item resting on the design alone names it", all(it["quotes"] or "design" in it["basis"] or "sequence" in it["basis"] for it in its), ""),
    ]


def markdown(p: dict, its: list[dict]) -> str:
    lines = ["# 01 45 00: Quality control, the walk-up's tests and inspections", "",
             "Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Each test is the code's own "
             "(quoted below its table) or the design's claim to be proved; Pennsylvania's code official inspects as 34 Pa. Code "
             "403.45 asks.", ""]
    for area in dict.fromkeys(it["area"] for it in its):
        lines += [f"## {area}", "", "| Id | What | Who | When | Passes | Basis |", "|---|---|---|---|---|---|"]
        lines += [f"| {it['id']} | {it['what']} | {it['who']} | {it['when']} | {it['passes']} | {it['basis']} |" for it in its if it["area"] == area]
        lines.append("")
    lines += ["## The codes' words", ""]
    for it in its:
        for src, q in it["quotes"]:
            lines.append(f"- **{it['id']}** ({SRC[src][1]}): \"{q}\"")
    return "\n".join(lines) + "\n"


def run(apt: dict, p: dict) -> dict:
    from . import OUT_DIR, routed

    routes = routed.load(apt, p)
    s7 = routed.summary(apt, p, routes)
    its = items(p, s7)
    md = markdown(p, its)
    path = OUT_DIR / "pass3" / "acceptance.md"
    path.write_text(md, encoding="utf-8")
    return {"items": its, "checks": checks(p, s7, its), "path": path}


def report(r: dict) -> str:
    from .systems import report as fmt

    by = {}
    for it in r["items"]:
        by[it["area"]] = by.get(it["area"], 0) + 1
    return "\n".join([f"Pass 3g step 9c: the tests and inspections (01 45 00, for Addendum 7)", "", fmt(r["checks"]), "",
                      ", ".join(f"{a} {n}" for a, n in by.items()), f"wrote {r['path']}"])
