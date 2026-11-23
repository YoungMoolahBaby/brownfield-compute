# 23 09 93: Sequence of operations for the walk-up's services

Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Setpoints are the design's; those marked as judgement are set at commissioning.

## 1. The hot-water plant (P-601)

**Normal: on the data center's heat.**

- P-2 starts when TS-4, at 50% of the storage from its cold end (where ST-1B's top joins ST-1A's bottom), falls below 140 F, and stops when it reaches 140 F (Ecosizer's primary aquastat): it runs only with the heating cycle (IECC C404.6.3).
- With P-2, V-1 opens and modulates the data center's water through HX-1 so it leaves HX-1 at 80 F, the heat pump's source (ClimateMaster's table goes to 80 F); HX-1 preheats the circuit to 116.6 F.
- HP-1 runs with P-2 and lifts the circuit to 140 F into ST-1A's top; the storage's water moves from ST-1B to ST-1A as hot water is drawn (the tanks in series).
- BK-1's elements stay locked out (the interlock below).
- ST-2's element switches on at 125 F and off at 133 F (Ecosizer's swing tank).
- MV-1 sends 125 F to the flats.
- P-3 runs while TS-5 reads under 122 F and stops when it reaches 124 F: off when the loop is at temperature (IECC C404.6.1).
- Each flat's TBV, set at 124 F, throttles its flat's return as it nears that, so every flat's loop returns at 122 F or more (4.79 gpm in all, 0.40 a flat, at the design's loss).

**Fallback: the data center's heat gone (step 9a).**

- Entered when TS-1 reads below 80 F, or FS-1 proves no flow, for 10 min.
- V-1 closes; HP-1 stops and is locked out; then BK-1's contactor is released.
- BK-1's own thermostats hold 140 F at its outlet (set within its 120-181 F range); P-2 runs on TS-4 as in normal, so ST-1's 300 gal are heated as in normal running (Ecosizer asks 255).
- Left when TS-1 is back at 80 F or more with flow for 30 min: BK-1 locked out first, then HP-1 enabled.

**Alarms, from PC-1 to the building's manager.**

- the plant in or out of its fallback;
- the storage at TS-4 below 125 F;
- the hot-water return at TS-5 below 122 F (WHO: not less than 50 C) after P-3 has run 30 min;
- HP-1's or BK-1's fault.

## 2. The building loop: the radiant floors (M-601)

**Heating season.**

- P-1 runs while TS-3 reads below 15.5 C (60 F) and stops above it.
- V-2 modulates the data center's water through HX-2 to hold TS-2 on the outdoor reset: -16.3 C out, 40.2 C supply; -10 C out, 36.7 C supply; 0 C out, 31.1 C supply; 10 C out, 25.6 C supply; 15.5 C out, 22.5 C supply. At the heating design dry bulb it is the design's 40.2 C; a straight line to the room's 20 C. A starting curve, tuned at commissioning.
- Each room's thermostat opens and closes its loops' actuators on the flat's manifold; each flat's heat meter counts.

**The data center's heat gone.**

- While the plant is in its fallback (TS-1 or FS-1, above), V-2 closes and P-1 stops: the data center's water, cold or still, would only cool the floors. Each flat's mini-split takes the room (below).
- PC-1 alarms when TS-2 stays 2 K under its reset target for 30 min.

## 3. Each flat's mini-split (M-101 to M-103)

**Heating season.**

- Set to heat at 18 C, 2 K under the floor's 20 C: idle while the floor holds the room, it carries the flat when the floor can't (step 9a: at least twice the design heat).
- Fujitsu's units take no outside mode signal, so the setting is each flat's: the manager confirms it at the season's change and when the plant alarms.

**Cooling season.**

- Cooling at the tenant's setpoint (the design's 75 F).

**Always.**

- Its fan runs continuously at low speed while the ERV runs: the ERV's fresh air enters its return.
- Its static pressure is set to its ducts by Fujitsu's function setting (M-601).
- Its water-level switch stops it (Fujitsu function 46-02, forced stop; IMC 307.2.3).

## 4. The ERV and its preheater (M-101 to M-103)

**Always.**

- The ERV runs continuously at its design flows, supply and exhaust balanced (step 9c tests them).
- The preheater holds the outdoor air leaving it at 2.5 C (36.5 F), only with its airflow proved by its own sensor, and its over-temperature cut-out in the circuit.

## 5. Fire protection (FP-601)

**Always.**

- The waterflow switch: an alarm at the monitoring panel, the exterior horn-strobe, the supervising station.
- Each shutoff valve's tamper switch: a supervisory signal.

## 6. Interlocks, wired, not programmed

- **BK-1 never with HP-1:** BK-1's contactor coil is wired through a normally closed contact of HP-1's enable relay: BK-1 can't energize while HP-1 is enabled. The house panel's size counts only the larger of the two (220.60) and rests on it.
- **the preheater with its airflow:** the preheater's own airflow sensor and over-temperature cut-out (Ouellet's) in its circuit.
- **each mini-split with its drain:** the water-level switch on Fujitsu's forced-stop input (function 46-02).

## 7. Control points

| Tag | What | Chosen |
|---|---|---|
| PC-1 | the plant controller (programmable, with an outdoor sensor, analog outputs and alarm notification) | to select |
| TS-1 | the data center's water entering the annex, its temperature | to select |
| FS-1 | the data center's water entering the annex, a flow switch | to select |
| V-1 | the data center's water through HX-1, a modulating valve | to select |
| P-2 | the heater circuit's pump: ST-1B's bottom (the storage's cold end) through HX-1, HP-1 and BK-1 to ST-1A's top | to select |
| TS-4 | the storage's aquastat, at Ecosizer's height in it | with ST-1 |
| HP-1 | the water-to-water heat pump, its enable | ClimateMaster Tranquility SW036 (basis of design) |
| BK-1 | the backup heater's contactor, its own thermostats | A. O. Smith DRE-52-12 (basis of design) |
| ST-2 | the swing tank's element thermostat | Bradford White RE340S6 (basis of design) |
| MV-1 | the master mixing valve | ASSE 1017 |
| P-3 | the recirculation pump, switched by PC-1 | Grundfos ALPHA2 15-55SF (basis of design) |
| TS-5 | the hot-water return's temperature, at ST-2 | to select |
| TBV | each flat's thermostatic balancing valve, under its lavatory in the vanity, where its loop's return starts (self-acting; IECC C404.6: with access) | Caleffi ThermoSetter 116 series, 1/2 in. (basis of design; Addendum 7) |
| TS-3 | the outdoor air's temperature, shaded, out of the sun and the exhausts | with PC-1 |
| V-2 | the data center's water through HX-2, a modulating valve | to select |
| P-1 | the building loop's circulator | Grundfos ALPHA2 15-55F (basis of design) |
| TS-2 | the building loop's supply leaving HX-2, its temperature | to select |
