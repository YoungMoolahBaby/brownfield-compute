Addendum 2 (made up, pass 3g step 1, D28): the rooms, the plumbing walls and the service annex

  1. Every room as a space (IfcSpace), 122 in all: its use, the openings in its walls and its net floor area, from forge `rooms` (pass 3g step 1).
  2. The flats' walls: 72 partitions and 12 plumbing walls (IFC's PLUMBINGWALL), each plumbing wall 1/2 in. clear of the party wall.
  3. The service annex behind the stair: its walls, slab and roof; a mechanical and plumbing room (door D5) and an electrical room (door D4), each with its own outside door.
  4. The ground floor's back stair window removed (1-stair/back/0 was safety glazed): the annex covers it. Safety glazing goes 14 -> 13 openings.
  5. Each bedroom's escape window named (24): its own type (W3), side-hinged (a casement), since hung or sliding a window of their size can't clear IBC 2021 1031; every window now says whether it is one (Pset_WindowCommon.FireExit).

What changed (against Addendum 1):
  13 doors: properties
  1 wall: geometry
  76 windows: properties
  24 windows: properties, type
  0 openings in the walls resized or moved
  rooms (spaces): 122 added, 0 deleted, 0 resized or moved, 0 with changed properties
  type new: D4 (Service room door, 36 x 80 in.)
  type new: D5 (Service room door, 42 x 80 in.)
  type new: W3 (Window, 36 x 48 in. Side-hinged (a casement): a bedroom's emergency escape and rescue opening. In normal operation its net clear opening must be at least 5.7 ft2, 24 in high and 20 in wide, its bottom no more than 44 in above the floor (IBC 2021 1031.3); hung or sliding, a unit this size can't give that.)
  type new: annex exterior wall, 7 in. as the building's, framing to be sized (the service annex's walls, one storey (forge rooms, pass 3g step 1; not yet in brownfield frame))
  type new: annex partition, 2x4 wood studs, 1/2 in. gypsum each side (between the annex's mechanical and plumbing room and its electrical room (forge rooms, pass 3g))
  type new: flat partition, 2x4 wood studs, 1/2 in. gypsum each side (the walls between a flat's rooms (forge rooms, pass 3g step 1))
  type new: plumbing wall, 2x6 wood studs, 1/2 in. gypsum on the room side, 1/2 in. clear of the party wall (behind each flat's bath, utility closet and kitchen: the pipes run in it, so none touch or pierce the party wall (forge rooms, pass 3g step 1))
  92 elements added, 1 deleted, 114 changed; no other element, opening or type changed (ifcdiff alone flags 165: the rest only because entity numbers moved)

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
  ok   GlobalIds unique: 2344
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
  ok   a second export is byte-for-byte the same file: 12,443 lines
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
  type mark (window): 101 of 101 -> 100 of 100
  type mark (door): 25 of 25 -> 27 of 27
  storey (window): 101 of 101 -> 100 of 100
  storey (door): 25 of 25 -> 27 of 27
  exterior or not (window): 101 of 101 -> 100 of 100
  exterior or not (door): 25 of 25 -> 27 of 27
  unit width (window): 101 of 101 -> 100 of 100
  unit width (door): 25 of 25 -> 27 of 27
  unit height (window): 101 of 101 -> 100 of 100
  unit height (door): 25 of 25 -> 27 of 27
  rough opening width (window): 0 of 101 -> 0 of 100
  rough opening width (door): 0 of 25 -> 0 of 27
  rough opening height (window): 0 of 101 -> 0 of 100
  rough opening height (door): 0 of 25 -> 0 of 27
  operation (window): 0 of 101 -> 24 of 100
  operation (on the door type) (doortype): 0 of 3 -> 0 of 5
  frame material (window): 0 of 101 -> 0 of 100
  frame material (door): 0 of 25 -> 0 of 27
  frame colour inside (window): 0 of 101 -> 0 of 100
  frame colour inside (door): 0 of 25 -> 0 of 27
  frame colour outside (window): 0 of 101 -> 0 of 100
  frame colour outside (door): 0 of 13 -> 0 of 15
  glass: low-e coating (yes or no) (window): 0 of 101 -> 0 of 100
  glass: gas fill (window): 0 of 101 -> 0 of 100
  glass: tempered (yes or no) (window): 0 of 101 -> 0 of 100
  glass: obscure (yes or no) (window): 0 of 101 -> 0 of 100
  U-factor within the code's limit (window): 101 of 101 -> 100 of 100
  SHGC (window): 0 of 101 -> 0 of 100
  performance grade (design pressure) (window): 0 of 101 -> 0 of 100
  performance grade (design pressure) (door): 0 of 13 -> 0 of 15
  escape window (yes or no) (window): 0 of 101 -> 100 of 100
  escape window: clear opening area (window): 0 of 0 -> 0 of 24
  escape window: clear opening width (window): 0 of 0 -> 0 of 24
  escape window: clear opening height (window): 0 of 0 -> 0 of 24
  escape window: bottom of the clear opening above the floor (window): 0 of 0 -> 0 of 24
  screen (yes or no) (window): 0 of 101 -> 0 of 100
  grilles (window): 0 of 101 -> 0 of 100
  hardware finish (window): 0 of 101 -> 0 of 100
  hardware finish (door): 0 of 25 -> 0 of 27
  install type (window): 0 of 101 -> 0 of 100
  install type (door): 0 of 13 -> 0 of 15
  in a wall (window): 101 of 101 -> 100 of 100
  in a wall (door): 25 of 25 -> 27 of 27
  the wall's construction (on exterior walls) (wall): 12 of 12 -> 15 of 15
  MasterFormat section, level 3 (window): 0 of 101 -> 0 of 100
  MasterFormat section, level 3 (door): 0 of 25 -> 0 of 27
  safety glazing where required (assessed under IBC 2018 2406.4.1-2406.4.3, 2406.4.6 and 2406.4.7) (window): 0 of 2 -> 0 of 1

The schedule, where it moved:
  W3: new (24 windows)
  D4: new (1 door)
  D5: new (1 door)
  W1 count: 99 -> 75
  W1 per_storey: Level 1: 32; Level 2: 33; Level 3: 34 -> Level 1: 24; Level 2: 25; Level 3: 26
  W1 escape_window: not in the model -> False
  W2 count: 2 -> 1
  W2 per_storey: Level 1: 1; Level 2: 1 -> Level 2: 1
  W2 escape_window: not in the model -> False

Openings in the exterior walls (the annex's doors aside): 151.9 -> 150.8 m2 (1,635 -> 1,623 ft2).
