Addendum 4 (made up, pass 3g step 3c, D28): the glass: ENERGY STAR's Northern zone, at a solar heat gain that sizes the cooling

  Item 1 (glass): every window and patio door is rated, whole unit, at a U-factor of at most 0.22 Btu/h ft2 F (NFRC 100; the code asks 0.30), a solar heat gain coefficient from 0.17 to 0.25 (NFRC 200) and air leakage of at most 0.3 cfm/ft2: ENERGY STAR v7's Northern zone, which all of western Pennsylvania is in. The window and door schedule now carries the U-factor and the SHGC (Pset_DoorWindowGlazingType.SolarHeatGainTransmittance).
  Why: the flats' cooling (step 3c). The schedule gave no SHGC, and the cooling design had assumed 0.35: at that, no 1-ton unit covers a flat; at this glass one does. The winter sun the glass gives up is heat the data center's loop supplies anyway.
  Why the U-factor: ENERGY STAR, chosen beyond the code; it lowers the flats' heat, and the water their floors need.
  No drawing changes; no opening moves or resizes.

What changed (against Addendum 3):
  12 doors: properties
  100 windows: properties
  0 openings in the walls resized or moved
  type changed: D1 (properties)
  type changed: W1 (properties)
  type changed: W2 (properties)
  type changed: W3 (properties)
  0 elements added, 0 deleted, 112 changed; no other element, opening or type changed (ifcdiff alone flags 250: the rest only because entity numbers moved)

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
  ok   GlobalIds unique: 2351
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
  ok   a second export is byte-for-byte the same file: 12,471 lines
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
  SHGC (window): 0 of 100 -> 100 of 100
  SHGC (door): 0 of 12 -> 12 of 12

The schedule, where it moved:
  W1 u_factor_btu_h_ft2_f: 0.30 -> 0.22
  W1 u_factor_w_m2k: 1.703 -> 1.249
  W1 u_factor_source: params pass3.envelope.window_u (medium) -> params systems.addendum_4.window_u_max (high)
  W1 shgc: not in the model -> 0.25
  W2 u_factor_btu_h_ft2_f: 0.30 -> 0.22
  W2 u_factor_w_m2k: 1.703 -> 1.249
  W2 u_factor_source: params pass3.envelope.window_u (medium) -> params systems.addendum_4.window_u_max (high)
  W2 shgc: not in the model -> 0.25
  W3 u_factor_btu_h_ft2_f: 0.30 -> 0.22
  W3 u_factor_w_m2k: 1.703 -> 1.249
  W3 u_factor_source: params pass3.envelope.window_u (medium) -> params systems.addendum_4.window_u_max (high)
  W3 shgc: not in the model -> 0.25
  D1 u_factor_btu_h_ft2_f: 0.30 -> 0.22
  D1 u_factor_w_m2k: 1.703 -> 1.249
  D1 u_factor_source: params pass3.envelope.window_u (medium) -> params systems.addendum_4.window_u_max (high)
  D1 shgc: not in the model -> 0.25

Openings in the exterior walls (the annex's doors aside): 150.8 -> 150.8 m2 (1,623 -> 1,623 ft2).
