# Qualification and success

There are three separate questions:

1. Is this a valid OMTS document? Schema and semantic validation answer this.
2. Can an implementation represent these requirements? Adapter capability checks
   answer this for a restricted subset.
3. Does a generated mechanism satisfy them? Only actual evaluation can answer this.

`omts validate` answers the first question. `omts adapt` also answers the second
and produces a plan with status `prepared_not_evaluated`. Neither establishes the
third. Even accepting `requested_validation_level: kinematic_candidate` expresses
the request, not an achieved result.

OMTS's vocabulary includes kinematic, mechanically screened, dynamically evaluated,
structurally evaluated, and prototype validated outputs. The public engine performs
kinematic checks only. The adapter rejects requests above `kinematic_candidate`.

In public R2.5c outputs, read `selection_eligible`, `engineering_acceptable`,
and `qualification_level`. Physical assembly alone is not path accuracy or adequate
transmission. The historical label `engineering_acceptable` describes that engine's
kinematic thresholds; it is not proof of dynamic, structural, or prototype validity.

The historical engine can reserve an unqualified fixed-reference mechanism in its
selected exports. This adapter sets `--portfolio_guarantee_fixed_count 0` and
`--strict_qualification` so those references cannot bypass qualified selection.
The public alpha also fixes the engine so fixed reservation considers only eligible
candidates, and rejects unqualified fallback. Raw `all_candidates` and stage reports can still
contain rejected mechanisms. Count eligible candidates, not output files.

For a three-pose task, the engine checks the point position and directed coupler
orientation at the same three optimized phases:

- `path_acceptable` reports the position requirements, including physical
  feasibility and the shared path budget.
- `orientation_acceptable` requires valid target assemblies and every angular
  error within its own tolerance. Errors use the shortest circular difference;
  reversing the directed axis by 180 degrees is a different orientation.
- `pose_acceptable` requires both position and orientation acceptance.
- `selection_eligible` additionally requires the practical transmission,
  robustness, and compactness criteria. `engineering_acceptable` applies the
  preferred kinematic thresholds as well.

A position match with a failed orientation is labeled
`path_acceptable_but_orientation_failed`. It cannot enter the selected portfolio.
The report records requested and achieved world-frame angles and each target's
absolute angular error. The tool frame is at P, with +x parallel to A to B; see
the [three-pose guide](three-pose.md) for its precise convention.

Coupler orientation describes the direction of that frame. Transmission angle
describes the angle between moving links and has its own acceptance thresholds.
Passing either check does not imply passing the other. These pose checks constrain
three configurations; they do not prescribe the intervening orientation path,
speed, or dwell.

Fewer than `top_k` results, including none, is a valid outcome. An exported plan or
nonempty result directory does not establish success.

When a panel is specified, both selection and preferred engineering acceptance
also require `panel_acceptable`. Failed or missing screening cannot qualify.
`path_acceptable` and `pose_acceptable` retain their position/angle meanings.
Panel failure after a position pass is reported as
`path_acceptable_but_panel_failed` unless an orientation failure takes precedence.
Read [the sampled panel definition](tolerance-and-panel.md): a passing result
does not certify continuous containment, clearance between moving links, thickness
or physical safety.
