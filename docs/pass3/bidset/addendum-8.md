Addendum 8 (made up, found scoping pass 3g step 10, D28): the air-leakage tests to Phius's limits, which the heat loads assume

  Item 1 (the air-leakage tests, E-1 of specification section 01 45 00 and sheet G-002): Addendum 7's E-1 held each flat to 3.0 air changes an hour at 50 Pa, the energy code's limit, and said the heat loads assume it. They don't: they take Phius's limit, 0.06 cfm50 per ft2 of gross enclosure, which is 39-93 cfm50 a flat, 0.31-0.75 air changes an hour. With every flat at 3.0, the building's design heat would be 23.1 kW, not the 19.4 its building loop carries (6.04 gpm, P-1 at 10.7 ft of its curve's 12.3), and its hardest floor would need 35.6 C water, not 34.0. E-1 is now Phius's two tests (its Guidebook, 1.3.3.2 and 1.5.2.3). The whole building, the flats, the stair and the annex together: at most 1,032 cfm50, 0.06 per ft2 of its 17,193 ft2 of gross enclosure, measured at the outside of the thermal boundary, the slab included; multi-point, pressurized and depressurized, by ANSI/RESNET/ICC 380-2022 or ASTM E779. And each flat alone, unguarded: at most 0.30 cfm50 per ft2 of its own shell, which is also the energy code's limit for flats tested one by one (R402.4.1.2, its exception). By a RESNET rater or Phius verifier, a signed report to the code official.
  Item 2 (the documents): specification section 01 45 00, revised (spec-01-45-00-tests-addendum-8.md), and sheet G-002, reissued alone (services-sheet-g-002-addendum-8.pdf), replace Addendum 7's. Nothing else in them changes, and no element of the building, the frame or the services.

What changed: no element of the building, the frame or the services. Section 01 45 00's E-1 is revised and sheet G-002 reissued; Addendum 7's other documents stand.

Checks:
  ok   every check of 7c's designs on the routes passes: 20 checks
  ok   the services model in effect (Addendum 7's) was built from these routes, and its own checks pass (7d): services-addendum-7.ifc, 3,162 elements
  ok   the plant inside the mechanical room, each piece's service space clear of the rest and the door's way in clear: storage-tank-a, storage-tank-b, heat-pump, swing-tank, backup-heater
  ok   each piece of the plant through the mechanical room's door and stood up under its ceiling: the widest 31.0 in. through 42 in.; the longest diagonal 100.5 in. under 108 in.
  ok   the plant's and the fire service's drops through the slab clear of every piece and its service space: plant at 492, 612 in., fire at 492, 588 in.
  ok   the recovery against A. O. Smith's own table (12.3 kW, a 100 F rise: 50 gal/h): 50.4 gal/h
  ok   Fujitsu's heating table read back at its own rows: -15 C 4.54 kW; 15 m at -7.5 m 0.926
  ok   every flat heated by its mini-split alone at the design dry bulb (-16.3 C), the line set's length and the outdoor unit's height counted: least spare 1-back-left: 4080 W against 1986 (factor 0.920)
  ok   the plant's backup heater covers its capacity (Ecosizer's, over its run hours): 12.3 kW against 11.63; 54 gal/h through 94 F
  ok   the house panel's breaker covers its load, the backup heater and the heat pump interlocked (220.60): 108.4 A on 110 A (the backup 15,375 VA counted, the heat pump not)
  ok   each flat's feeder covers its heat pump and preheater together: 91.0 A at most on 100 A
  ok   every feeder within 2% drop on its route: worst 1.98%
  ok   the service carries it all on its main: 166,958 VA, 463 A on 600 A
  ok   the reset gives the design's supply at the heating design dry bulb, and the room's at the room's temperature: 40.2 C at -16.3 C; 20 C at 20 C
  ok   the reset never falls as it gets colder: from -25 to 20 C
  ok   the loop still heats at the warm-weather shutdown (15.5 C): 22.5 C supply
  ok   the heat pump's source setpoint within ClimateMaster's table: 80 F, the table to 80
  ok   BK-1's setpoint within its thermostats' range: 140 F in 120-181
  ok   the swing tank's element switches on at the supply temperature, under the storage's: 125-133 F under 140
  ok   the preheater's setpoint at least Broan's 0 C: 2.5 C
  ok   leaving the fallback takes longer than entering it (no cycling between the heaters): 10 min in, 30 out
  ok   the house panel counts BK-1 and HP-1 as the interlock runs them: the larger, once: BK-1 counted
  ok   the recirculation pump stops with the loop at temperature (IECC C404.6.1): its stop above the least return, under the supply: runs under 122 F, stops at 124, the supply 125
  ok   each flat's balancing valve set within its range, at or over the least return and under the supply: 124 F in 95-140
  ok   every quotation found word for word in its saved source: 39 quotations
  ok   every item says what, who, when, what passes and on what it rests; ids unique: 28 items
  ok   every item resting on the design alone names it: 
  ok   E-1's whole-building limit is the leakage the heat loads take, flat by flat: E-1 1,032 cfm50 on 17,193 ft2 = 0.060 a ft2; the loads 0.060-0.060 (worst 1-front-left)
  ok   the enclosure E-1's limit is on adds up: the flats as the loads take them and the stair are the building's outline: 1,523.6 against 1,523.6 m2, the annex 82.8 m2 added, 9.1 m2 of back wall behind it taken off
  ok   the loads at the leakage Addendum 7's E-1 allowed would need more than the building loop carries (why the test is revised): 23.1 kW against 19.4
  ok   G-002 is reissued alone, as Addendum 8, with E-1's limit on it as text: services-sheet-g-002-addendum-8.pdf: 1 page
