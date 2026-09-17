# Diagnosis: a candidate within the original tolerances

**A private tolerance-aware geometric search found one candidate that meets the
original hard kinematic requirements and sampled panel screen.** The released
v0.1.0a6 search result remains unchanged: zero eligible candidates from its
original run. No engine code or model weights were changed for this investigation.

The new candidate was independently checked in millimetres, accepted by the
released engine's candidate evaluator, and screened over 72,001 input phases.
It is a kinematic research result, not a validated hardware design.

## What was blocking progress?

The released geometric initializer constructs mechanisms through the exact
nominal orientations, even when the task allows angular tolerances. The regular
optimizer already checks those tolerances; the limitation identified here is in
the geometric starting-point search.

Reproducing 65,536 original exact-pose samples gave 38,453 finite in-bounds
geometries. None permitted a full input turn, even before adding robustness
margins. Individually, 6,899 met Grashof's condition and 15,361 had a strictly
shortest input link, but no sample passed all these requirements together.
Removing one of the three combined screening gates, or removing all extra
robustness margins, did not produce a qualifying exact-pose seed. Independent
geometry verified 64 representative candidates at all three poses.

This isolates a failure in the sampled exact-pose search. It does not prove
that every exact-pose mechanism, including geometries outside these bounds, fails.

## Controlled comparisons

The plans were saved before their corresponding runs. Each initial comparison
used 65,536 deterministic samples. The same underlying sequence was reused;
these are controlled development experiments, not independent statistical trials.
The original positions, angle limits and panel remain the acceptance reference.

| Search change | Candidates passing full-turn motion filters, either direction | Passing original panel screen |
|---|---:|---:|
| Original exact nominal angles | 0 | 0 |
| Sample angles inside the existing ±3° tolerances | 59 | 0 |
| Carrier on opposite side of coupler | 0 | 0 |
| Attachment extended before joint A | 0 | 0 |
| Attachment extended beyond joint B | 0 | 0 |
| Same tolerance-aware search, increased to 262,144 samples | 230 | **1** |

Attachment changes expand the released parameter representation; they do not
change the external pose targets. All full-turn survivors in this comparison
used negative crank rotation. After the fixed-pivot clearance check, only two
candidates remained in the 65,536-sample tolerance run, and seven in the denser
run. All those remaining candidates were panel-screened. The first pair extended
5.740 and 3.977 mm below the panel, motivating the recorded density increase.
The denser sequence includes the earlier samples and uses four times that budget.

A separately labelled **relaxed** comparison allowed a limited working arc and
a reversing return, dropping the full-turn and rotating-crank class requirements.
It yielded 23,206 candidates passing working-arc checks, 640 also passing fixed
pivot clearance. All 128 candidates selected for panel screening passed. They
reach the exact nominal poses, but are not solutions to the original full-turn
brief. No claim is made that all 640 pass the panel screen.

## Original-brief candidate

Deterministic sample 208725, negative input rotation, branch −1:

| Measurement | Result | Hard requirement |
|---|---:|---:|
| Mean / maximum position error | Numerically zero; below 10⁻⁸ mm | ≤1 / ≤1.5 mm |
| Pickup angle | −7.298899° | −10° ±3° |
| Raised-midpoint angle | −2.958494° | 0° ±3° |
| Placement angle | +11.616338° | +10° ±3° |
| Minimum target transmission angle | 20.593° | ≥15° |
| Analytic minimum full-cycle transmission angle | 13.471° | ≥10° |
| Sampled envelope x | 19.124…389.053 mm | 0…400 mm |
| Sampled envelope y | 0.913…146.352 mm | 0…300 mm |
| Minimum fixed-pivot edge clearance | 16.885 mm | ≥10 mm |

Analytic full-cycle assembly and mechanism-class checks pass. Target order is
retained on one branch. The released evaluator reports `selection_eligible=true`
and `pose_acceptable=true`. It reports `engineering_acceptable=false` because the
preferred 35° target and 15° global transmission goals are not achieved; those
were soft preferences, not the hard 15°/10° selection floors.

There is only **0.913 mm sampled panel clearance** and **0.0415° remaining tilt
margin** at the tightest target. Real links have thickness and manufacturing
variation. Collisions, bearings, loads, dynamics and manufacturing tolerances
have not been checked. The panel screen samples 72,001 phases; it is not a proof
of continuous containment between samples. These limitations matter before any
physical implementation.

Exact dimensions, input phases and achieved poses are in
[successful-candidate.json](diagnosis/successful-candidate.json). The independent
and released-engine checks are in [verified-witness.json](diagnosis/verified-witness.json).
The baseline [assessment](assessment.json) has not been replaced or reclassified.

## Reproduce

From the source checkout with the engine dependencies installed:

```sh
python tools/diagnose_tabletop_transfer.py --output-dir generated/tabletop-diagnosis
```

The command reproduces the constraint breakdown, controlled comparisons and
denser tolerance-aware search using frozen settings. It refuses an existing
output directory. It runs local numerical geometry, without downloading weights,
training models, or uploading results. Published engine defaults remain unchanged.
Plans, complete counts and screened candidates are retained under [diagnosis/](diagnosis/).

## Smallest justified next improvement

**Implementation update:** this step is released in v0.1.0a7; see the [integration guide and measured results](../../docs/tolerance-and-panel.md).
The following paragraphs describe the conclusion of the original diagnostic
experiment, whose settings and evidence remain frozen.

Extend geometric initialization to sample inside requested orientation
tolerances while retaining the original nominal-target samples. Include panel
constraints in candidate screening and selection when the task specifies them.
This witness required a larger research budget and evaluation of survivors that
the current six-seed ranking would not necessarily retain. A production change
therefore needs bounded budgets, clear provenance, and checks on additional
frozen tasks before claiming a general improvement.

There is no evidence here that new weights are needed. The controlled experiment
establishes a concrete search improvement worth implementing and a verified
candidate for further refinement, with the original brief intact.
