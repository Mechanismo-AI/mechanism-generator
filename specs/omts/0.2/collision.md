# OMTS v0.2 Collision Geometry (Draft)

> **Draft 0.2.0-collision.** This document grounds open questions 2 and 3 of
> `synchronization.md` in a deliberately small collision model. It is a
> specification draft for public review. Verifier wiring has landed (G3):
> the adapter records `regions` and per-task collision body models in the
> plan's line section, and `omts verify-line` reports sampled occupancy
> windows per selected candidate as data in `line_result.json`. The composed
> timeline artifact has landed (G4): `omts timeline` writes `timeline.json`
> with, per sampled master phase, each participating task's input phase and
> body poses. Neither artifact gates the verdict. The adapter still rejects
> relations over derived region events until they gate the verdict (G5).

**Status:** Draft; G1 through G4 of the staged plan in section 7 have landed
(spec text, a pure-stdlib geometry kernel parity-tested against the
engine's independent NumPy panel screening, document validation, verifier
wiring that reports sampled occupancy windows as data, and the composed
timeline artifact).

**Depends on:** OMTS v0.1 (`specs/omts/0.1/specification.md`), OMTS v0.2
synchronization (`synchronization.md`).

## 1. Purpose and scope

Planar, coplanar collision timing between composed mechanisms, in the same
right-handed XY world frame and world units as task targets. In scope: link
centerlines with optional thickness, an optional carrier rectangle, fixed
pivot discs, and static rectangular or circular named regions. Out of scope:
meshes, 3D, link-shape catalogs, moving regions, dynamics, self-collision
certification, and machinery safety.

The honesty rule is inherited from v0.1: a collision-free claim requires an
implementation that evaluates the mechanism links and moving bodies, not only
the end-effector point. Occupancy is sampled, not certified: it proves
nothing between samples, and every artifact that reports it says so.

## 2. Collision bodies

Per task, under `requirements.collision`:

```yaml
requirements:
  collision:
    bodies:
      links: {thickness: 2}        # capsule radius per link centerline
      carrier: {width: 50, depth: 10}
    steps: 720
    mode: hard
```

- `links.thickness` is a non-negative radius in world units; 0 (the default)
  reduces bodies to zero-thickness centerlines, the same model the engine's
  sampled panel screening already reasons about.
- `carrier` is optional and identical to the engine panel carrier: a
  rectangle centered on the coupler point P, width axis along A to B
  (frame `coupler_A_to_B`).
- The fixed pivots are discs of radius `links.thickness`; the ground link is
  static geometry, not a moving body.
- `steps` is the sampled phase count per task cycle, an integer in
  [361, 72001] (the panel sampling range).
- A task with a declared collision body model contributes the derived events
  of section 4; a task without one contributes none, and relations that
  reference its derived events are rejected at validation (fail-closed).

## 3. Regions

Document-level named static regions:

```yaml
regions:
  - id: shared_zone
    shape: box            # box | circle
    min: [285, 0]
    max: [335, 60]
  - id: approach
    shape: circle
    center: [310, 30]
    radius: 20
```

Region ids must be unique, and events or relations that name a region id
must find it declared. Box bounds must increase componentwise; circle radii
must be positive; all values finite. Regions are static in v0.2: a moving
region is a mechanism body, not a region.

## 4. Derived events (open question 2, draft answer)

Path-fragment events are derived, not authored. For every declared region
and every task with a collision body model, the timeline verifier computes
the sampled phases where any moving body touches the region (within declared
thickness) and exposes:

- `<task>.occupies_region.<region_id>` -- a window event: each maximal
  contiguous run of occupied samples as `[start_deg, end_deg]`; windows may
  wrap through zero; several windows per cycle are normal.
- `<task>.enters_region.<region_id>` and `<task>.exits_region.<region_id>`
  -- point events at window boundaries (sampled: the first and last in-window
  sample of each run).

So `transfer.enters_region.north` is expressible once `north` is a declared
region: authored event ids stay `task.event`, and the region layer supplies
the path-fragment vocabulary.

### Resolution (review, 2026-10-14): no authored path-fragment events

Derived events are the sole source of boundary timing. The id segments
`occupies_region`, `enters_region`, and `exits_region` are reserved for
the derived namespace: authored event ids keep the `task.event` shape, and
G2 validation rejects an authored event id that uses a reserved segment,
fail-closed. Authored timing intent over a derived boundary is an ordinary
relation with no new vocabulary: bounds on a boundary point are `ordering`
leads against another event, window containment is `contains`, and
keep-out is `disjoint_windows` (section 5).

```yaml
relations:
  - id: transfer_enters_within_pick_lead
    from: transfer.pick.reached
    to: transfer.enters_region.north
    type: ordering
    min_lead: {phase: 30}
    max_lead: {phase: 60}
    mode: hard
```

An authored boundary time would either be trusted over the computed one --
the document drifts from what the mechanism actually does -- or be checked
against it, at which point it is a relation, not an event. Authoring stays
for semantics (handoffs, payloads, design intent); geometry timing stays
derived.

## 5. Sweep windows (open question 3, draft answer)

A sweep window is an `occupies_region` window of a body in a region two
mechanisms share. Collision timing uses the existing relation types, with no
new vocabulary: a `disjoint_windows` relation between two tasks'
`occupies_region` windows is the temporal keep-out.

```yaml
relations:
  - id: gate_catcher_keepout
    from: gate.occupies_region.shared_zone
    to: catcher.occupies_region.shared_zone
    type: disjoint_windows
    clearance: {phase: 10}
    mode: hard
```

With multiple windows per cycle the relation must hold for every window
pair: every window of `from` must sit at least `clearance` from every
window of `to`, circularly.

## 6. Verdict semantics and sampling honesty

- Derived-window relations are ordinary relations: hard mode gates the
  composed verdict, soft mode reports only. Undefined assembly at any sampled
  phase is an error, never a quiet pass -- occupancy is never guessed.
- The v0.1 per-task `path_constraints.keep_out_box` stays rejected by the
  adapter in this round. Mapping static obstacle boxes to regions, and
  engine-side search-time screening, are future work, taken up only if
  post-hoc evidence shows search could have avoided real failures.
- Every artifact that reports occupancy records `method:
  sampled_collision_geometry_v1`, the step count, the declared thickness
  and bodies, and the disclaimer: sampled, not certified; no between-sample
  guarantee; not collision, thickness or machinery certification.

## 7. Staging (no new solver physics at any stage)

1. **G1 (landed):** spec text plus the pure-stdlib geometry kernel
   (`omts/geometry.py`): candidate parameters to per-phase world
   positions, region occupancy and window extraction, parity-tested against
   the engine's independent NumPy panel screening.
2. **G2 (landed):** document validation: regions and collision bodies,
   semantic checks, reserved id segments, fail-closed rejection of
   undeclared references and of region events on tasks without collision
   bodies. From G3 the adapter records collision features in the plan's
   line section for post-hoc occupancy computation.
3. **G3 (landed):** the kernel reads candidate geometry from run
   manifests; derived windows are computed per selected candidate and
   reported as data in `line_result.json` (raw and composed windows,
   never gating the verdict).
4. **G4 (landed):** the composed timeline artifact promised by section 8 of
   `synchronization.md`: `omts timeline <plan-dir> [--steps N]` writes
   `timeline.json` -- per sampled master phase, each participating task's
   input phase and body poses per selected candidate -- the collision and
   animation substrate. Composition follows the verifier's anchoring and
   applied-offset rule; the artifact is data-only and never gates the
   verdict, and undefined assembly at a sampled phase is an error, never a
   guessed pose.
5. **G5:** line verification integration: derived windows feed events and
   relations; `disjoint_windows` gates; corpus rerun on the synchronized
   pair sharing one zone.

## 8. Open questions of this draft

1. **Resolved (G3):** both window events and enter/exit point events are
   computed for every declared region and modeled task; boundaries are
   sampled phases, not certified instants.
2. **Resolved (G3):** the schema default is 720 samples (0.5 deg); cost
   scales with candidates, regions, and tasks, not with the number of
   candidate combinations.
3. Should the carrier default be undeclared (centerlines only) in the first
   examples? (Proposed: yes.)
4. Does `path_constraints.keep_out_box` map to regions in a later adapter
   round, or stay a separate per-task feature?
