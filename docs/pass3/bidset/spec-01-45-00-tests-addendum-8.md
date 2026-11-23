# 01 45 00: Quality control, the walk-up's tests and inspections

Revised by Addendum 8: E-1, the air-leakage tests (the whole building to Phius's limit, which the heat loads take, and each flat on its own). Otherwise as Addendum 7 issued it.

Made up, from the brownfield-compute study: not a real project, nothing is out to bid. Each test is the code's own (quoted below its table) or the design's claim to be proved; Pennsylvania's code official inspects as 34 Pa. Code 403.45 asks.

## Plumbing

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| P-1 | drainage and vent piping, water test | the plumber (the permit holder) | at rough-in, before the walls and ceilings close | each section filled to at least a 10 ft head of water and held 15 min, tight at all points (cast iron: the air test of 312.3 is the alternative) | IPC 312.2 |
| P-2 | drainage and vent, final test | the plumber (the permit holder) | with the fixtures set and their traps filled | seen complete and to the code; a smoke test, if used, holds 1 in. w.c. for 15 min | IPC 312.4 |
| P-3 | water supply piping, cold and hot and the flats' loops | the plumber (the permit holder) | at rough-in, before the walls and ceilings close | tight under water at not less than its working pressure (60 psi, the most static the building's piping sees) for 15 min; with water, not air: the pipe is PEX | IPC 312.5 |
| P-4 | each backflow prevention assembly (the domestic and the fire service's double checks) | a tester to one of the ASSE 5000-series or CSA B64.10 procedures | at installation, after any repair, then yearly | the procedure's own criteria; yearly inspection that each is operable | IPC 312.10.1-312.10.2 |
| P-5 | the building sewer, where it is in the contract | the plumber (the permit holder) | before backfill | filled to a 10 ft head of water, held 15 min | IPC 312.6 |

## Hot water

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| HW-1 | the flats' hot pipe's insulation | the construction code official | at the energy inspection, before it is covered | 1 in. on the flats' hot pipe and their loops' returns, continuous but where it passes a plate or joist; the bored holes for the bare pipe | IECC C404.4, Table C403.12.3 |
| HW-2 | each hot fixture's pipe off its flat's loop, as built | the construction code official | at rough-in, before the walls and ceilings close | the sizes and runs drawn: each fixture's own pipe at its size, no fixture more than 64 fl oz from circulating water (the design's worst 53, 1-back-left's tub) | IECC C404.5.2 |
| HW-3 | each flat's loop, balanced | the balancing contractor, witnessed by the engineer | at commissioning, before occupancy | each flat's balancing valve set at 124 F; with the plant in normal running and P-3 on, each flat's return at its valve's gauge at or over 122 F (the design: 4.79 gpm in all, 0.40 a flat) | the design (Addendum 7); WHO's 50 C return |
| HW-4 | the recirculation pump's control | the balancing contractor, witnessed by the engineer | at commissioning | P-3 stops when TS-5 reads 124 F and starts under 122 F | IECC C404.6.1; the sequence (23 09 93) |
| HW-5 | the plant: its setpoints, its interlock and its fallback | the balancing contractor, witnessed by the engineer | at commissioning | ST-1 held at 140 F; MV-1 sends 125 F; P-2 runs only with the heating cycle; BK-1 can't be energized while HP-1 is enabled (the wired interlock); with the data center's water cut, the plant goes to its fallback after 10 min and back 30 min after it returns | the sequence (23 09 93); IECC C404.6.3 |

## Building loop

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| H-1 | each flat's radiant tubing, before its topping | the HVAC contractor | before the topping is poured, and through the pour | hydrostatic at 1.5 times the loop's design pressure, not less than 100 psi, for 15 min; held at its operating pressure while the topping is poured | IMC 1209.2, 1208.1 |
| H-2 | the loop's mains, risers and tails | the HVAC contractor | before it is covered | hydrostatic at 1.5 times the design pressure, not less than 100 psi, for 15 min | IMC 1208.1 |
| H-3 | the loop's balance and its pump | the balancing contractor, witnessed by the engineer | at commissioning | each flat's flow at its design (0.27-0.81 gpm), read on its heat meter; 6.04 gpm in all with P-1 at its setting (the design: 10.7 ft at the worst flat, 1-front-left, against its curve's 12.3 ft at its highest fixed speed) | the design (step 3; 9c) |
| H-4 | the outdoor reset | the balancing contractor, witnessed by the engineer | at commissioning | the supply follows the reset (the design's 40.2 C at the heating design temperature, a straight line to the room's) and the loop stops above 15.5 C outdoors | the sequence (23 09 93) |

## Mini-splits

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| R-1 | each line set | the HVAC contractor | before it is covered, and before it runs | pressurized with nitrogen (or helium or argon) for at least 60 min at the outdoor unit's nameplate design pressure with no loss; then a 500-micron vacuum that, isolated, stays under 1,500 microns for 10 min | IMC 1110.2, 1110.5 |
| R-2 | each unit's static pressure | the HVAC contractor | at start-up | set by Fujitsu's function setting to its own ducts' need: 0.38-0.80 in. w.c. by flat (the schedule) | the design (7c) |
| R-3 | each unit's water-level switch | the HVAC contractor | at start-up | water in the drain pan stops the unit (Fujitsu's forced stop, function 46-02) | IMC 307.2.3; the sequence |

## Ventilation

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| V-1 | each ERV's flows | the balancing contractor, witnessed by the engineer (an approved third party where the code official asks) | at commissioning, before occupancy | supply and exhaust each at least 45 cfm (the design; the code's floor 30.8, the kitchen's and the bath's exhaust 25 and 20), within 10% of each other (Phius); a signed report to the code official | IECC R403.6.3 |
| V-2 | duct leakage | - | - | not required: every flat's ducts and units are inside the building's thermal envelope | IECC R403.3.5, exception 1 |

## Envelope

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| E-1 | air leakage (blower door): the whole building, and each flat on its own | a RESNET rater or Phius verifier (an approved third party), a signed report to the code official | the whole building with its envelope complete, before occupancy; each flat with its own shell complete | the whole building (the flats, the stair and the annex together) at most 1,032 cfm at 50 Pa: 0.06 per ft2 of its 17,193 ft2 of gross enclosure, measured at the outside of the thermal boundary, the slab included, the leakage the heat loads take. Multi-point (at least 5 points), pressurized and depressurized, by ANSI/RESNET/ICC 380-2022 or ASTM E779, its accuracy within 10% and its correlation 0.95 or better. Each flat alone, unguarded (RESNET's Test 1): at most 0.30 cfm50 per ft2 of its own shell (its outside and party walls, its floor and ceiling); sampled only as RESNET's Chapter 6 allows, agreed with the QA provider. Revised by Addendum 8 | Phius 2024 1.3.3.2 and 1.5.2.3 (the heat loads' basis); IECC R402.4.1.2, its exception for attached dwelling units |

## Fire protection

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| F-1 | the underground supply, flushed | the sprinkler contractor | before it is connected to the sprinkler piping | at the system's demand rate (56 gpm, the governing design) until the water runs clear | NFPA 13R 10.2.1 |
| F-2 | the sprinkler piping, hydrostatic | the sprinkler contractor | before it is covered | NFPA 13's test (the system has more than 20 sprinklers): 200 psi, for NFPA 13's period (not read here) | NFPA 13R 10.2.2.1; USFA on NFPA 13 |
| F-3 | the waterflow alarm | the sprinkler contractor and the alarm contractor | at acceptance | flow through the inspector's test connection sounds the alarm on the premises within 5 min, and the monitoring panel signals the supervising station | NFPA 13R 10.2.3.1 |
| F-4 | the main drain | the sprinkler contractor | at acceptance | static and residual pressures recorded on the contractor's certificate: the design takes the street at 55 psi static and needs 44.8 psi at 56 gpm | NFPA 13R 10.2.4 |
| F-5 | the contractor's material and test certificate | the sprinkler contractor | before asking for approval | completed and sent to the authority having jurisdiction | NFPA 13R 10.1.2-10.1.3 |

## General

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| G-1 | the work, open for inspection | the permit holder | at each stage | the code official told when it is ready, the work left accessible and exposed | 34 Pa. Code 403.45(c) |
| G-2 | the final inspection | the construction code official | before occupancy | a final report finding the general building, electrical, plumbing, accessibility, fire protection, mechanical and energy work to the Uniform Construction Code | 34 Pa. Code 403.45(e) |

## Electrical

| Id | What | Who | When | Passes | Basis |
|---|---|---|---|---|---|
| EL-1 | the wiring, rough and final | the construction code official, with the electrician | at rough-in, before the walls and ceilings close; and final | to the code (the house panel's BK-1/HP-1 interlock proved in HW-5) | 34 Pa. Code 403.45(a), (e)(2) |

## The codes' words

- **P-1** (PA 2021 IPC (UpCodes), chapter 3): "sections shall not be tested with less than a 10-foot (3048 mm) head of water"
- **P-1** (PA 2021 IPC (UpCodes), chapter 3): "This pressure shall be held for not less than 15 minutes. The system shall then be tight at all points"
- **P-2** (PA 2021 IPC (UpCodes), chapter 3): "The final test of the completed drainage and vent systems shall be visual"
- **P-3** (PA 2021 IPC (UpCodes), chapter 3): "tested and proved tight under a water pressure not less than the working pressure of the system"
- **P-3** (PA 2021 IPC (UpCodes), chapter 3): "for piping systems other than plastic, by an air test"
- **P-4** (PA 2021 IPC (UpCodes), chapter 3): "shall be tested at the time of installation, immediately after repairs or relocation and at least annually"
- **P-5** (PA 2021 IPC (UpCodes), chapter 3): "testing with not less than a 10-foot (3048 mm) head of water and maintaining such pressure for 15 minutes"
- **HW-1** (PA 2021 IECC (UpCodes), chapter CE 4): "Pipe insulation shall be continuous except where the piping passes through a framing member"
- **HW-2** (PA 2021 IECC (UpCodes), chapter CE 4): "For other plumbing fixtures or plumbing appliances; not more than 0.5 gallon"
- **HW-4** (PA 2021 IECC (UpCodes), chapter CE 4): "shall automatically turn off the pump when the water in the circulation loop is at the desired temperature"
- **HW-5** (PA 2021 IECC (UpCodes), chapter CE 4): "shall limit operation of the pump from heating cycle startup to not greater than 5 minutes after the end of the cycle"
- **H-1** (PA 2021 IMC (UpCodes), chapter 12): "Piping to be embedded in concrete shall be pressure tested prior to pouring concrete"
- **H-1** (PA 2021 IMC (UpCodes), chapter 12): "at one and one-half times the maximum system design pressure, but not less than 100 psi"
- **H-2** (PA 2021 IMC (UpCodes), chapter 12): "The duration of each test shall be not less than 15 minutes"
- **R-1** (PA 2021 IMC (UpCodes), chapter 11): "Refrigerant pipe and joints installed in the field shall be exposed for visual inspection and testing prior to being covered"
- **R-1** (PA 2021 IMC (UpCodes), chapter 11): "The system shall be pressurized for a period of not less than 60 minutes"
- **R-1** (PA 2021 IMC (UpCodes), chapter 11): "A vacuum of 500 microns shall be achieved"
- **R-1** (PA 2021 IMC (UpCodes), chapter 11): "The system pressure shall not rise above 1,500 microns for a period of not less than 10 minutes"
- **R-3** (PA 2021 IMC (UpCodes), chapter 3): "one of the following auxiliary protection methods shall be provided"
- **V-1** (PA 2021 IECC (UpCodes), chapter RE 4): "Mechanical ventilation systems shall be tested and verified to provide the minimum ventilation flow rates"
- **V-2** (PA 2021 IECC (UpCodes), chapter RE 4): "A duct air-leakage test shall not be required where the ducts and air handlers are located entirely within the building thermal envelope"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "All other buildings 0.06"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "A whole-building test for airtightness must be"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "the gross envelope is measured at the exterior of the thermal boundary, the same as for the energy model and includes surfaces in contact with the ground"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "Conducted in both pressurization and depressurization"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "The test reports shall indicate a minimum of a 5-point"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "Individual dwelling unit compartmentalization testing shall be"
- **E-1** (Phius 2024 Certification Guidebook v26.1.2): "The test threshold shall be 0.3"
- **E-1** (PA 2021 IECC (UpCodes), chapter RE 4): "When testing individual dwelling units, an air leakage rate not exceeding 0.30 cubic feet per minute per square foot"
- **E-1** (PA 2021 IECC (UpCodes), chapter RE 4): "Attached single and multiple-family building dwelling units"
- **F-1** (NFPA 13R, the 2022 edition's second draft (NFPA's public report)): "The flushing operation shall be continued until the water issuing from the main is clear"
- **F-2** (NFPA 13R, the 2022 edition's second draft (NFPA's public report)): "Systems having more than 20 sprinklers or having a fire department connection shall pass a"
- **F-2** (USFA/NFA, Commercial Fire Sprinkler System Plans Review (2023)): "hydrostatic test pressure of 200 psi"
- **F-3** (NFPA 13R, the 2022 edition's second draft (NFPA's public report)): "The flow test shall result in an audible alarm on the premises within 5 minutes"
- **F-4** (NFPA 13R, the 2022 edition's second draft (NFPA's public report)): "shall be opened and remain open until the system pressure stabilizes"
- **F-5** (NFPA 13R, the 2022 edition's second draft (NFPA's public report)): "The installer shall forward the certificate(s) to the authority having jurisdiction"
- **G-1** (34 Pa. Code 403.45 (Inspections, commercial construction)): "The work shall remain accessible and exposed for inspection"
- **G-2** (34 Pa. Code 403.45 (Inspections, commercial construction)): "shall conduct a final inspection of the completed construction work"
- **EL-1** (34 Pa. Code 403.45 (Inspections, commercial construction)): "shall perform inspections to insure that the construction complies with the approved permit"
