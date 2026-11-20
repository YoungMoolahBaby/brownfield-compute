What Addendum 1 changed, element by element (by GlobalId):
  12 doors: attributes, geometry, properties, type
  24 windows: properties, type
  12 openings in the walls resized or moved
  type withdrawn: D1 (Patio door, 72 x 80 in. Safety glazing: IBC 2018 2406.4.1-2406.4.3 call for it here.)
  type withdrawn: W2 (Window, 36 x 48 in. Safety glazing: IBC 2018 2406.4.1-2406.4.3 call for it here.)
  type new: D1 (Patio door, 60 x 80 in. Safety glazing: IBC 2018 2406.4.1-2406.4.3 call for it here.)
  0 elements added, 0 deleted, 36 changed; no other element, opening or type changed (ifcdiff alone flags 114: the rest only because entity numbers moved)

The schedule, where it moved:
  W2: withdrawn (24 windows)
  W1 count: 77 -> 101
  W1 per_storey: Level 1: 25; Level 2: 26; Level 3: 26 -> Level 1: 33; Level 2: 34; Level 3: 34
  D1 width: 6'-0" -> 5'-0"
  D1 width_mm: 1828.8 -> 1524.0
  D1 description: Patio door, 72 x 80 in. Safety glazing: IBC 2018 2406.4.1-2406.4.3 call for it here. -> Patio door, 60 x 80 in. Safety glazing: IBC 2018 2406.4.1-2406.4.3 call for it here.
  D1 tempered: not in the model -> True
  D1 safety_glazing: not in the model -> tempered
