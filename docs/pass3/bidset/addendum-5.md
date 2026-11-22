Addendum 5 (made up, pass 3g step 7e, D28): the services, the frame, the stair's enclosure and the roof hatch

  Item 1 (the stair's enclosure and the annex, IBC 2021 1023.7 and 1023.2): the annex's walls annex-left, annex-right, within 10 ft of the stair's unrated back windows above the annex, are rated 1 hour from the ground to the annex's roof, over their whole length; the door annex-mechanical/left/0 is a 45-minute fire door assembly, self-closing and latching; and the stair's back wall where the annex meets it (the wall between the stair walls, ext-back-1-stair) is part of the stair's 1-hour enclosure.
  Item 2 (the roof hatch, IMC 2021 306.5 and IBC 2021 1011.16): a 30 x 36 in. insulated roof hatch over the stair's top hall, 10.5 ft from the roof's edge (no guards: 1011.13), and a fixed steel ladder to it against the hall's side wall, 18 in. between its rails, its rungs at most 14 in. apart and its rails 30 in. above the roof; the hall keeps 73 in. clear beside it. The hatch is an opaque door in the envelope, at most U-0.20.
  Item 3 (the frame): the completed wood frame is issued, framing-addendum-5.ifc: the flats' partitions and plumbing walls, the service annex, the stair halls' floors and the roof hatch's opening (doubled trimmers and headers), with the shell's members. It replaces Addendum 3's frame, which was for reference.
  Item 4 (the services): the services model is issued, services-addendum-5.ifc, 3,118 elements in their systems: heating, cooling and air 2,678 ft; plumbing 4,008 ft; sprinklers 1,319 ft; wiring 6,567 ft of pipe, duct, conduit and cable, with their fittings, fixtures, equipment and sprinklers. Its schedules: lengths, fittings, equipment, fixtures, sprinklers, registers, switches, holes through the frame and the firestop schedule. For the trades:
    a. PEX is bent on a bend support at its turns; elbows only at the fixtures' stub-outs, the risers' feet, where the top flat's branch leaves its riser and at the manifolds.
    b. Holes through studs, plates and joists are bored at the member's centre: there every pipe and cable clears NEC 300.4(A)(1), IPC 305.6, IMC 305.5 and NFPA 13R 5.2.3.7 without a steel plate.
    c. The feeders' PVC conduit runs straight under the slab between its stub-ups, at most 356° of bends from the meter to a panel (NEC 352.26: 360°), with no pull point between.
    d. A 2 in. vent stack in each column's plumbing wall (IPC 905.1, Table 906.1).
    e. Each mini-split's static pressure is set to its ducts by Fujitsu's function setting, and each takes a UL 508 water-level switch at its drain, wired to its forced stop (IMC 307.2.3 item 4).
  Item 5 (firestopping, IBC 2021 714): 453 openings through rated assemblies, each by its condition in the firestop schedule. Listed systems where they fit as tested (STI F-C-1074, STI F-C-2032); for the other 345, the same maker's engineering judgments, submitted for the authority's approval. Pipe insulation stops at each face of a rated floor (714.3); partitions under a rated ceiling are sheathed in Type X gypsum board and the ceiling is tight to their double top plates (714.5.2 exception 7); the top storey's ceiling, a roof/ceiling Type V-B doesn't rate, and the stair's halls take fireblocking only (718.2.1.4). Every listed floor system found is tested in UL L500 floors; the walk-up's is AWC's WIJ-1.3 (Item 6), so each takes the authority's acceptance or the maker's engineering judgment for it.
  Item 6 (the floors between flats, IBC 2021 711.2.4.3): 1-hour, built as AWC DCA 3 (Feb 2024) WIJ-1.3: 23/32 in. tongue-and-groove sheathing glued and nailed to the I-joists, 2 in. of 3.5 pcf mineral wool batts on 1x4 setting strips along the bottom flanges, resilient channels 16 in. o.c., and one layer of 5/8 in. Type C gypsum board screwed 7 in. o.c. It replaces WIJ-1.1, which the bid set named: WIJ-1.1 asks I-joist flanges of 5.25 in.2 and the PRI-60's are 1-1/2 x 2-5/16 in. (3.5 in.2); WIJ-1.3 asks 2.25. No UL L500 design matches the floor (the I-joist ones name one maker's joists, and two layers of board under resilient channels). Sound (AWC's TR15 estimates, joists 16 in. o.c., 1 in. of gypsum concrete): STC 57; IIC 59 under carpet and pad but 46 under cushioned vinyl, short of IBC 1206.3's 50: a hard floor finish needs a tested underlayment, chosen with the interiors.

What changed (against Addendum 4):
  1 door: properties
  1 slab: geometry
  4 slabs: properties
  1 wall: geometry
  2 walls: properties
  0 openings in the walls resized or moved
  type new: D6 (Roof hatch, 36 x 30 in.)
  4 elements added, 0 deleted, 9 changed; no other element, opening or type changed (ifcdiff alone flags 379: the rest only because entity numbers moved)

Checks on the revision:
  ok   every wall, slab and roof of forge's model, the stair's floors, landings and partitions among them, once, and nothing else: 132 in the file, 132 in forge's model
  ok   every opening, once, and nothing else: 128 in the file, 128 in forge's model
  ok   every window and door, once, and nothing else: 128 in the file, 128 in forge's model
  ok   windows and doors by type: D1 12, D2 1, D3 12, D4 1, D5 1, D6 1, W1 75, W2 1, W3 24
  ok   sizes exact: 128 of 128
  ok   every wall, slab, window and door where forge has it (to 1 mm): worst 0.0000 mm
  ok   every opening where forge has it (to 1 mm): worst 0.0000 mm
  ok   every opening voids its own wall and holds its own window or door: 128 openings, 0 wrong
  ok   no clashes between walls, slabs and roof: 132 elements, 0 clashes
  ok   glazing per flat equals pass 3b's flat_envelope: 12 flats glazed of 12, worst 0.00e+00 m2
  ok   GlobalIds unique: 2386
  ok   schema validation (with express rules): 0 issues
  ok   the stair's flights and railings, once, and nothing else: 4 flights, 9 railings (8 handrails and 1 guard)
  ok   every flight and the guard where forge has it (to 1 mm): worst 0.0000 mm
  ok   every handrail along its path, within its radius: 8 handrails, 0 off
  ok   each flight's risers, treads, riser height and tread length: 4 flights, 0 differ
  ok   each flight, landing and handrail part of its storey's IfcStair: 3 stairs, 0 wrong
  ok   the flat doors 1 h fire doors, self-closing, and the stair walls rated 1 h: 12 doors, 6 stair walls; 0 wrong
  ok   every room once as an IfcSpace, and nothing else: 122 spaces, 122 rooms in forge's model
  ok   every room where forge has it (to 1 mm): worst 0.0000 mm
  ok   every room in its storey, with its net floor area: 122 rooms, 0 wrong
  ok   every window says whether it is an escape window; each bedroom's is side-hinged (casement) and named on the room: 24 escape windows of 100, 24 bedrooms; 0 wrong
  ok   a second export is byte-for-byte the same file: 12,612 lines
  ok   web-ifc reads it, at the version the lock pins: web-ifc 0.0.78 (lock: 0.0.78), IFC4
  ok   web-ifc: every element of forge's model, once, by class, and nothing else: IFCWALL 118, IFCSLAB 14, IFCOPENINGELEMENT 128, IFCWINDOW 100, IFCDOOR 28, IFCSTAIR 3, IFCSTAIRFLIGHT 4, IFCRAILING 9
  ok   web-ifc: windows and doors by type: D1 12, D2 1, D3 12, D4 1, D5 1, D6 1, W1 75, W2 1, W3 24
  ok   web-ifc: sizes exact: 128 of 128
  ok   web-ifc: every element in its storey: 0 wrong
  ok   web-ifc: every opening voids its own wall and holds its own unit: 0 wrong
  ok   web-ifc: every unit's id, kind, flat, face, index and sill height: 0 differ
  ok   web-ifc: each type's U-factor is its params value, or a flat door's its fire rating: 9 of 9
  ok   web-ifc's own geometry: every wall, slab, window, door, flight and the guard where forge has it (to 1 mm): worst 0.0003 mm
  ok   web-ifc's own geometry: every handrail along its path, within its radius: 8 handrails, 0 off
  ok   web-ifc: glazing per flat equals pass 3b's flat_envelope: 12 flats glazed of 12, worst 0.00e+00 m2

The checklist (IDS), where it moved:
  type mark (door): 27 of 27 -> 28 of 28
  storey (door): 27 of 27 -> 28 of 28
  exterior or not (door): 27 of 27 -> 28 of 28
  unit width (door): 27 of 27 -> 28 of 28
  unit height (door): 27 of 27 -> 28 of 28
  rough opening width (door): 0 of 27 -> 0 of 28
  rough opening height (door): 0 of 27 -> 0 of 28
  operation (on the door type) (doortype): 0 of 5 -> 0 of 6
  frame material (door): 0 of 27 -> 0 of 28
  frame colour inside (door): 0 of 27 -> 0 of 28
  frame colour outside (door): 0 of 15 -> 0 of 16
  performance grade (design pressure) (door): 0 of 15 -> 0 of 16
  hardware finish (door): 0 of 27 -> 0 of 28
  install type (door): 0 of 15 -> 0 of 16
  in a wall (door): 27 of 27 -> 27 of 28
  the wall's construction (on exterior walls) (wall): 15 of 15 -> 17 of 17
  MasterFormat section, level 3 (door): 0 of 27 -> 0 of 28

The schedule, where it moved:
  D6: new (1 door)
  D5 fire_rating: not in the model -> 0.75 h
  D5 self_closing: not in the model -> True

Openings in the exterior walls (the annex's doors aside): 150.8 -> 150.8 m2 (1,623 -> 1,623 ft2).
