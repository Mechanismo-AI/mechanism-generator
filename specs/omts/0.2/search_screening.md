# OMTS v0.2 Search-Time Zone Screening (Draft)

> **Draft 0.2.0-search-screening.** This document specifies the
> search-time zone screening vocabulary motivated by the G5 capstone
> evidence: post-hoc gating rejects structurally conflicting lines but
> cannot repair them, clearance tuning and phasing are both dead, and
> the remaining lever is shaping the candidate pools the search draws
> from. It is a specification draft for public review. Z1, Z2, and Z3
> have landed: the vocabulary is declared, validated, and honored by
> the engine, which screens every candidate at qualification time
> when a task declares a screen; the screened capstone example, the
> corpus job with its frozen prediction scorecard, and the corpus
> driver support are on main; and the run itself has been executed
> maintainer-local and read against the frozen scorecard, with the
> outcome recorded as data in section 6.

**Status:** Draft; Z1 and Z2 of the staged plan in section 6 have landed
(spec text, schema vocabulary, semantic validation, the kernel width
metric pinned by tests, the engine-side NumPy screen parity-tested
against the kernel, the adapter `zone_screen.json` sidecar with a runner
flag, and the adapter rejection lifted). Z3 (capstone rerun on new
engine runs) is run-recorded: the job and its prediction scorecard
were written before the run, the run was executed maintainer-local on
fresh engine runs, and its outcome is recorded as data (general
properties in this spec; the concrete readings live in the job file).

**Depends on:** OMTS v0.1 (`specs/omts/0.1/specification.md`), OMTS v0.2
synchronization (`synchronization.md`), OMTS v0.2 collision geometry
(`collision.md`).

## 1. Purpose and scope

Per-task search-time criteria over the sampled occupancy windows a
candidate mechanism produces against a declared region. The goal is to
keep structurally conflicting candidates out of the candidate pools
before line composition, instead of rejecting composed lines after the
fact. In scope: criteria computable from the G1 occupancy kernel
(`omts/geometry.py`), declared per task under
`requirements.collision.screen`. Out of scope: certified (non-sampled)
reasoning, moving regions, new solver physics, and any gating of the
composed line verdict -- the screen shapes search, it never replaces
verification.

The evidence grounding this draft is recorded in `collision.md` section
6 and the capstone jobs (`jobs/sync-corpus-05`, `jobs/sync-corpus-06`):
region-blind candidate sets have structurally wide shared-zone occupancy
windows, post-hoc keep-out gating flips variants whose authored
constraints all pass, and the anchor probe finds no offset for either
anchor that admits a passing combination in those variants.

## 2. Declaration

Screens are declared per task, nested under that task's collision
requirement. Each entry names one declared region and at least one
criterion:

```yaml
requirements:
  collision:
    bodies:
      links: {thickness: 0.5}
    screen:
      - region: shared_zone        # required; must be a declared region
        max_total_width: {phase: 30}  # phase-quantified only; [0, 360]
        max_windows: 2            # integer >= 0
        mode: hard                 # hard | soft | report_only
      - region: approach
        avoid: true
```

Schema notes: `region` is required and must reference an id declared
under `regions`; `avoid` is a boolean; `max_total_width` is a
phase-quantified value; `max_windows` is a nonnegative integer; `mode`
is the standard `constraintMode` enum. A region may be screened at most
once per task. A screen entry with no criterion is a validation error,
not a pass.

Semantic checks (fail-closed, mirroring the G2 rules): unknown region
references are rejected; duplicate per-task region screens are
rejected; `max_total_width` must be phase-quantified -- time-quantified
bounds depend on the task period and are rejected in this draft; the
phase value must lie in [0, 360]; v0.1 documents must not declare
screens.

## 3. Criteria semantics

- `avoid: true` -- the candidate must produce no occupancy window
  against the region.
- `max_total_width` -- the sum of the candidate's window widths against
  the region must not exceed the bound. Width is measured exactly as
  the kernel measures it: each window spans the sampled phases from
  `start_deg` to `end_deg` inclusive, so its width is one sample step
  wider than the bare gap, taken modulo 360 so windows wrapping through
  zero measure correctly, and full occupancy is exactly 360. The helper
  pair `omts/geometry.py: window_width(window, steps)` and
  `occupancy_summary(windows, steps)` pins this definition; the engine
  screen (Z2) must be parity-tested against it.
- `max_windows` -- the number of occupancy windows against the region
  must not exceed the bound.

Two properties make per-candidate screening sound before line
composition:

1. **Offset invariance.** The criteria are arc-width and count
   quantities; applying a line offset rotates a task's windows along
   with its phases and does not change any width or count. A candidate
   that passes a screen passes it under every offset, so screening at
   qualification time is not later undone by offset selection.
2. **Per-candidate computability.** Every criterion is a function of
   one candidate's occupancy against one region -- the same sampling
   the G1 kernel already computes -- so no cross-task or composed
   quantity is needed at qualification time.

Undefined assembly at any sampled phase is an error, never a quiet
pass, exactly as in the kernel and the verifier.

## 4. Mode semantics

- `hard` (default): a failing candidate is excluded from
  `selection_eligible` -- a search requirement in the same sense as the
  selection floor, never a verdict on the composed line. Metrics for
  rejected candidates are recorded as data.
- `soft`: the screen computes and records metrics only; failing
  candidates stay eligible.
- `report_only`: the screen records a summary without binding. Soft and
  report_only exist to gather evidence before hardening a criterion.

If no candidate passes a hard screen, that is honest data: the search
reports zero eligible candidates (`no_candidates`) rather than relaxing
the screen or falling back to the unscreened pool. The screen never
widens the search; fail-closed only.

One asymmetry is deliberate and recorded: the stdlib kernel raises an
error on undefined assembly at a sampled phase, while the engine screen
fails the candidate (`zone_screen_geometry_valid` and
`zone_screen_acceptable` both false, no windows recorded). The verifier
keeps erroring on undefined assembly because it inspects recorded lines;
the engine screen cannot defer a decision per candidate, so it fails
closed. Occupancy is never guessed on either side.

## 5. Honesty

A screen pass is not a collision-free claim. The screen is sampled
occupancy against declared regions by the same method as G1-G5; the
composed verdict is gated only by the relations the verifier evaluates
(the G5 rule), never by a screen. Every artifact that reports screen
metrics records `method: sampled_collision_geometry_v1`, the step
count, the declared thickness and bodies, and the disclaimer: sampled,
not certified; no between-sample guarantee; not collision, thickness or
machinery certification. From Z2 the engine records the per-candidate
screen metrics (window counts, total widths, per-region acceptability,
window boundaries) in the candidate JSON/CSV exports and npz archives,
and the adapter writes the screen it applied to a per-task
`zone_screen.json` sidecar next to the targets file.

## 6. Staging (no new solver physics at any stage)

1. **Z1 (landed, this draft):** spec text, the schema vocabulary
   (`zoneScreen`), semantic validation, and fail-closed adapter
   rejection -- documents that declare a screen are rejected until the
   engine honors them, so the vocabulary cannot silently pass. The
   kernel width metric (`window_width`, `occupancy_summary`) lands with
   tests pinning its semantics.
2. **Z2 (landed):** the engine screen: occupancy computed per candidate
   at qualification time by the existing NumPy pipeline
   (`engine/zone_screen.py`, sampled at 360*i/steps like the kernel),
   parity-tested against the stdlib kernel (the G1 pattern); the adapter
   normalizes screen entries, writes a per-task `zone_screen.json`
   sidecar and a runner `--zone_screen` flag; the Z1 adapter rejection
   is lifted. Hard screens exclude failing candidates from
   `selection_eligible` (qualification level
   `path_acceptable_but_zone_screen_failed`); soft and report_only
   entries record data only. Undefined assembly fails the candidate
   (section 4). Per-candidate metrics are recorded in the candidate
   exports.
3. **Z3 (landed, run recorded):** capstone rerun as
   `jobs/sync-corpus-07`:
   `examples/omts/collision_pair_screened.omts.yaml` (the G5 pair with
   a hard `max_total_width {phase: 60}` screen on the shared zone for
   both tasks), the corpus driver passing the adapter's per-task sidecar
   to the engine (`--zone_screen`, exactly as the generated runner
   does), and a fail-closed driver refusal of `--results-from` for
   screened documents (screening changes selection, so prior
   region-blind trees were not produced under the screen and are never
   reused across that boundary). The prediction scorecard in the job
   file was written before the run; NEW engine runs only; the run has
   been executed maintainer-local and its outcome is recorded as data
   in the job file. Measured against the frozen scorecard: the identity
   variant verified with more passing combinations than the
   region-blind baseline (the screen admitted gate candidates the
   region-blind search had out-ranked -- pool shaping improved the
   line, not merely preserved it); among the flipped variants, some
   tasks reported honest zero-eligible pools (every qualified
   candidate over the cap), extending the structural reading from the
   selected sets to the full pools, while one variant's pools
   narrowed, survived the screen, and still composed no passing
   combination (narrowing without repair); the upstream-zero variant
   and the negative control were unchanged, and the screen never gated
   a verdict. Whether offsets can re-time the new pools is a
   follow-up probe question, not claimed here.

## 7. Open questions of this draft

1. Should hard screens also rank among passing candidates (a preference
   order), or only exclude failing ones? The capstone evidence only
   motivates exclusion; ranking is unclaimed.
2. Is a per-window width bound needed in addition to `max_total_width`,
   or does total width plus window count cover the observed conflict
   shapes? Unclaimed until a corpus shows otherwise.
3. Should `omts propose-offsets` eventually compose derived relations
   for screened lines, or does screening make the hand-declared-offset
   rule permanent? Unclaimed; the G5 fail-closed rule stands until
   screened-line re-time evidence exists.
