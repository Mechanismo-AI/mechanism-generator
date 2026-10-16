# Job corpus-timeline-animator: per-exemplar occupancy timelines

**Purpose.** Menu item E: for every corpus-07 task group, pick exemplar
candidates (lower-median total_width_deg per group, ties by candidate_id),
re-resolve their 720-phase occupancy from the recorded row geometry against
the task's zone_screen.json sidecar, and emit one self-contained HTML (SVG
animation plus meta JSON) so the temporal structure -- window placement,
dwell timing -- is inspectable without re-running the engine. Fail-closed:
recorded tallies/classes/steps/cap anchors; aborts on structural anomalies.

**Run (maintainer-local, from the repo root).**

```sh
python jobs/corpus-timeline-animator/anim_e.py  # runs/analysis/animation-e01/
```

## Scorecard and recorded outcome (2026-10-16)

Verification before delivery: 21/21 python checks on a synthetic 33-row
fixture tree (including tamper paths) and 22/22 headless JS checks of the
generated HTML. Two real-corpus aborts during delivery, both fail-closed
guards working as designed: (1) traversal picked up engine contribution/
bundle dirs -- fixed by accepting only target dirs matching \d{4,}_.+ in
the latest completed r25c run; (2) the engine serializes branch_sign as
float ("1.0"/"-1.0") -- the parser accepts exactly 1, -1, 1.0, -1.0 and
aborts otherwise. A serialization audit against the engine source found no
other mismatches.

The maintainer run: 12/12 sidecars parsed, 499 candidate rows read, menu-B
tallies PASS (12/12 tasks), pooled classes PASS (never 53, quick_pass 192,
drag_over_cap 246, full360 8, invalid 0), 6/6 exemplars selected, assembly
re-validated 720/720 phases. Outputs runs/analysis/animation-e01/
(timeline_animator.html, anim_e_meta.json).

**P0 CONFIRMED:** all 6 exemplars reproduce their recorded windows only in
the screen frame (base = radians(base_angle)); the plain frame matched
none. Unit observation, recorded as an observation, not a claimed
convention: decode_refinement_variables stores base_angle in radians via
remainder(raw[8], 2*pi) but zone_screen.screen() applies math.radians()
again -- the recorded windows live in the "screen" frame where effective
bases are tiny (about 0-6.28 deg). Follow-on: corpus-frame-sweep upgraded
this check from 6 exemplars to all 499 rows.
