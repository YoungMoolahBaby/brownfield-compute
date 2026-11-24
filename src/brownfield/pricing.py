"""Pass 3g step 10b (D28): both walk-ups priced, item by item, and the engineering fee.

Every item of 10a's lists (`baseline.items`) is priced by its class (`CLASSES`):
- **A price a unit** (`baseline.price.<class>`): material or equipment at list price from a named
  seller, or installed from a free database (REMDB's regressions, LBNL's PV, the utilities'
  tariffs), each dated and ranged.
- **The labour to install it** (`baseline.hours.<class>`): hours a unit by the trade that does it,
  stated (a placeholder each, with a wide range: no free source of labour units was found), at
  the trade's wage (BLS OEWS May 2025, Indiana County's area) times the employer's burden (BLS
  ECEC, construction).
- **Markups:** the trade's overhead and profit on its own material and labour; then the builder's
  general requirements, overhead, profit and contingency on the whole (PHFA's caps). Prices taken
  installed carry no trade markup; fees and utility charges no builder's either.

The fixtures and appliances, the same in every walk-up and outside NAHB's "except fixtures"
systems, aren't priced. Neither is anything every walk-up shares that isn't in 10a's lists (the
outlets and switches, the luminaires): they cancel in the difference, and the NAHB check says so.
"""

from __future__ import annotations

import json
from collections import defaultdict

from . import OUT_DIR

NL = chr(10)

from .baseline import WALKUPS

# class: (trade or None when priced installed, unit, what it is, markup: "trade" (trade's O&P and
# the builder's), "builder" (the builder's only: priced installed), "none" (a fee or a charge))
CLASSES = {
    # Plumbing pipe and fittings (material per ft or each; the hours include hangers and testing).
    **{f"pex_a_{s}": ("plumber", "ft", f"PEX-a {s} in. (Uponor AquaPEX)", "trade") for s in ("0.5", "0.75", "1", "1.25", "1.5")},
    "pex_a_fitting_small": ("plumber", "each", "PEX-a fitting to 1 in., with its rings (ProPEX EP)", "trade"),
    "pex_a_fitting_large": ("plumber", "each", "PEX-a fitting 1-1/4 to 2 in., with its rings", "trade"),
    "pex_preins_small": ("plumber", "ft", "pre-insulated PEX to 1 in., under the slab", "trade"),
    "pex_preins_large": ("plumber", "ft", "pre-insulated PEX 1-1/4 to 2 in., under the slab", "trade"),
    **{f"ci_nohub_{s}": ("plumber", "ft", f"cast iron no-hub {s} in., its couplings", "trade") for s in ("1.5", "2", "3", "4")},
    "ci_fitting_small": ("plumber", "each", "cast iron no-hub fitting to 2 in., two couplings", "trade"),
    "ci_fitting_large": ("plumber", "each", "cast iron no-hub fitting 3 to 4 in., two couplings", "trade"),
    **{f"pvc_dwv_{s}": ("plumber", "ft", f"PVC DWV {s} in.", "trade") for s in ("1.5", "2", "3", "4")},
    "pvc_fitting_small": ("plumber", "each", "PVC DWV fitting to 2 in.", "trade"),
    "pvc_fitting_large": ("plumber", "each", "PVC DWV fitting 3 to 4 in.", "trade"),
    "pvc_sch40_0.75": ("hvac", "ft", "PVC Schedule 40 3/4 in. (condensate)", "trade"),
    "pvc_fitting_condensate": ("hvac", "each", "PVC 3/4 in. fitting (condensate)", "trade"),
    "pvc_sch40_2": ("plumber", "ft", "PVC Schedule 40 2 in. (a gas appliance's vent and combustion air)", "trade"),
    "gas_csst_0.75": ("plumber", "ft", "gas pipe, CSST 3/4 in.", "trade"),
    # Insulation (material per ft).
    "insul_1in_small": ("insulator", "ft", "pipe insulation 1 in. thick, to 1 in. pipe", "trade"),
    "insul_15in_large": ("insulator", "ft", "pipe insulation 1-1/2 in. thick, 1-1/2 in. pipe", "trade"),
    "insul_05in": ("insulator", "ft", "pipe insulation 1/2 in. thick (R-3)", "trade"),
    "duct_insul_15": ("insulator", "ft", "duct insulation 1-1/2 in., 5 in. round duct", "trade"),
    # Hot water and the plant.
    "caleffi_116": ("plumber", "each", "thermostatic balancing valve 1/2 in. (Caleffi 116)", "trade"),
    "leonard_tm186": ("plumber", "each", "master mixing valve (Leonard TM-186)", "trade"),
    "grundfos_alpha2": ("plumber", "each", "circulator (Grundfos ALPHA2 15-55)", "trade"),
    "lochinvar_hp150g": ("plumber", "each", "150 gal storage tank (Lochinvar HP150G)", "trade"),
    "bradford_re340s6": ("plumber", "each", "40 gal electric swing tank (Bradford White RE340S6)", "trade"),
    "aosmith_dre52": ("plumber", "each", "commercial electric water heater (A. O. Smith DRE-52-12)", "trade"),
    "climatemaster_sw036": ("plumber", "each", "water-to-water heat pump (ClimateMaster SW036)", "trade"),
    "bphe_50kw": ("plumber", "each", "brazed plate heat exchanger, ~50 kW", "trade"),
    "exp_tank_hydronic": ("plumber", "each", "expansion tank, hydronic", "trade"),
    "exp_tank_dhw_small": ("plumber", "each", "thermal expansion tank, a flat's heater (2 gal)", "trade"),
    "exp_tank_dhw_large": ("plumber", "each", "thermal expansion tank, a plant's", "trade"),
    "plant_controls": ("electrician", "lot", "the plant's controller, sensors, flow switch and two modulating valves (to select)", "trade"),
    "aosmith_bth120": ("plumber", "each", "central gas water heater (A. O. Smith BTH-120)", "trade"),
    "central_vent": ("plumber", "each", "the central heater's vent and combustion air", "trade"),
    "kamstrup_403": ("plumber", "each", "heat meter (Kamstrup MULTICAL 403)", "trade"),
    "badger_eseries_34": ("plumber", "each", "water submeter 3/4 in. (Badger E-Series)", "trade"),
    "sleeve_support": ("plumber", "each", "a closed-cell elastomeric sleeve at a water pipe's support (Armaflex, cut to length)", "trade"),
    **{f"isolator_{s}": ("plumber", "each", f"an acoustic through-stud isolator, {s} in. pipe (Holdrite SILENCER)", "trade") for s in ("0.5", "0.75", "1")},
    # Each flat's own water heater (its installed cost checked against REMDB's, `known_cases`).
    "aosmith_ent50": ("plumber", "each", "electric water heater 50 gal (A. O. Smith ENT-50)", "trade"),
    "rheem_prog40_pdv": ("plumber", "each", "gas water heater 40 gal, power direct vent (Rheem PROG40)", "trade"),
    # The radiant floors.
    "radiant_pex_0.5": ("plumber", "ft", "radiant PEX 1/2 in., oxygen barrier", "trade"),
    "radiant_manifold": ("plumber", "each", "radiant manifold and its cabinet", "trade"),
    "gypcrete_15": (None, "ft2", "gypsum concrete topping 1-1/2 in., installed", "builder"),
    "xps_r5": ("laborer", "ft2", "XPS 1 in. (R-5) under the slab", "trade"),
    # Water service, fire service, sprinklers.
    "watts_lfn45b_2": ("plumber", "each", "pressure-reducing valve 2 in. (Watts LFN45B)", "trade"),
    "domestic_service": ("plumber", "each", "the domestic service's double check valve assembly 2 in. (Watts LF007)", "trade"),
    "fire_service": ("sprinkler", "each", "the fire service's double check valve assembly 4 in. with its OS&Y valves", "trade"),
    "combined_service": ("sprinkler", "each", "the shared service's backflow assembly 4 in. with its OS&Y valves", "trade"),
    "supervision": ("electrician", "each", "the monitoring panel (Potter PFC-6006) and two tamper switches", "trade"),
    "alarm": ("sprinkler", "each", "waterflow switch and horn-strobe", "trade"),
    "fdc": ("sprinkler", "each", "fire department connection", "trade"),
    "tap_first": (None, "each", "the water utility's first connection to a building", "none"),
    "tap_fire_second": (None, "each", "the water utility's second connection, a separate fire line, at its actual cost", "none"),
    "ug_2in": (None, "ft", "underground water service 2 in., trenched, installed", "builder"),
    "ug_4in": (None, "ft", "underground water service 4 in., trenched, installed", "builder"),
    **{f"cpvc_{s}": ("sprinkler", "ft", f"CPVC sprinkler pipe {s} in. (BlazeMaster)", "trade") for s in ("1.25", "1.5", "2.5")},
    "cpvc_fitting": ("sprinkler", "each", "CPVC sprinkler fitting", "trade"),
    "head_ty2236": ("sprinkler", "each", "residential pendent sprinkler (Tyco TY2236)", "trade"),
    "head_qr_k56": ("sprinkler", "each", "quick-response K5.6 sprinkler", "trade"),
    # HVAC and ventilation.
    # Equipment at list price and its installation, every walk-up's alike (each checked against
    # REMDB's installed cost for its measure, `known_cases`).
    "minisplit_fujitsu_12_ducted": ("hvac", "each", "ducted mini-split 12k, indoor and outdoor (Fujitsu ARUH12KUAS)", "trade"),
    "erv_broan_blp120": ("hvac", "each", "ERV (Broan EDGE BLP120)", "trade"),
    "furnace_goodman_40k": ("hvac", "each", "gas furnace 40 kBtu/h (Goodman GR9S960403AN)", "trade"),
    "ac_goodman_15ton": ("hvac", "each", "split air conditioner 1.5 ton with its coil (Goodman GLXS4B)", "trade"),
    "preheater_1kw": ("hvac", "each", "duct preheater 1 kW (Ouellet)", "trade"),
    **{f"duct_round_{s}": ("sheetmetal", "ft", f"round galvanized duct {s} in.", "trade") for s in ("4", "5", "6", "7", "8")},
    "duct_elbow_small": ("sheetmetal", "each", "round duct elbow 4-6 in.", "trade"),
    "duct_elbow_large": ("sheetmetal", "each", "round duct elbow 7-8 in.", "trade"),
    "duct_boot": ("sheetmetal", "each", "register boot", "trade"),
    "duct_takeoff": ("sheetmetal", "each", "duct take-off", "trade"),
    "register_supply": ("sheetmetal", "each", "supply register", "trade"),
    "grille_exhaust": ("sheetmetal", "each", "exhaust grille", "trade"),
    "wallcap_5_hood": ("sheetmetal", "each", "wall hood 5 in. (the ERV's)", "trade"),
    "wallcap_usual": ("sheetmetal", "each", "wall cap, a bath fan's (4 in.) or a hood's (6 in.)", "trade"),
    "lineset_14_38": ("hvac", "ft", "line set 1/4 x 3/8 in., insulated", "trade"),
    "level_switch": ("hvac", "each", "condensate safety switch", "trade"),
    "bath_fan_panasonic": ("electrician", "each", "bath fan, continuous (Panasonic FV-0511VQ1)", "trade"),
    # Electrical.
    **{f"nmb_{s}": ("electrician", "ft", f"NM-B {s} AWG", "trade") for s in ("14", "12", "10", "8")},
    "feeder_1": ("electrician", "ft", "feeder: 1 in. PVC conduit, three 3 AWG and a 8 AWG ground", "trade"),
    "feeder_1.25": ("electrician", "ft", "feeder: 1-1/4 in. PVC conduit, three 2 AWG and a 8 AWG ground", "trade"),
    # 10h: a feeder a designed walk-up upsizes for drop at its flats' load (none in the published items)
    "feeder_1.25_1awg": ("electrician", "ft", "feeder: 1-1/4 in. PVC conduit, three 1 AWG and a 8 AWG ground", "trade"),
    "conduit_elbow_1": ("electrician", "each", "PVC conduit elbow", "trade"),
    "qo130l125pg": ("electrician", "each", "load centre (Square D QO130L125PG)", "trade"),
    "service_600": ("electrician", "each", "the meter stack's 600 A main (EZM3600CB) and two sets of 250 kcmil", "trade"),
    "service_400": ("electrician", "each", "the meter stack's 400 A main (EZM3400CB) and one set of 600 kcmil", "trade"),
    "fixture_roughin": ("plumber", "each", "a fixture's rough-in and setting parts", "trade"),
    "device": ("electrician", "each", "an outlet or switch with its box and plate", "trade"),
    "smoke_alarm": ("electrician", "each", "a hardwired smoke alarm with its battery", "trade"),
    "ezmh314125": ("electrician", "each", "a meter stack socket module, four positions (Square D EZMH314125)", "trade"),
    "plant_circuits": ("electrician", "lot", "the house panel's circuits to the engineered plant", "trade"),
    "central_circuits": ("electrician", "lot", "the house panel's circuits to the central heater and its pump", "trade"),
    "pv_kw": (None, "kW AC", "rooftop PV, installed", "builder"),
    # Gas utility, the envelope and the tests.
    "gas_service_ft": (None, "ft", "a gas service line from the main, trenched, the owner's", "builder"),
    "gas_meter": (None, "each", "a gas meter set (the first on its line, the utility's)", "none"),
    "airseal_ft2": (None, "ft2", "air sealing to Phius's limit beyond the code's, installed, a ft2 of floor", "builder"),
    "bdt_whole": (None, "ft2", "whole-building blower door test, a ft2 of floor", "builder"),
    "bdt_unit": (None, "each", "a flat's blower door test", "builder"),
    **{f"test_{t}": (t, "each", f"a test or inspection by the {t}, its hours", "trade")
       for t in ("plumber", "hvac", "sprinkler", "electrician", "laborer")},
    "test_tab": (None, "each", "balancing and commissioning, its hours at a TAB firm's rate", "builder"),
    # Priced with another item: the plant's valves and sensors in its controls' lot; the mini-split's
    # outdoor unit in the system's price (the pair, sold together).
    "in_plant_controls": (None, "each", "in the plant's controls' lot", "none"),
    "in_minisplit": (None, "each", "in the mini-split system's price", "none"),
}

# Who does each test (by its id, else its prefix): the trades their own; a TAB firm the balancing and
# the design's claims proved at commissioning.
TEST_BY = {"P": "test_plumber", "HW": "test_plumber", "H": "test_plumber", "R": "test_hvac", "F": "test_sprinkler", "G": "test_laborer",
           "EL": "test_electrician", "HW-3": "test_tab", "HW-4": "test_tab", "HW-5": "test_tab", "H-3": "test_tab", "H-4": "test_tab",
           "R-2": "test_tab", "V-1": "test_tab"}

SIZE = {"1/2": "0.5", "3/4": "0.75", "1": "1", "1-1/4": "1.25", "1-1/2": "1.5", "2": "2", "2-1/2": "2.5", "3": "3", "4": "4",
        "0.5": "0.5", "0.75": "0.75", "5": "5", "6": "6", "7": "7", "8": "8"}


def _nps(size: str) -> float:
    """A size in inches, as `SIZE` writes it ("1.5") or as the model does ("1-1/2")."""
    try:
        return float(size)
    except ValueError:
        return float(SIZE.get(size, "nan"))


def classes_of(it: dict) -> list[tuple[str, float]]:
    """An item's price classes and how many of each a unit of it takes; [] for what isn't priced
    (the fixtures and appliances, every walk-up's alike)."""
    w, k = it["what"], it["id"]
    if k.startswith("run |"):
        size = SIZE.get(it.get("size", ""), it.get("size", ""))
        if "pre-insulated" in w:
            return [("pex_preins_small" if _nps(size) <= 1 else "pex_preins_large", 1.0)]
        if w.startswith("PEX-a"):
            return [(f"pex_a_{size}", 1.0)]
        if w.startswith("cast iron"):
            return [(f"ci_nohub_{size}", 1.0)]
        if w.startswith("PVC DWV"):
            return [(f"pvc_dwv_{size}", 1.0)]
        if w.startswith("CPVC"):
            return [(f"cpvc_{size}", 1.0)]
        if w.startswith("round galvanized"):
            return [(f"duct_round_{'8' if size == 'plenum' else size}", 1.0)]
        if w.startswith("soft copper"):
            return [("lineset_14_38", 1.0)]
        if w.startswith("PVC Schedule 40"):
            return [("pvc_sch40_0.75", 1.0)]
        if w.startswith("NM-B"):
            return [(f"nmb_{size.split()[0]}", 1.0)]
        if w.startswith("rigid PVC conduit"):
            return [(f"feeder_{size}", 1.0)]
    if k.startswith("fit |"):
        size = SIZE.get(k.split(" | ")[-1], "")
        if w.startswith(("PEX-a", "PEX")):
            return [("pex_a_fitting_small" if _nps(size) <= 1 else "pex_a_fitting_large", 1.0)]
        if w.startswith("cast iron"):
            return [("ci_fitting_small" if _nps(size) <= 2 else "ci_fitting_large", 1.0)]
        if w.startswith("PVC DWV"):
            return [("pvc_fitting_small" if _nps(size) <= 2 else "pvc_fitting_large", 1.0)]
        if w.startswith("CPVC"):
            return [("cpvc_fitting", 1.0)]
        if w.startswith("PVC Schedule 40"):
            return [("pvc_fitting_condensate", 1.0)]
        if w.startswith("rigid PVC conduit"):
            return [("conduit_elbow_1", 1.0)]
        if w.startswith("round galvanized"):
            if "boot" in w:
                return [("duct_boot", 1.0)]
            if "take-off" in w:
                return [("duct_takeoff", 1.0)]
            return [("duct_elbow_small" if _nps(size) <= 6 else "duct_elbow_large", 1.0)]
    el = {"ERV": [("erv_broan_blp120", 1.0)], "mini-split indoor unit": [("minisplit_fujitsu_12_ducted", 1.0)], "mini-split outdoor unit": [("in_minisplit", 1.0)],
          "supply register": [("register_supply", 1.0)], "exhaust grille": [("grille_exhaust", 1.0)],
          "wall cap (exhaust)": [("wallcap_5_hood", 1.0)], "wall cap (intake)": [("wallcap_5_hood", 1.0)],
          "UL 508 water-level switch": [("level_switch", 1.0)], "load centre": [("qo130l125pg", 1.0)],
          "thermostatic balancing valve": [("caleffi_116", 1.0)], "radiant manifold": [("radiant_manifold", 1.0)],
          "hot-water storage tank": [("lochinvar_hp150g", 1.0)], "swing tank": [("bradford_re340s6", 1.0)],
          "backup water heater": [("aosmith_dre52", 1.0)], "water-to-water heat pump": [("climatemaster_sw036", 1.0)],
          "sprinkler, Tyco TY2236": [("head_ty2236", 1.0)], "sprinkler, quick-response": [("head_qr_k56", 1.0)]}
    if k.startswith("el |"):
        for prefix, cl in el.items():
            if w.startswith(prefix):
                return cl
        return []  # the fixtures and appliances (washer, dryer, dishwasher, WC, lavatory, tub, sink)
    design = {
        "radiant | tubing": [("radiant_pex_0.5", 1.0)], "radiant | topping": [("gypcrete_15", 1.0)],
        "radiant | slab insulation": [("xps_r5", 1.0)], "radiant | heat meter": [("kamstrup_403", 1.0)],
        "plant | HX-1": [("bphe_50kw", 1.0)], "plant | HX-2": [("bphe_50kw", 1.0)], "plant | P-1": [("grundfos_alpha2", 1.0)],
        "plant | P-2": [("grundfos_alpha2", 1.0)], "plant | V-1": [("in_plant_controls", 1.0)], "plant | V-2": [("in_plant_controls", 1.0)],
        "plant | TS-1/2/5, FS-1": [("in_plant_controls", 1.0)],
        "plant | PC-1": [("plant_controls", 1.0)],  # the controller, the sensors, the flow switch and the two valves, as one lot
        "plant | ET": [("exp_tank_hydronic", 2.0)], "plant | P-3": [("grundfos_alpha2", 1.0)], "plant | MV-1": [("leonard_tm186", 1.0)],
        "plant | ET-DHW": [("exp_tank_dhw_large", 1.0)], "water | submeters": [("badger_eseries_34", 1.0)],
        "water | prv": [("watts_lfn45b_2", 1.0)], "water | sleeves": [("sleeve_support", 1.0)], "water | domestic service": [("domestic_service", 1.0), ("tap_first", 1.0)],
        "water | domestic line": [("ug_2in", 1.0)], "fire | underground": [("ug_4in", 1.0)],
        "fire | service": [("fire_service", 1.0), ("tap_fire_second", 1.0)], "fire | supervision": [("supervision", 1.0)],
        "fire | alarm": [("alarm", 1.0)], "fire | fdc": [("fdc", 1.0)], "fire | combined service": [("combined_service", 1.0), ("tap_first", 1.0)],
        "ventilation | preheater": [("preheater_1kw", 1.0)], "electrical | pv": [("pv_kw", 1.0)],
        "envelope | air sealing": [("airseal_ft2", 1.0)], "envelope | whole-building test": [("bdt_whole", 1.0)],
        "envelope | flat tests": [("bdt_unit", 1.0)], "electrical | plant circuits": [("plant_circuits", 1.0)],
        "electrical | central circuits": [("central_circuits", 1.0)],
        "shared | fixture rough-in": [("fixture_roughin", 1.0)], "shared | devices": [("device", 1.0)],
        "shared | smoke alarms": [("smoke_alarm", 1.0)], "shared | meter sockets": [("ezmh314125", 1.0)],
        "shared | house panel": [("qo130l125pg", 1.0)],
        "own | trunk": [("pex_a_0.75", 1.0)], "own | drops": [("pex_a_0.5", 1.0)], "own | fittings": [("pex_a_fitting_small", 1.0)],
        "own | trunk insulation": [("insul_05in", 1.0)], "own | heater electric": [("aosmith_ent50", 1.0)],
        "own | heater gas": [("rheem_prog40_pdv", 1.0)], "own | expansion": [("exp_tank_dhw_small", 1.0)],
        "own | heater circuit": [("nmb_10", 1.0)], "gas | furnace": [("furnace_goodman_40k", 1.0)], "gas | condenser": [("ac_goodman_15ton", 1.0)],
        "gas | furnace circuit": [("nmb_14", 1.0)], "gas | vents": [("pvc_sch40_2", 1.0)], "gas | meters": [("gas_meter", 1.0)],
        "gas | meter central": [("gas_meter", 1.0)], "gas | service": [("gas_service_ft", 1.0)], "gas | lines": [("gas_csst_0.75", 1.0)],
        "gas | branches": [("gas_csst_0.75", 1.0)], "central | heater": [("aosmith_bth120", 1.0)], "central | vent": [("central_vent", 1.0)],
        "vent | bath fan": [("bath_fan_panasonic", 1.0)], "vent | bath duct": [("duct_round_4", 1.0)],
        "vent | hood duct": [("duct_round_6", 1.0)], "vent | caps": [("wallcap_usual", 1.0)],
    }
    if k in design:
        return design[k]
    if k.startswith("water | isolators |"):
        return [(f"isolator_{SIZE[k.split(' | ')[2]]}", 1.0)]
    if k.startswith("insulation |"):
        if it["system"] == "ventilation":
            return [("duct_insul_15", 1.0)]
        t = w.split()[1]
        return [({"1": "insul_1in_small", "1.5": "insul_15in_large", "0.5": "insul_05in"}[t], 1.0)]
    if k.startswith("test |"):
        return [(TEST_BY.get(k.split(" | ")[1]) or TEST_BY[k.split(" | ")[1].split("-")[0]], 1.0)]
    if k.startswith("electrical | service |"):
        return [(f"service_{it['main_a']}", 1.0)]
    raise ValueError(f"no price class for {k!r}: {w}")


def book_classes() -> frozenset[str]:
    """The prices taken from a distributor's book or a maker's list (their params' note "book"):
    contractors buy below them, by `baseline.markup.book_to_net`."""
    from .params import load_params

    return frozenset(k.removeprefix("baseline.price.") for k, v in load_params().items()
                     if k.startswith("baseline.price.") and getattr(v, "note", None) == "book")


BOOK: frozenset[str] | None = None


def unit_cost(cls: str, p: dict, test: str | None = None) -> tuple[float, float]:
    """A class's price a unit (material or installed) and its labour hours a unit, from the params; a
    book or list price at what a contractor pays (`book_to_net`)."""
    global BOOK
    if BOOK is None:
        BOOK = book_classes()
    hr = "baseline.hours."

    class _P(dict):  # the prices, each book or list one taken to net
        def __getitem__(self, key):
            v = p[key]
            name = key.removeprefix("baseline.price.")
            return v * p["baseline.markup.book_to_net"] if key.startswith("baseline.price.") and name in BOOK else v

    pp = _P()
    pr = "baseline.price."
    if cls.startswith("test_"):  # each test's own hours, `baseline.hours.test_<id>`; a TAB firm's at its rate
        h = p[hr + f"test_{test}"]
        return (h * p["baseline.labour.tab_billing_usd_h"], 0.0) if cls == "test_tab" else (0.0, h)
    if cls.startswith("in_"):
        return 0.0, 0.0
    if cls == "feeder_1":
        mat = pp[pr + "pvc_conduit_1"] + 3 * pp[pr + "thhn_3"] + pp[pr + "thhn_8"]
    elif cls == "feeder_1.25":
        mat = pp[pr + "pvc_conduit_1.25"] + 3 * pp[pr + "thhn_2"] + pp[pr + "thhn_8"]
    elif cls == "feeder_1.25_1awg":  # 1 AWG at its price over 2 AWG's, the same seller's (`thhn_1_over_2`)
        mat = pp[pr + "pvc_conduit_1.25"] + 3 * pp[pr + "thhn_2"] * p[pr + "thhn_1_over_2"] + pp[pr + "thhn_8"]
    elif cls == "service_600":
        mat = pp[pr + "ezm3600cb"] + 2 * 4 * pp[pr + "service_250kcmil"] * p["baseline.usual.service_ft"]
    elif cls == "service_400":
        mat = pp[pr + "ezm3400cb"] + 4 * pp[pr + "service_600kcmil"] * p["baseline.usual.service_ft"]
    elif cls == "pv_kw":  # LBNL's installed price a W DC, a kW AC of it at the design's DC/AC ratio
        mat = pp[pr + "pv_commercial_per_w"] * 1000.0 * p["systems.pv.dc_ac"]
    elif cls == "radiant_manifold":
        mat = pp[pr + "radiant_manifold"] + pp[pr + "radiant_cabinet"]
    elif cls == "sleeve_support":  # a sleeve cut from a 6 ft length
        mat = pp[pr + "armaflex_6ft"] / 6.0 * p["baseline.sleeves.sleeve_ft"]
    elif cls == "domestic_service":
        mat = pp[pr + "watts_lf007_2"]
    elif cls in ("fire_service", "combined_service"):
        mat = pp[pr + "dcva_4_osy"]
    elif cls == "supervision":
        mat = pp[pr + "facp_potter"] + 2 * pp[pr + "ostamper"]
    elif cls == "alarm":
        mat = pp[pr + "flow_switch"] + pp[pr + "horn_strobe"]
    elif cls == "wallcap_usual":
        mat = (pp[pr + "wallcap_4"] + pp[pr + "wallcap_6"]) / 2
    elif cls.startswith("ci_nohub_"):
        size = cls.split("_")[-1]
        mat = pp[pr + cls] + pp[pr + ("ci_coupling_small" if float(size) <= 2 else "ci_coupling_large")] / 10.0  # a coupling a 10 ft length
    elif cls in ("ci_fitting_small", "ci_fitting_large"):
        mat = pp[pr + cls] + 2 * pp[pr + cls.replace("fitting", "coupling")]
    else:
        mat = pp[pr + cls]
    trade = CLASSES[cls][0]
    if cls == "feeder_1.25_1awg":  # pulled in the same conduit as 2 AWG: its hours
        return mat, p[hr + "feeder_1.25"]
    return mat, (p[hr + cls] if trade else 0.0)


def wage(trade: str, p: dict) -> float:
    """A trade's loaded hourly cost: its wage times the burden."""
    return p[f"baseline.labour.{trade}_usd_h"] * p["baseline.labour.burden"]


GROUPS = {  # how the items' systems add up, as NAHB's categories read ("except fixtures")
    "cold": "plumbing", "hot": "plumbing", "drain": "plumbing", "vent": "plumbing", "gas": "plumbing",
    "loop": "heating", "air": "hvac", "refrigerant": "hvac", "condensate": "hvac", "ventilation": "hvac",
    "power": "electrical", "sprinkler": "fire", "envelope": "envelope", "tests": "tests",
}


def price(items: list[dict], p: dict) -> dict:
    """Each walk-up's cost: each item's material, labour and markups by its classes; the totals by
    group, before and after the builder's markups. Returns the lines and the totals."""
    o = "baseline.markup."
    trade_op = p[o + "trade_op"]
    builder = (1 + p[o + "general_requirements"] + p[o + "overhead"] + p[o + "profit"]) * (1 + p[o + "contingency"])
    lines, totals = [], {w: defaultdict(float) for w in WALKUPS}
    unpriced = []
    for it in items:
        cl = classes_of(it)
        if not cl:
            unpriced.append(it["id"])
            continue
        group = GROUPS.get(it["system"], "plumbing" if it["system"] in ("", None) else it["system"])
        for cls, per in cl:
            test = it["id"].split(" | ")[1] if cls.startswith("test_") else None
            mat, h = unit_cost(cls, p, test)
            trade, _, _, markup = CLASSES[cls]
            lab = h * wage(trade, p) if trade else 0.0
            base = mat + lab
            hard = base * (1 + trade_op) if markup == "trade" else base
            full = hard * builder if markup in ("trade", "builder") else hard
            row = {"id": it["id"], "what": it["what"], "class": cls, "per": per, "unit_usd": full, "group": group,
                   "qty": {w: it["qty"][w] * per for w in WALKUPS}}
            row["usd"] = {w: row["qty"][w] * full for w in WALKUPS}
            lines.append(row)
            for w in WALKUPS:
                totals[w][group] += row["usd"][w]
                totals[w]["material_base"] += row["qty"][w] * mat  # before any markup
                totals[w]["labour_base"] += row["qty"][w] * lab
                totals[w]["labour_h"] += row["qty"][w] * h
    out = {w: dict(t) for w, t in totals.items()}
    for w in WALKUPS:
        out[w]["total"] = sum(v for k, v in out[w].items() if k in set(GROUPS.values()))
    return {"lines": lines, "totals": out, "unpriced": unpriced, "builder": builder, "trade_op": trade_op}


def installed(cls: str, p: dict) -> float:
    """One unit of a class, installed and marked up as `price` marks an item's (USD)."""
    o = "baseline.markup."
    builder = (1 + p[o + "general_requirements"] + p[o + "overhead"] + p[o + "profit"]) * (1 + p[o + "contingency"])
    mat, h = unit_cost(cls, p)
    trade, _, _, markup = CLASSES[cls]
    base = mat + (h * wage(trade, p) if trade else 0.0)
    hard = base * (1 + p[o + "trade_op"]) if markup == "trade" else base
    return hard * builder if markup in ("trade", "builder") else hard


# ---- the fee ----

def construction_usd(p: dict, flats: int = 12) -> float:
    """The building's construction cost for the fee's percentage: HUD's 2024 housing construction cost
    for a 2-bedroom walk-up flat in the Johnstown market, to 2026, times the flats."""
    return p["baseline.fee.hud_hcc_flat"] * p["baseline.fee.hcc_to_2026"] * flats


def fee(p: dict, flats: int = 12) -> dict:
    """The engineered design's fee beyond the usual walk-up's (the decision in PLAN D28 step 10: a
    difference in depth). PHFA's cap for a walk-up's architect already buys mechanical and electrical
    drawings; the extra runs from none to the whole MEP share of a public-works fee (Washington's
    Schedule B), its central value a stated share of that (`baseline.fee.extra_of_mep`)."""
    f = "baseline.fee."
    c = construction_usd(p, flats)
    mep = p[f + "ofm_pct"] * p[f + "mep_share"] * c
    extra = p[f + "extra_of_mep"] * mep
    return {"construction_usd": c, "phfa_fee_usd": p[f + "phfa_pct"] * c, "ofm_fee_usd": p[f + "ofm_pct"] * c, "mep_fee_usd": mep,
            "extra_usd": extra, "extra_flat_usd": extra / flats}


# ---- the heat network's share ----

def network_share(p: dict, s7: dict, flats: int, floor_m2: float) -> dict:
    """The engineered walk-up's share of the heat network that brings the data center's water, as
    pass 3 §4 prices it for an apartment (`block.per_home`: the street network by its frontage, the
    main from the campus shared by the block's homes, the exchanger at the data center by the flat's
    design heat): at §4's base case (200 homes on a 1.5 km main) and its dense one (1,000 on 0.5 km).
    Not a building system: shown beside the systems, never in them."""
    from .block import per_home

    design_kw = s7["loop"]["w"] / 1e3 / flats
    out = {}
    dense = ("dense", p["baseline.network.dense_homes"], p["baseline.network.dense_main_km"])
    for case, homes, km in (("base", p["pass3.block.homes"], p["pass3.block.main_km"]), dense):
        q = dict(p, **{"pass3.block.homes": homes, "pass3.block.main_km": km})
        h = per_home(q, 0.0, 0.0, design_kw, floor_m2, p["pass3.density.apartment_m"])
        out[case] = {"homes": homes, "main_km": km, "street": h["street"], "main": h["main"], "plant": h["plant"], "flat": h["network"]}
    return out


# ---- the known cases ----

def known_cases(r: dict, p: dict, floor_ft2: float, flats: int = 12) -> dict:
    """The usual walk-up's systems against what the free sources give whole:
    - NAHB's single-family shares (plumbing, electrical, HVAC, each "except fixtures") of HUD's
      construction cost for a Johnstown walk-up flat, to 2026: the usual all-electric walk-up's per
      flat within `baseline.check.nahb_factor` (single-family shares on a walk-up, and the shared
      rough-in and devices allowances in our lists: a wide band, said so);
    - the sprinklers alone (heads, pipe, fittings, their labour and markups) per ft2 of the flats at
      least NFSA's $1.35 for an NFPA 13D house (a floor: 13R does more);
    - REMDB's heat-pump water heater over its electric one against ENERGY STAR MFNC's incremental
      cost (partly REMDB's own, so a consistency check, not an independent one);
    - each piece of equipment's installed cost, built up, against REMDB's for its measure."""
    c = "baseline.check."
    t = r["totals"]["electric"]
    hcc = p["baseline.fee.hud_hcc_flat"] * p["baseline.fee.hcc_to_2026"]
    ours = {"plumbing": t.get("plumbing", 0.0) / flats, "electrical": t.get("electrical", 0.0) / flats,
            "hvac": (t.get("hvac", 0.0) + t.get("heating", 0.0)) / flats}
    nahb = {k: p[c + f"nahb_{k}_share"] * hcc for k in ours}
    sprinklers = sum(x["usd"]["electric"] for x in r["lines"]
                     if x["class"].startswith(("cpvc", "head_")))
    rd = "baseline.remdb."
    hp_extra = p[rd + "remdb_hpwh_50"] - p[rd + "remdb_ewh_50"]
    # Each piece of equipment built up (list price, its hours at the trade's loaded wage, the trade's
    # markup: what an installer charges, as REMDB's installed costs are) against REMDB's, to 2026.
    equipment = {}
    for cls, measure in REMDB_PAIRS.items():
        mat, h = unit_cost(cls, p)
        built = (mat + h * wage(CLASSES[cls][0], p)) * (1 + p["baseline.markup.trade_op"])
        theirs = p[rd + measure] * p[rd + "to_2026"]
        equipment[cls] = {"ours": built, "remdb": theirs, "ratio": built / theirs}
    return {"nahb": {k: {"ours": ours[k], "nahb": nahb[k], "ratio": ours[k] / nahb[k]} for k in ours}, "nahb_factor": p[c + "nahb_factor"],
            "sprinklers_ft2": sprinklers / floor_ft2, "nfsa_13d_ft2": p[c + "nfsa_13d_ft2"],
            "hpwh_extra": hp_extra, "energy_star_hpwh_extra": p[rd + "energy_star_hpwh_extra"],
            "equipment": equipment, "remdb_factor": p[rd + "factor"]}


REMDB_PAIRS = {"minisplit_fujitsu_12_ducted": "remdb_ducted_minisplit_1ton", "erv_broan_blp120": "remdb_erv_120cfm",
               "aosmith_ent50": "remdb_ewh_50", "rheem_prog40_pdv": "remdb_gwh_40", "furnace_goodman_40k": "remdb_furnace_40k",
               "ac_goodman_15ton": "remdb_ac_15ton"}


# ---- 10b: the run ----

UNPRICED = ("washer", "dryer", "dishwasher", "water closet", "lavatory", "bathtub", "kitchen sink")


def checks(pr: dict, kc: dict, items: list[dict]) -> list[tuple[str, bool, str]]:
    by = {it["id"]: it for it in items}
    odd = [i for i in pr["unpriced"] if not by[i]["what"].startswith(UNPRICED)]
    f, rf = kc["nahb_factor"], kc["remdb_factor"]
    eq = kc["equipment"]
    return [
        ("every item priced but the fixtures and appliances (every walk-up's alike)", not odd,
         f"{len(pr['unpriced'])} not priced" + (f"; unexpected: {odd}" if odd else "")),
        ("the usual all-electric walk-up's plumbing, electrical and HVAC a flat within NAHB's single-family shares of HUD's Johnstown "
         f"cost (a factor of {f:g} either way)", all(1 / f <= v["ratio"] <= f for v in kc["nahb"].values()),
         "; ".join(f"{k} ${v['ours']:,.0f} against ${v['nahb']:,.0f} ({v['ratio']:.2f})" for k, v in kc["nahb"].items())),
        ("the sprinklers alone at least NFSA's cost a ft2 for a 13D house (a floor)", kc["sprinklers_ft2"] >= kc["nfsa_13d_ft2"],
         f"${kc['sprinklers_ft2']:.2f} a ft2 of the flats against ${kc['nfsa_13d_ft2']:.2f}"),
        ("REMDB's heat-pump water heater over its electric one, against ENERGY STAR MFNC's increment",
         1 / rf <= kc["hpwh_extra"] / kc["energy_star_hpwh_extra"] <= rf,
         f"${kc['hpwh_extra']:,.0f} against ${kc['energy_star_hpwh_extra']:,.0f}"),
        (f"each piece of equipment built up within a factor of {rf:g} of REMDB's installed cost (new construction, to 2026)",
         all(1 / rf <= v["ratio"] <= rf for v in eq.values()),
         "; ".join(f"{k} ${v['ours']:,.0f} against ${v['remdb']:,.0f} ({v['ratio']:.2f})" for k, v in eq.items())),
    ]


def run(r: dict, apt: dict, p: dict) -> dict:
    """10b on 10a's run `r` (`baseline.run`): every walk-up priced, the fee, the known cases."""
    pr = price(r["items"], p)
    flats = len(apt["flats"])
    pr["fee"] = fee(p, flats)
    pr["network"] = network_share(p, r["s7"], flats, sum(f["floor_m2"] for f in apt["flats"]) / flats)
    floor = sum(f["floor_m2"] for f in apt["flats"]) / 0.09290304
    pr["known"] = known_cases(pr, p, floor, flats)
    pr["checks"] = checks(pr, pr["known"], r["items"])
    pr["flats"] = flats
    out = OUT_DIR / "pass3"
    (out / "pricing.json").write_text(json.dumps({k: pr[k] for k in ("lines", "totals", "fee", "network", "known", "checks", "unpriced")},
                                                 indent=1, default=str) + NL, encoding="utf-8")
    (out / "pricing.md").write_text(report(pr) + NL, encoding="utf-8")
    pr["written"] = [out / "pricing.json", out / "pricing.md"]
    return pr


ORDER = ("plumbing", "heating", "hvac", "electrical", "fire", "envelope", "tests")


def report(pr: dict) -> str:
    from .systems import report as fmt

    t, n, fe = pr["totals"], pr["flats"], pr["fee"]
    lines = ["Pass 3g step 10b: both walk-ups priced, and the fee", "", fmt(pr["checks"]), "",
             f"A flat (USD 2026; the builder's markups x{pr['builder']:.3f}, the trade's {pr['trade_op']:.0%}):",
             f"{'':12s} " + " ".join(f"{w:>11s}" for w in WALKUPS)]
    for g in ORDER:
        lines.append(f"{g:12s} " + " ".join(f"{t[w].get(g, 0.0) / n:11,.0f}" for w in WALKUPS))
    lines.append(f"{'total':12s} " + " ".join(f"{t[w]['total'] / n:11,.0f}" for w in WALKUPS))
    lines.append(f"{'labour h':12s} " + " ".join(f"{t[w]['labour_h'] / n:11,.0f}" for w in WALKUPS))
    e = t["engineered"]["total"]
    lines += ["", "The engineered design over each usual walk-up (the building; a flat):"]
    for w in WALKUPS[1:]:
        d = e - t[w]["total"]
        lines.append(f"  over {w}: ${d:,.0f}; ${d / n:,.0f} a flat ({d / fe['construction_usd']:.1%} of HUD's construction cost)")
    lines += ["", "What the engineered design's premium buys, a flat (its cost less each usual walk-up's):",
              f"{'':66s} " + " ".join(f"{w:>9s}" for w in WALKUPS[1:])]
    bp = by_purpose(pr)
    for k, v in sorted(bp.items(), key=lambda kv: -(kv[1]["engineered"] - kv[1]["electric"])):
        lines.append(f"  {k[:64]:64s} " + " ".join(f"{(v['engineered'] - v[w]) / n:9,.0f}" for w in WALKUPS[1:]))
    nw = pr["network"]
    lines += ["", "The engineered walk-up's share of the heat network (pass 3 §4, an apartment's; not a building system): "
              + "; ".join(f"{k} ({v['homes']:,.0f} homes on {v['main_km']:g} km) ${v['flat']:,.0f} a flat: the street ${v['street']:,.0f}, "
                          f"the main ${v['main']:,.0f}, the exchanger ${v['plant']:,.0f}" for k, v in nw.items())]
    lines += ["", f"The fee: the building's construction cost ${fe['construction_usd']:,.0f} (HUD's, to 2026); PHFA's cap ${fe['phfa_fee_usd']:,.0f} "
                  f"(MEP drawings in it); Washington's public-works fee ${fe['ofm_fee_usd']:,.0f}, its MEP share ${fe['mep_fee_usd']:,.0f}; "
                  f"the engineered design's extra ${fe['extra_usd']:,.0f} (${fe['extra_flat_usd']:,.0f} a flat)"]
    return "\n".join(lines)


# ---- what the premium buys ----

def purpose(line: dict) -> str:
    """What a priced line is for, so the difference between the walk-ups reads by what it buys."""
    k, cls, w = line["id"], line["class"], line["what"]
    sysw = k.split(" | ")[1] if " | " in k else ""
    if cls == "radiant_manifold":
        return "space heat from the data center's water"
    if cls in ("wallcap_5_hood", "grille_exhaust"):
        return "ventilation: the ERVs, or the bath fans and hoods"
    if k.startswith("insulation | cold"):
        return "the cold risers' insulation, against condensation"
    if k == "test | P-4":
        return "the water and fire services: apart and supervised, or one"
    if k.startswith(("radiant |",)) or sysw == "loop" or cls in ("bphe_50kw",) and "HX-2" in w or k in ("plant | HX-2", "plant | P-1", "plant | V-2", "plant | ET") \
            or k.startswith("test | H-") or (k.startswith("insulation |") and "loop" in w):
        return "space heat from the data center's water"
    if k.startswith(("own |", "central |", "plant |", "electrical | plant circuits", "electrical | central circuits", "test | HW-")) \
            or sysw == "hot" or k.startswith("insulation | hot") or "balancing valve" in w or "water heater" in w or "storage tank" in w \
            or "swing tank" in w or "water-to-water" in w:
        return "hot water: the plant and the loops, or each flat's heater"
    if sysw == "ventilation" or k.startswith(("vent |", "ventilation |", "test | V-")) or cls in ("erv_broan_blp120", "preheater_1kw") \
            or "ERVs' and preheaters'" in w or k.startswith("insulation | ventilation"):
        return "ventilation: the ERVs, or the bath fans and hoods"
    if k.startswith("envelope | air sealing") or k.startswith("envelope | whole-building"):
        return "airtightness to Phius"
    if sysw in ("drain", "vent") and not k.startswith("shared"):
        return "drains and vents: cast iron, or PVC"
    if k == "water | prv":
        return "the pressure-reducing valve, for quiet"
    if k == "water | sleeves" or k.startswith("water | isolators"):
        return "the water pipes held off the frame, for quiet"
    if k == "water | submeters":
        return "the flats' water submeters"
    if k.startswith(("fire | service", "fire | supervision", "fire | combined", "water | domestic")):
        return "the water and fire services: apart and supervised, or one"
    if k == "electrical | pv":
        return "PV"
    if k in ("gas | furnace", "gas | condenser", "gas | furnace circuit"):
        return "heating and cooling in the flats: the mini-splits, or the furnaces and air conditioners"
    if k.startswith("gas |"):
        return "gas: its service lines, meters, piping and vents"
    if k.startswith("electrical | service"):
        return "the electrical service's main"
    if sysw in ("air", "refrigerant", "condensate") or cls in ("minisplit_fujitsu_12_ducted", "in_minisplit", "level_switch"):
        return "heating and cooling in the flats: the mini-splits, or the furnaces and air conditioners"
    return "every walk-up's alike"


def by_purpose(pr: dict) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for x in pr["lines"]:
        d = out.setdefault(purpose(x), {w: 0.0 for w in WALKUPS})
        for w in WALKUPS:
            d[w] += x["usd"][w]
    return out
