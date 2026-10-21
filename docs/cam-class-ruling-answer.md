# The cam class ruling: recorded (2026-10-21) -- re-rule at the committed inputs

Status: **The ruling is RECORDED in the frozen answer schema's nine
mandatory fields (docs/cam-class-ruling-schema.md, v1.0, committed with
PR #75). This file is the desk record.** Per the strategy fold
(continuity STATE-VOL-2.md entry85) the ruling runs as the parallel
desk round it was frozen to be. It is a desk analysis -- free, no
machine step, no instrument touched, no recorded row rewritten; the
recorded outcome is data and keeps its meaning.

## The frozen question (verbatim)

For positive-drive cams (a captured two-flank groove pin), is the
fixed-frame pressure-angle class gate -- 45 deg, the gate the
flip-station-capability-01 scorecard applied -- the right class gate
for this family, or does the family's binding transmission channel
differ (friction/efficiency at the pin), requiring a re-derived gate?

## The fence (verbatim)

The ruling must be derivable from family physics WITHOUT reference to
the failed design's numbers -- "would this ruling have been made at
freeze time if the architecture mismatch had been noticed then?" The
derivation may not use any number from the recorded capability
outcome; the recorded design enters only afterward, as the object the
computed gate is applied to. Attested in field 7.

## Field 1: ruling

**re-rule** -- exactly one value from the closed enum: the family's
class gate is re-derived on the friction/efficiency channel; a new
frozen scorecard row applies PROSPECTIVELY; the recorded outcome
keeps its meaning ("failed the class gate as then defined"); never a
waiver.

The reasoning in brief, from family physics only: for a captured
two-flank groove pin the drive is maintained through the dead points
by the constraint set (the family's own defining feature, recorded at
the capability staging: the structural dead-point bands "passed
through by the positive-drive constraint set"); the binding limit at
the pin is friction self-lock, quantified through the pressure angle
by the schema's frozen arithmetic; the 45 deg fixed-frame precedent
was the force-class cam gate (the -05 re-derived precedent value
carried to the scorecard), not a derivation from the groove pin's
friction physics. The derivation below computes the honest gate at the
committed inputs; the recorded design's angles are applied to it only
afterward, as the object.

## Field 2: committed_inputs

- mu = 0.10-0.15, the lubricated-steel pin friction coefficient.
  Lineage: a declared assumption, the fold-time debate's stated
  premise, carried by the schema's own fold-time cross-check
  unchanged ("mu 0.10-0.15 lubricated steel"); committed per the
  schema's rule (first, with lineage), not re-derived at this desk.
- SF = 2, the friction safety factor (usable-tangential-to-friction
  force ratio). Lineage: the fold-time debate's declared premise,
  carried by the schema's cross-check unchanged.

## Field 3: derivation

The schema's frozen arithmetic, executed with the committed inputs.
No number from the recorded design appears anywhere in this
derivation.

- Motion requires cos(alpha) > mu*sin(alpha): self-lock at
  alpha = 90 deg - arctan(mu).
  At mu = 0.10: arctan(0.10) = 5.710593 deg -> self-lock at
  84.289407 deg.
  At mu = 0.15: arctan(0.15) = 8.530766 deg -> self-lock at
  81.469234 deg.
- With the safety factor: tan(alpha) <= 1/(SF*mu).
  At mu = 0.10, SF 2: tan(alpha) <= 5.000000 -> alpha <= 78.690068
  deg.
  At mu = 0.15, SF 2: tan(alpha) <= 3.333333 -> alpha <= 73.300756
  deg.
- The gate holds across the committed mu range, so the binding
  (design-facing) gate is the tighter end: 73.300756 deg at
  mu = 0.15; the looser end, 78.690068 deg at mu = 0.10, reported
  alongside.
- Transmission efficiency is reported as data (field 6), never gated.

## Field 4: gate_value_deg

- Gate: 73.300756 deg at mu = 0.15, SF 2 (the binding end);
  78.690068 deg at mu = 0.10, SF 2 (the looser end).
- Self-lock boundary alongside: 81.469234 deg (mu = 0.15) and
  84.289407 deg (mu = 0.10).
- The gate's own meaning at the committed inputs: tan(alpha) =
  1/(SF*mu) is exactly mu*tan(alpha) = 1/SF = 0.500 -- the gate is
  the 50 percent loss-fraction boundary; the safety factor and the
  gate are the same statement (field 6).

## Field 5: recorded_design_passfail

The recorded design's worst pressure angles, cited from the
flip-station-capability-01 record as INPUT (the recorded outcome
section, on main): 89.070 deg (groove_1, t = 92.30) and 89.314 deg
(groove_2, t = 89.25) over the loaded carry arc; the sweep's a_G1
range 89.192-90.000 deg; the dead-point alpha exactly 90.000 deg
(the dead-point bands excluded per the recorded gate definition).
Applied to the computed gate, publicly:

- 89.070 deg > 78.690068 deg (the looser committed gate) and >
  73.300756 deg (the binding gate): FAIL at both committed inputs,
  by 10.379932 deg over the looser gate.
- 89.314 deg FAIL likewise (15.623932 deg over the looser gate).
- Both worst angles also exceed both self-lock boundaries
  (84.289407 / 81.469234 deg): the recorded loaded arc's worst
  samples run past the friction channel's self-lock boundary at both
  grooves.

READ, recorded as data: the honest re-rule does NOT rescue the
recorded design -- the schema's fold-time cross-check implication,
now computed publicly as this ruling's own output. The recorded
outcome keeps its meaning, "failed the class gate as then defined"
(the 45 deg fixed-frame gate); it now additionally reads as failing
the re-derived gate.

## Field 6: efficiency_rows

Loss fraction per the same derivation: loss = mu*tan(alpha) -- the
friction share of the driving component (self-lock at loss = 1; the
SF-2 gate at loss = 0.500). Computed over the recorded sweep's values
carried on main; the full per-phase sweep table is corpus-side
(maintainer-local under runs/flip-station-capability-01/, referenced
by the recorded hashes cdac1413.../4edb232c...), and the rows below
are computed at the angles the record carries on main:

| recorded angle (source) | loss at mu = 0.10 | loss at mu = 0.15 |
| --- | --- | --- |
| 89.070 deg (groove_1 worst, loaded arc) | 6.160 | 9.240 |
| 89.192 deg (sweep a_G1 low end) | 7.091 | 10.636 |
| 89.314 deg (groove_2 worst, loaded arc) | 8.352 | 12.528 |
| 90.000 deg (dead points, excluded bands) | unbounded | unbounded |
| 78.690068 deg (the gate, mu = 0.10) | 0.500 (the gate) | 0.750 |
| 73.300756 deg (the gate, mu = 0.15) | 0.333 | 0.500 (the gate) |
| 45.000 deg (the as-then-defined gate) | 0.100 | 0.150 |

Readings, recorded as data: every loaded-arc angle the record carries
sits deep past loss = 1 (self-lock) -- the recorded loaded arc is
carried by the positive-drive constraint set (the two-flank capture),
not by friction-feasible transmission. The as-then-defined 45 deg
gate sits at loss 0.10-0.15 (mu*tan(45 deg) = mu): the old gate was a
10-15 percent loss bound, the SF-2 commitment allows 50 percent --
the re-derived gate is looser by construction, exactly as the
fold-time cross-check recorded.

## Field 7: fence_attestation

Stated check: the derivation (field 3) uses only the committed inputs
mu and SF and trigonometry; no number from the recorded capability
outcome appears in it; the recorded design's numbers enter only in
fields 5 and 6, as the object the computed gate is applied to. The
acceptance test: would this ruling have been made at freeze time if
the architecture mismatch had been noticed then? YES -- every input
and equation was frozen in the schema at commit time; this record
adds only the execution.

## Field 8: consequence

Prospective-only; the recorded outcome is never rewritten. The
dual-groove plate-cam record keeps its meaning and now additionally
reads against the re-derived gate (field 5). A new frozen scorecard
row for the positive-drive groove-cam family applies PROSPECTIVELY at
any future staging: pressure angle <= 73.300756 deg at the committed
inputs (mu 0.10-0.15, SF 2), the self-lock boundary reported
alongside, efficiency as data. The re-stage decision -- whether the
cam line re-stages as a new study under the new gate -- is the
owner's explicit strategy decision, never automatic, with both
studies' lineages visible. The boundary carries: contact stress and
pin bending are rated-force questions and stay behind the existing
rated-force/payload trigger; this ruling smuggles no stress gate it
cannot derive.

## Field 9: schema_version

1.0 -- the answer is staged in the frozen schema's nine mandatory
fields; additive changes only (a meaning change would be 2.0, the
frozen succession rule).

## Trigger bookkeeping

- The six-bar line: already run and recorded (flip-station-sixbar-01,
  the fired trigger's recorded alternative, honest all-fail); case
  study C closed with the flip unsolved. This ruling does not reopen
  C; it makes the cam line ELIGIBLE to re-stage as a new study under
  the new gate -- Jean's explicit call, never automatic.
- The strategy fold's scheduling (entry85): the ruling was scheduled
  as the parallel desk round it was frozen to be; on merge the
  schema's never-ran status closes with this answer recorded in its
  own fields.
- No runs, training, or automation started; no instrument touched;
  the owner executes every run.
