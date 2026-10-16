You are a careful clerk summarizing a mechanism-synchronization experiment.
Each variant is a rotate/scaled copy of the same two-task document (a gate
task and a catcher task). For each variant, every combination of selected
candidates was checked against hard events (a phase window for the handoff)
and hard ordering relations (a required lead between release and grab, in
degrees of master-cycle phase). The digest below was computed exactly by a
script; all numbers in it are trustworthy.

Write the following, using ONLY numbers that appear in the digest:
1. For each variant: 2-3 sentences in plain language saying which
   constraint fails, how often, and by how much (quote the numbers).
2. Group the variants into failure families (e.g. window overshoot,
   reversed order, lead too short) and name the family of each variant.
3. One short paragraph on what the anchor_probe intervals mean for fixing
   each variant by re-phasing (shifting a task's offset), if probe data is
   present.
Do not invent numbers, do not recompute anything, and say so explicitly
if the digest does not contain what a section asks for.

DIGEST (computed exactly by script):

### variant corpus_pair_01: verdict=failed, passing 0/15 combinations
event handoff_window (hard): fails in 15/15 combos; window=[100, 140] deg
  participant 0: phase 92.1..131.3 deg (12/15 phases below window by 4.6..7.9 deg; 3/15 phases inside)
  participant 1: phase 18.2..20.0 deg (15/15 phases below window by 80.0..81.8 deg)
relation release_before_grab (ordering, hard): fails in 15/15 combos; required lead [10, 45] deg
  achieved lead 246.9..287.9 deg
  15/15 combos exceed the maximum by 201.9..242.9 deg
  15/15 combos have lead > 180 deg (equivalent to -113.1..-72.1 deg, i.e. the pair happens in the reversed order)
anchor_probe (feasible offset intervals per task): [{"task": "catcher", "passing_offsets_count": 41, "best_passing_combinations": 3, "best_offsets_deg": [88.0, 89.0, 90.0, 91.0, 92.0, 93.0, 94.0, 95.0, 96.0, 97.0, 98.0, 99.0, 100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0, 110.0, 111.0, 112.0, 113.0, 114.0, 115.0, 116.0, 117.0, 118.0, 119.0, 120.0, 124.0], "feasible_intervals_deg": [{"from_deg": 86.0, "to_deg": 126.0, "max_passing_combinations": 3}]}, {"task": "gate", "passing_offsets_count": 0, "best_passing_combinations": 0, "best_offsets_deg": [], "feasible_intervals_deg": []}]

### variant corpus_pair_02: verdict=failed, passing 0/25 combinations
event handoff_window (hard): fails in 0/25 combos; window=[100, 140] deg
  participant 0: phase 115.4..123.3 deg (25/25 phases inside)
  participant 1: phase 111.2..122.4 deg (25/25 phases inside)
relation release_before_grab (ordering, hard): fails in 25/25 combos; required lead [10, 45] deg
  achieved lead 0.4..359.2 deg
  7/25 combos short of the minimum by 3.1..9.6 deg
  18/25 combos exceed the maximum by 302.9..314.2 deg
  18/25 combos have lead > 180 deg (equivalent to -12.1..-0.8 deg, i.e. the pair happens in the reversed order)
anchor_probe (feasible offset intervals per task): [{"task": "catcher", "passing_offsets_count": 30, "best_passing_combinations": 24, "best_offsets_deg": [21.0, 22.0], "feasible_intervals_deg": [{"from_deg": 4.0, "to_deg": 33.0, "max_passing_combinations": 24}]}, {"task": "gate", "passing_offsets_count": 25, "best_passing_combinations": 23, "best_offsets_deg": [340.0], "feasible_intervals_deg": [{"from_deg": 332.0, "to_deg": 356.0, "max_passing_combinations": 23}]}]

### variant corpus_pair_03: verdict=failed, passing 0/25 combinations
event handoff_window (hard): fails in 25/25 combos; window=[100, 140] deg
  participant 0: phase 114.0..138.5 deg (25/25 phases inside)
  participant 1: phase 153.4..164.7 deg (25/25 phases above window by 13.4..24.7 deg)
relation release_before_grab (ordering, hard): fails in 1/25 combos; required lead [10, 45] deg
  achieved lead 14.9..50.7 deg
  1/25 combos exceed the maximum by 5.7 deg
anchor_probe (feasible offset intervals per task): [{"task": "catcher", "passing_offsets_count": 32, "best_passing_combinations": 5, "best_offsets_deg": [331.0, 332.0, 333.0, 334.0, 335.0, 336.0, 337.0, 338.0, 339.0, 340.0], "feasible_intervals_deg": [{"from_deg": 320.0, "to_deg": 351.0, "max_passing_combinations": 5}]}, {"task": "gate", "passing_offsets_count": 0, "best_passing_combinations": 0, "best_offsets_deg": [], "feasible_intervals_deg": []}]

### variant corpus_pair_04: verdict=failed, passing 0/25 combinations
event handoff_window (hard): fails in 25/25 combos; window=[100, 140] deg
  participant 0: phase 116.2..136.2 deg (25/25 phases inside)
  participant 1: phase 161.8..291.9 deg (25/25 phases above window by 21.8..151.9 deg)
relation release_before_grab (ordering, hard): fails in 22/25 combos; required lead [10, 45] deg
  achieved lead 25.6..175.7 deg
  22/25 combos exceed the maximum by 0.5..130.7 deg
anchor_probe (feasible offset intervals per task): [{"task": "catcher", "passing_offsets_count": 44, "best_passing_combinations": 9, "best_offsets_deg": [213.0], "feasible_intervals_deg": [{"from_deg": 195.0, "to_deg": 219.0, "max_passing_combinations": 9}, {"from_deg": 325.0, "to_deg": 343.0, "max_passing_combinations": 3}]}, {"task": "gate", "passing_offsets_count": 0, "best_passing_combinations": 0, "best_offsets_deg": [], "feasible_intervals_deg": []}]

### variant corpus_pair_05: verdict=no_candidates, passing 0/0 combinations

### variant corpus_pair_06: verdict=failed, passing 0/25 combinations
event handoff_window (hard): fails in 25/25 combos; window=[100, 140] deg
  participant 0: phase 193.7..221.6 deg (25/25 phases above window by 53.7..81.6 deg)
  participant 1: phase 277.0..286.0 deg (25/25 phases above window by 137.0..146.0 deg)
relation release_before_grab (ordering, hard): fails in 25/25 combos; required lead [10, 45] deg
  achieved lead 55.4..92.3 deg
  25/25 combos exceed the maximum by 10.4..47.3 deg
anchor_probe (feasible offset intervals per task): [{"task": "catcher", "passing_offsets_count": 0, "best_passing_combinations": 0, "best_offsets_deg": [], "feasible_intervals_deg": []}, {"task": "gate", "passing_offsets_count": 0, "best_passing_combinations": 0, "best_offsets_deg": [], "feasible_intervals_deg": []}]
