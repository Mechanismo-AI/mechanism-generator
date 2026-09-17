# Tolerance-aware initialization and panel screening

Implemented in **v0.1.0a7**. Published inference weights
are unchanged. This adds local numerical search and qualification, without training.

Pose tasks now retain two separate geometric search branches. The first constructs
the nominal target angles. The second samples angles **inside each requested
angular tolerance**, while still constructing the three requested positions exactly
before numerical encoding. Final evaluation always uses the original targets and
tolerances; sampled angles never replace the task requirements.

Both use deterministic sequences, without changing NumPy or Torch random state.
The geometry coordinates use radical-inverse bases 2, 3 and 5; the additional
angle coordinates use bases 7, 11 and 13. Increasing a sample budget extends the
same sequence. Each branch has its own slots for up to six diverse seeds, and
each parent is retained separately from its refined child. A failed refinement
cannot erase its parent.

## Budgets

| Setting | Default | Allowed range |
|---|---:|---:|
| `--pose_dyad_samples` | 4,096 nominal samples | 0–262,144 |
| `--pose_tolerance_samples` | 65,536 tolerance samples | 0–262,144 |
| `--pose_dyad_seed_count` | 6 per branch | 0–6 |
| `--panel_steps` | 7,201 full-turn phases | 361–72,001 |

Set either sample budget to zero to disable that branch, or the seed count to zero
to disable both. Position-only tasks do not run either pose initializer. The
additional samples and refined children add compute; this is not an equal-compute
comparison with older releases. An `either` direction request runs both complete
budgets independently. No search is exhaustive.

OMTS exposes the same budgets under each task:

```yaml
search:
  implementation_profile: r2.5c-fourbar
  pose_initialization:
    nominal_samples: 4096
    tolerance_samples: 65536
    seeds_per_branch: 6
```

## Optional panel requirement

Supply `--panel_bounds XMIN XMAX YMIN YMAX` together with
`--carrier_size WIDTH HEIGHT`. All distances use the same world units and origin
as the target positions. The rectangle is centred on output point P, and its width
axis follows the directed coupler A-to-B axis. There is no independent mounting
rotation. `--panel_pivot_clearance` defaults to zero and sets the minimum distance
of each fixed pivot from every panel edge.

The OMTS equivalent, using **normalized** world coordinates, is:

```yaml
requirements:
  panel:
    bounds: [-8.333333333333334, 5.0, -1.3333333333333333, 8.666666666666666]
    carrier_size: [1.6666666666666667, 0.3333333333333333]
    pivot_clearance: 0.3333333333333333
    steps: 7201
    carrier_frame: coupler_A_to_B
    mode: hard
```

This maps to the tabletop brief's 400 × 300 mm panel and 50 × 10 mm carrier,
using physical XY = 30 × normalized XY + [250, 40] mm.

Before geometric seeds are truncated, fixed pivots are screened and ranked
survivors are checked over a full crank turn. Sampling stops after enough diverse
passing seeds are retained or the survivors are exhausted. Diagnostics distinguish
the number passing pivot clearance, the number actually screened, and the number
passing the sampled screen. They do not claim every survivor was screened.

Every final candidate, including neural proposals and refined children, is checked
again. `panel_acceptable` requires defined assembly at the sampled phases, both
fixed pivots' clearance, and containment of link endpoints and all four carrier
corners. The panel is convex, so containment of endpoints also contains the
straight, zero-thickness link centrelines. The check uses an independent NumPy
circle-intersection implementation tested against the engine's Torch simulator.

`selection_eligible` and `engineering_acceptable` require the panel gate when it is
specified. Missing or failed screening cannot enter the final selected portfolio.
Position and orientation acceptance retain their existing meanings. A candidate
can satisfy both and still fail panel containment.

**This is sampled containment**, not a guarantee between samples. It does not
check link thickness, bearings, fasteners, self-collision, payload, forces, dynamics
or manufacture. Panel acceptance is a final screen, not a differentiable panel
objective; refinement may leave the panel and be rejected.

## Results and sharing

JSON, CSV and NPZ candidate exports retain panel requirements, screen resolution,
sampled envelope, clearances and acceptance. Run manifests include the panel
configuration and source fingerprint. `proposal_source` distinguishes
`three_pose_dyad_v1` from `three_pose_tolerance_dyad_v1`; aggregate diagnostics use
`three_pose_dyad_v2` when the tolerance branch is enabled and report both budgets.

Contribution schema 0.5 preserves panel outcomes even if optional geometry is
excluded. Task and Candidate sections each retain panel dimensions when included;
the offline review shows those values before sharing. Older 0.1–0.4 bundles remain
readable. Local preparation still performs no uploads.

## Tabletop regression

The [integrated example](../examples/omts/tabletop_transfer_panel.omts.yaml) keeps
the frozen physical brief and uses 262,144 tolerance samples per direction.
The full run produced 38 final candidates: 18 positive-direction and 20 negative.
Two eligible rows describe a parent and its refined child; deduplication selected
**one distinct design**, the preserved tolerance seed. Independent physical
geometry verifies the original position, angular, full-turn and panel limits.
The nominal search still returns no seed for this case.

The selected design's largest angle error is 2.9585° against a 3° limit; sampled
panel clearance is 0.9132 mm. Its minimum target/global transmission angles are
20.593°/13.471°, meeting the 15°/10° hard floors but missing the preferred 35°/15°
goals. Consequently `engineering_acceptable` remains false. These small margins
make dimensional sensitivity and robustness the next design questions.

```sh
omts adapt examples/omts/tabletop_transfer_panel.omts.yaml --output-dir runs/panel
python runs/panel/run_r25c.py --models-directory models
python tools/assess_tabletop_transfer.py --results runs/panel/results --output runs/panel-assessment.json
```

The original [released-engine assessment](../examples/tabletop-transfer/assessment.json)
is preserved. The integrated [assessment](../examples/tabletop-transfer/integration/assessment.json)
records all candidates and engine/model fingerprints. This task is development
data, and this success does not establish a general success-rate gain.

The [eight-case frozen development regression](pose-panel-regression.json) also
completed with qualifying selected designs in **8/8 tasks**, using the default
4,096 + 65,536 sample budgets, the unchanged proposal weights, standard optimizer
budgets and seed 101. All 40 selected designs passed the independent pose check.
This is a regression result on constructed tasks without panel requirements,
not an independent estimate of panel-design success or an equal-compute gain.
The four original analytic pose probes, point-only CLI smoke run, 310 Python
tests (five Windows symlink skips) and offline contribution-review checks passed.

```sh
python tools/pose_corpus.py run --models-directory models --split development --budget standard --initializer-samples 4096 --initializer-seeds 6 --tolerance-samples 65536 --label tolerance-panel-integration --output runs/panel-regression
```
