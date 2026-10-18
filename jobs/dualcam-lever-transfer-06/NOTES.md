
# dualcam-lever-transfer-06 -- reconstruction stash (WIP branch)

## What this branch is

The staging environment (the local working sandbox) died mid-turn
on 2026-10-18 while staging job dualcam-lever-transfer-06; the
local working copy of the design script may or may not have
survived. This branch is the durable stash: the script is stored
here in seven parts, .part1.txt through .part7.txt, to be
concatenated into dualcam_lever_design.py and verified before
anything else happens.

IMPORTANT: parts 1 and 2 were pushed byte-exact from the verified
local copy before the failure. Parts 3-7 were RE-AUTHORED from the
recorded turn notes after the failure. If the local copy
survived, it is authoritative: diff it against this branch
reconstruction and reconcile any difference explicitly -- never
silently edit either. If it did not survive, this branch is the
only copy and it MUST be re-verified by running it before
staging.

## Assembly

    for f in .part1.txt .part2.txt .part3.txt .part4.txt \
             .part5.txt .part6.txt .part7.txt; do
        cat "$f"; echo
    done > dualcam_lever_design.py
    python3 dualcam_lever_design.py   # from the repo root
    # run twice, compare stdout byte-for-byte (G5)
    # then delete the .partN.txt files from this branch

The frozen task input is jobs/sixbar-gap-transfer-02/
gap_transfer_nostops.motion.json (sha256 591a562c33b7455476e2055
9fdd16f46bb0c1a3c4645d4a25048e4607e3a24d5), consumed read-only.

## What was verified before the environment failure

The final script revision ran once end-to-end (exit 0) with this
reading, all of which the reassembled script must reproduce:

- G1 task validation HELD (same tolerances as -05).
- Cam y carry: all six printed readings MATCH the -05 record
  (25.8817 deg at 332 deg; 246.098 mm; 174.262 mm; 98.3361 mm;
  695.99 mm/rad^2).
- Swing scan: the 30.0 deg first cut INFEASIBLE (the extreme-creep
  asymptote EQUALS the swing, approached from above); declared
  design point phi_max = 25.0 deg, b = 307.606 mm.
- Pivot: L/a infimum 3.02242, quantized pick 3.1; worst pressure
  angle 29.8008 deg at 109.4 deg (margin 0.199244 deg,
  boundary-tight by the minimal-offset pick, disclosed).
- r/a = 3.52262; lambda window [3.80203, 33.0199] (cap /
  curvature); pick 3.85 giving a = 79.8977 mm, L = 247.683 mm,
  e = -72.4119 mm, r_max = 281.449 mm (headroom 3.55 mm); band
  point 4.25 (r_max 254.96 mm); min positive rho 160.811 mm vs
  the 18.75 mm gate.
- G2 cam x HELD; cam y carried HELD; G3 stop velocities at the
  slide 0/0 (exact); contacts 15/15 mm; normal cross-check dev
  ~6e-12 deg; curvature cross-validation ~1.1e-14; in-process
  two-audit determinism PASS.
- Envelope: EXCEEDS (742.683 x 705.018 mm), with the per-
  dimension rows and the plan-view-union caveat, for the brief
  owner, not a gate.
- Junction rows: boundary alphas 25.00 deg at the swing extremes;
  peak a|phi''| 232.966 at 120 deg; a phi'^2 26.4308 at 96.8 deg;
  combined shaft-torque 53267.1 at 109.9 deg.

The second PROCESS-level run never completed: the worker died
mid-run. Process-level byte identity follows by construction
(no time, no randomness), and the the-hub machine run re-confirms
G5. The JOB staging disclosure must say exactly this.

## Bugs found and fixed at staging (record before they are lost)

1. cam_y_contact profile offset had the wrong-sense normal
   ((-hp, r) instead of (hp, -r) for the CCW convention): a
   mirrored curve cutting into the roller, far-field minimum
   9.0383 mm vs the 15 mm roller. Fixed; local and far-field both
   exactly 15 mm after.
2. report["lever"] never set "feasible" in the feasible branch,
   so main()'s fail-closed lever_ok gate silently never
   evaluated. Fixed; the final run exits 0 with the gate genuinely
   running.
3. Carry-precision finding: the -05 JOB.md outcome text
   transcribed the cam-y 45-deg-gate major radius as "174.26";
   the stdout-verbatim -05 reading is 174.262. The -06 record
   carries 174.262 with an explanatory note.

## Pending steps (in order)

1. Assemble and verify per above; delete the .partN.txt files
   from this branch once the assembled script is verified.
2. Write jobs/dualcam-lever-transfer-06/JOB.md (pattern of the
   -05 JOB): purpose, succession context, the frozen -02 task
   consumed read-only, cap derivation, the phi_max refutation
   disclosure + scan + the declared 25.0 deg design point (a
   declared design decision, open to Jean's review), the staging
   disclosure with the honest determinism wording, the staging
   smoke-test reading, Steps, the prediction scorecard frozen
   BEFORE the the-hub run ([staging: ...] brackets), the
   pre-declared terminal branch, open questions, decision rule
   (G2 HELD -> machine run -> Jean's merge decision; the
   envelope exceedance returns to the brief level).
3. Update jobs/README.md (-06 row: staged, run pending).
4. Open the staging PR (base main). PR #55 was the -05 outcome.
5. the-hub machine run, outcome record PR, STATE.md continuity
   entry, knowledge updates, per the usual governance.
