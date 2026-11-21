RFI 002: which energy code do the exterior walls meet?
  asked: The exterior wall type is 2x6 studs with R-20 in the cavities, U-0.060: the 2018 IECC's zone 5 wall. Pennsylvania's UCC took up the 2021 IECC on 2026-01-01 (55 Pa.B. 7701). Its zone 5 frame wall is U-0.051 (R-23, 13 + 7.5 or 20 + 3.8), and a heated slab needs R-5 under its full area besides its edge insulation. The ground floor's slab carries the radiant tubing. Which code do we price to?
  points at 15 exterior walls by GlobalId
  answered: Answered by Addendum 3: the 2021 IECC, as Pennsylvania adopts it. Item 1 (walls): the exterior walls, and the service annex's, take R-3.8 continuous insulation (1 in. of board outboard of the sheathing) over the R-20 cavities: U-0.051, the 2021 IECC's (Table R402.1.3, 20 + 3.8). The walls thicken inward from 7 to 8 in.; the building's outside stays 100 x 40 ft, so the rooms along the outside walls lose 1 in. and the stair, set against the back wall, moves with it. Item 2 (slabs): the ground floor's heated slab sits on R-5 under its full area, with R-10 at its edge to 4 ft; the annex's slab takes the same edge insulation (Table R402.1.3 and its footnote d).

Addendum 3 (made up, pass 3g, D28): the envelope to Pennsylvania's 2021 energy code

  Item 1 (walls): the exterior walls, and the service annex's, take R-3.8 continuous insulation (1 in. of board outboard of the sheathing) over the R-20 cavities: U-0.051, the 2021 IECC's (Table R402.1.3, 20 + 3.8). The walls thicken inward from 7 to 8 in.; the building's outside stays 100 x 40 ft, so the rooms along the outside walls lose 1 in. and the stair, set against the back wall, moves with it.
  Item 2 (slabs): the ground floor's heated slab sits on R-5 under its full area, with R-10 at its edge to 4 ft; the annex's slab takes the same edge insulation (Table R402.1.3 and its footnote d).
  The windows (U-0.30) and the roof (R-49) already meet the 2021 code: no change.
  The stair's checks after the move: 17 of 17 pass.

What changed (against Addendum 2):
  15 doors: geometry
  9 railings: geometry
  10 slabs: geometry
  2 slabs: properties
  4 stairflights: geometry
  41 walls: geometry
  15 walls: geometry, properties, type
  100 windows: geometry
  115 openings in the walls resized or moved
  rooms (spaces): 0 added, 0 deleted, 50 resized or moved, 50 with changed properties
  type withdrawn: annex exterior wall, 7 in. as the building's, framing to be sized (the service annex's walls, one storey (forge rooms, pass 3g step 1; not yet in brownfield frame))
  type withdrawn: exterior wall, 2x6 wood studs at 16 in. (1 row of 2x6 studs at 406.4 mm (brownfield frame, pass 3b))
  type new: annex exterior wall, 8 in. as the building's, framing to be sized (the service annex's walls, one storey (forge rooms, pass 3g step 1; not yet in brownfield frame))
  type new: exterior wall, 2x6 wood studs at 16 in., R-20 cavity + R-3.8 continuous (1 in.) (1 row of 2x6 studs at 406.4 mm (brownfield frame, pass 3b))
  0 elements added, 0 deleted, 196 changed; no other element, opening or type changed (ifcdiff alone flags 392: the rest only because entity numbers moved)

Checks on the revision:
  ok   every wall, slab and roof of forge's model, the stair's floors, landings and partitions among them, once, and nothing else: 130 in the file, 130 in forge's model
  ok   every opening, once, and nothing else: 127 in the file, 127 in forge's model
  ok   every window and door, once, and nothing else: 127 in the file, 127 in forge's model
  ok   windows and doors by type: D1 12, D2 1, D3 12, D4 1, D5 1, W1 75, W2 1, W3 24
  ok   sizes exact: 127 of 127
  ok   every wall, slab, window and door where forge has it (to 1 mm): worst 0.0000 mm
  ok   every opening where forge has it (to 1 mm): worst 0.0000 mm
  ok   every opening voids its own wall and holds its own window or door: 127 openings, 0 wrong
  ok   no clashes between walls, slabs and roof: 130 elements, 0 clashes
  ok   glazing per flat equals pass 3b's flat_envelope: 12 flats glazed of 12, worst 0.00e+00 m2
  ok   GlobalIds unique: 2348
  ok   schema validation (with express rules): 0 issues
  ok   the stair's flights and railings, once, and nothing else: 4 flights, 9 railings (8 handrails and 1 guard)
  ok   every flight and the guard where forge has it (to 1 mm): worst 0.0000 mm
  ok   every handrail along its path, within its radius: 8 handrails, 0 off
  ok   each flight's risers, treads, riser height and tread length: 4 flights, 0 differ
  ok   each flight, landing and handrail part of its storey's IfcStair: 2 stairs, 0 wrong
  ok   the flat doors 1 h fire doors, self-closing, and the stair walls rated 1 h: 12 doors, 6 stair walls; 0 wrong
  ok   every room once as an IfcSpace, and nothing else: 122 spaces, 122 rooms in forge's model
  ok   every room where forge has it (to 1 mm): worst 0.0000 mm
  ok   every room in its storey, with its net floor area: 122 rooms, 0 wrong
  ok   every window says whether it is an escape window; each bedroom's is side-hinged (casement) and named on the room: 24 escape windows of 100, 24 bedrooms; 0 wrong
  ok   a second export is byte-for-byte the same file: 12,464 lines
  ok   web-ifc reads it, at the version the lock pins: web-ifc 0.0.78 (lock: 0.0.78), IFC4
  ok   web-ifc: every element of forge's model, once, by class, and nothing else: IFCWALL 116, IFCSLAB 14, IFCOPENINGELEMENT 127, IFCWINDOW 100, IFCDOOR 27, IFCSTAIR 2, IFCSTAIRFLIGHT 4, IFCRAILING 9
  ok   web-ifc: windows and doors by type: D1 12, D2 1, D3 12, D4 1, D5 1, W1 75, W2 1, W3 24
  ok   web-ifc: sizes exact: 127 of 127
  ok   web-ifc: every element in its storey: 0 wrong
  ok   web-ifc: every opening voids its own wall and holds its own unit: 0 wrong
  ok   web-ifc: every unit's id, kind, flat, face, index and sill height: 0 differ
  ok   web-ifc: each type's U-factor is its params value, or a flat door's its fire rating: 8 of 8
  ok   web-ifc's own geometry: every wall, slab, window, door, flight and the guard where forge has it (to 1 mm): worst 0.0003 mm
  ok   web-ifc's own geometry: every handrail along its path, within its radius: 8 handrails, 0 off
  ok   web-ifc: glazing per flat equals pass 3b's flat_envelope: 12 flats glazed of 12, worst 0.00e+00 m2

The checklist (IDS), where it moved:
  (nowhere)

The schedule, where it moved:
  (nowhere)

Openings in the exterior walls (the annex's doors aside): 150.8 -> 150.8 m2 (1,623 -> 1,623 ft2).
