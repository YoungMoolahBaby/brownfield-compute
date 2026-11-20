What Addendum 1 changed, element by element (by GlobalId):
  12 doors: attributes, geometry, properties, type
  24 windows: properties, type
  12 openings in the walls resized or moved
  type withdrawn: D1 (Patio door, 72 x 80 in. Safety glazing: IBC 2018 2406.4.1 calls for it here.)
  type new: D1 (Patio door, 60 x 80 in. Safety glazing: IBC 2018 2406.4.1 calls for it here.)
  type changed: W2 (description: Window, 36 x 48 in. Safety glazing: IBC 2018 2406.4.2, 2406.4.3 and 2406.4.6 call for it here. -> Window, 36 x 48 in. Safety glazing: IBC 2018 2406.4.3 and 2406.4.6 call for it here.)
  0 elements added, 0 deleted, 36 changed; no other element, opening or type changed (ifcdiff alone flags 126: the rest only because entity numbers moved)

The schedule, where it moved:
  W1 count: 75 -> 99
  W1 per_storey: Level 1: 24; Level 2: 25; Level 3: 26 -> Level 1: 32; Level 2: 33; Level 3: 34
  W2 count: 26 -> 2
  W2 per_storey: Level 1: 9; Level 2: 9; Level 3: 8 -> Level 1: 1; Level 2: 1
  W2 description: Window, 36 x 48 in. Safety glazing: IBC 2018 2406.4.2, 2406.4.3 and 2406.4.6 call for it here. -> Window, 36 x 48 in. Safety glazing: IBC 2018 2406.4.3 and 2406.4.6 call for it here.
  W2 safety_glazing_required: yes (IBC 2018 2406.4.2, IBC 2018 2406.4.3, IBC 2018 2406.4.6) -> yes (IBC 2018 2406.4.3, IBC 2018 2406.4.6)
  D1 width: 6'-0" -> 5'-0"
  D1 width_mm: 1828.8 -> 1524.0
  D1 description: Patio door, 72 x 80 in. Safety glazing: IBC 2018 2406.4.1 calls for it here. -> Patio door, 60 x 80 in. Safety glazing: IBC 2018 2406.4.1 calls for it here.
  D1 tempered: not in the model -> True
  D1 safety_glazing: not in the model -> tempered
