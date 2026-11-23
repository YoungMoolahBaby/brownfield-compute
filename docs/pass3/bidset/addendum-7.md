Addendum 7 (made up, pass 3g step 9, D28): each flat's hot-water loop, the plant's storage and backup heater, the control sequence and the tests

  Item 1 (the hot water, IECC 2021 C404): a plant serving several flats comes under the energy code's commercial hot-water rules (R403.8), which the bid set's hot water didn't meet. Each flat's hot water is now a loop of its own: its hot branch runs past its fixtures to its lavatory, where a thermostatic balancing valve in the vanity starts its 0.5 in. return to the return riser: Caleffi ThermoSetter 116, 1/2 in. (basis of design), set 124 F, reached through the vanity's doors (C404.6: with access). Each fixture's own pipe is sized for it (tub 0.75, lav 0.5, sink 0.75, dishwasher 0.75, washer 0.75 in.): no fixture holds more than 64 fl oz from the loop (C404.5.2; the worst 53, 1-back-left's tub). The flats' hot pipe and returns are insulated 1 in. (C404.4, Table C403.12.3), stopped at each plate and joist, their holes bored for the bare pipe. P-3 runs while the return at the swing tank is under 122 F and stops at 124 F (C404.6.1); it moves 4.79 gpm at 3.3 ft round the longest circuit, within its rated 10.7 gpm at 8.202 ft. The returns: 1.25 in. main, 0.75 in. risers. The loop loses 176 W a flat (72 in the risers and mains).
  Item 2 (the hot-water plant): with each flat's loop, Ecosizer asks 255 gal of storage on the routes (259 on the square lengths), over the 250 gal tank Addendum 5's model placed. The storage is now 2 Lochinvar HP150G tanks in series, 300 gal (basis of design): cold in at ST-1B's bottom, hot out of ST-1A's top, for stratification. The next single tank, 450 gal and 49 in. across, wouldn't pass the mechanical room's 42 in. door. The swing tank's element is 4.5 kW (Ecosizer asks 4.03 kW on the square lengths, 3.70 on the routes; Bradford White makes 4.0 and 4.5 at 208 V); the plant's capacity 11.63 kW. The mechanical room's floor: the tanks along its far wall, the heat pump by the door, the swing tank and the backup heater (Item 3) on the back wall, each with its maker's service space; the plant's mains drop through the slab 12 in. off the wall to the building.
  Item 3 (when the data center's heat is gone): a backup heater, BK-1, on the heater circuit after HP-1: A. O. Smith DRE-52-12 (basis of design), 12.3 kW against the plant's 11.63, its elements locked out unless the data center's water is gone, and never energized with HP-1 enabled (its contactor's coil wired through a normally closed contact of HP-1's enable). The flats are heated by their mini-splits alone: each covers its flat at the design temperature (-16.3 C), the least margin 1-back-left's 4,080 W against 1,986. The wiring counts each flat's heating as its heat pump and the ERV's preheater together: each feeder at most 91.0 A on its 100 A breaker; the house panel 110 A (108.4 A calculated: BK-1 counted, HP-1 not, NEC 220.60); the service 463 A on its 600 A main. The house panel's 120% rule now takes 6.7 kW AC of the roof's PV.
  Item 4 (the building loop's pump): P-1, Grundfos ALPHA2 15-55F (basis of design), needs 10.7 ft at 6.04 gpm on its worst path (1-front-left), against 12.3 ft on its curve III, its highest fixed speed, with 10% kept in hand; the loop's risers 0.75 in.
  Item 5 (the control sequence): specification section 23 09 93 (spec-23-09-93-sequence.md) is issued, 31 steps in 5 systems, normal running and the fallback, 3 interlocks wired, not programmed, and 17 control points. 8 points are still to select by the bidder (PC-1, TS-1, FS-1, V-1, P-2, TS-5, V-2, TS-2).
  Item 6 (the tests and inspections): specification section 01 45 00 (spec-01-45-00-tests.md) is issued, 28 items in 9 areas (plumbing, hot water, building loop, mini-splits, ventilation, envelope, fire protection, general, electrical): what, who, when and what passes, 24 of them the codes' own tests quoted in their words, the rest the design's claims to be proved at commissioning.
  Item 7 (the services model and the sheets, reissued): services-addendum-7.ifc, 3,162 elements. Against Addendum 5's, 59 added (each flat's return and its balancing valve, the plant's two tanks and backup heater), 15 removed (the one storage tank, and fittings of runs routed again), 532 changed in route, length or size, most of them routed again around the flats' returns; by system: cold 0 added, 55 changed, 0 removed; hot 47 added, 234 changed, 5 removed; loop 0 added, 35 changed, 0 removed; power 0 added, 148 changed, 0 removed; vent 12 added, 60 changed, 10 removed. Its schedules are reissued with it. The services sheets, services-sheets-addendum-7.pdf: 23 sheets, G-002 (the tests) and M-602 (the sequence) new, P-601 and M-601 revised, every plan and elevation redrawn from the revised model. They replace Addendum 6's sheets.

What changed: no element of the building or the frame. The services model, against Addendum 5's (services-addendum-5.ifc -> services-addendum-7.ifc): cold: 0 added, 55 changed, 0 removed; hot: 47 added, 234 changed, 5 removed; loop: 0 added, 35 changed, 0 removed; power: 0 added, 148 changed, 0 removed; vent: 12 added, 60 changed, 10 removed. The sheets are reissued; the sequence and the tests are issued as specification sections.

Checks:
  ok   every check of 7c's designs on the routes passes: 20 checks
  ok   the services model was built from these routes, and its own checks pass (7d): services-addendum-7.ifc, 3,162 elements
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
  ok   every quotation found word for word in its saved source: 32 quotations
  ok   every item says what, who, when, what passes and on what it rests; ids unique: 28 items
  ok   every item resting on the design alone names it: 
  ok   what the services model changed is read from every element of both files: Addendum 5's as published, Addendum 7's as 7d counted them: 3,118 -> 3,162: 59 added, 532 changed, 15 removed
  ok   every element of the services model on a sheet (its fittings in the schedules): 1574 of 1574
  ok   the services model was built from the routes these sheets' figures come from: requests 3e27638e92285a1d
  ok   each sheet's number reads as text in the PDF (what a bidder's tools search): 23 of 23 sheets
