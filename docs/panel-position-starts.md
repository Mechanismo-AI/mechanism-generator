# Optional geometric candidates for panel-position tasks

Add `--panel_position_geometry` to a `mechanism-generate` command that supplies
three target positions, `--panel_bounds`, and `--carrier_size`. The option is off
by default. It supports unordered position-only tasks with adjustable base
spacing. Pose tasks, ordered tasks, and tasks without a panel bypass this branch.
It is currently a CLI option, not an OMTS document setting.

The branch samples 65,536 deterministic combinations of free coupler angles and
link geometry. Circumcenters construct two revolute dyads through the requested
positions. Physical constraints, search bounds, transmission floors, fixed-pivot
clearance, and sampled whole-cycle carrier/panel containment screen the proposals
before at most six diverse parents are retained. Requested assembly-branch limits
are respected. No reference solution, requested orientation, or model prediction
is an input to this geometric construction.

The existing learned search and its shared path reference remain unchanged.
This option adds computation and candidates; it does not replace refinement
starts. The analytic parents are evaluated without gradient refinement and enter
the usual qualification, ranking, deduplication and export flow. They remain in
the full candidate report even if another qualifying mechanism ranks higher.
An empty geometric result leaves the existing search available.

This differs from `--position_geometry`, which replaces a bounded number of starts
for tasks without a panel. Both options can be supplied; each applies only to its
supported task type. Base spacing remains adjustable and model weights unchanged.

Run manifests and `panel_position_initialization.json` record whether the branch
was disabled, bypassed, or sampled, along with counts, timing and its source hash.
Candidate records retain the construction method and sample index. Local
contribution schema 0.7 preserves these fields and still reads schemas 0.1–0.6.
Review and submission remain voluntary; running the solver uploads nothing.

Panel containment uses 7,201 samples by default and zero-thickness links, plus the
specified rectangular carrier. This is not a continuous-clearance or collision
certificate. A missed solution does not establish that a task is impossible.
See [the full-pipeline validation](panel-position-validation.md) for measured
results and limits of the constructed test corpus.
