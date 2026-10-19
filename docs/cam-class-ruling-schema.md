# The cam class ruling: frozen answer schema (v1.0)

The B2 pattern applied to a class question: the answer schema commits
BEFORE the ruling runs. The ruling is a desk analysis -- free, no
machine step, no instrument touched, no recorded row rewritten.

## The frozen question

For positive-drive cams (a captured two-flank groove pin), is the
fixed-frame pressure-angle class gate -- 45 deg, the gate the
flip-station-capability-01 scorecard applied -- the right class gate
for this family, or does the family's binding transmission channel
differ (friction/efficiency at the pin), requiring a re-derived gate?

The fence (the debate's acceptance test): the ruling must be
derivable from family physics WITHOUT reference to the failed
design's numbers -- "would this ruling have been made at freeze time
if the architecture mismatch had been noticed then?" The derivation
may not use any number from the recorded capability outcome; the
recorded design enters only afterward, as the object the computed
gate is applied to.

## The answer enum (closed, v1.0)

- re-rule -- the family's class gate is re-derived on the
  friction/efficiency channel; a new frozen scorecard row applies
  PROSPECTIVELY; the recorded outcome keeps its meaning ("failed the
  class gate as then defined"); never a waiver.
- decline -- the fixed-frame pressure-angle gate stands for this
  family; the cam line's wide-fail is final for this case study.
- inconclusive -- the committed inputs cannot carry a ruling; the
  question returns with the named missing input.

## The committed-inputs rule (the round's arithmetic catch, adopted)

The gate value is the derivation's OUTPUT, never an input. The
ruling commits, FIRST and with lineage each (a tribology reference
or a declared assumption):

- mu, the lubricated-steel pin friction coefficient;
- SF, the friction safety factor (usable-tangential-to-friction
  force ratio).

Then the gate falls out as arithmetic:

- Motion requires cos(alpha) > mu*sin(alpha): self-lock at
  alpha = 90 deg - arctan(mu).
- With the safety factor: tan(alpha) <= 1/(SF*mu).
- Transmission efficiency is reported as data (loss fraction per
  the same derivation), never gated.

Fold-time cross-check, recorded as data: the debate quoted a
"~55-60 deg" re-ruled gate, and the critic caught that it does not
fall out of the actor's declared inputs (mu 0.10-0.15 lubricated
steel, SF 2): tan(alpha) <= 1/(2*mu) computes to 78.69 deg at
mu = 0.10 and 73.30 deg at mu = 0.15. The 55-60 deg figure matches
dry friction (mu ~ 0.3) or a much larger safety factor -- neither
matches the stated premise. The catch is the reason this rule
exists. It also implies, at the checked inputs, that the recorded
design's worst angles (89.070/89.314 deg, cited from the
flip-station-capability-01 record as INPUT here, never as a
derivation input) exceed the honest re-derived gate -- the honest
re-rule does not rescue the recorded design. The ruling still
computes pass/fail with its own committed inputs, publicly.

## What the answer owes (all fields mandatory)

1. ruling: one of the closed enum.
2. committed_inputs: mu and SF, each with lineage.
3. derivation: the arithmetic shown, from the committed inputs to
   the gate value; no number from the recorded design appears in
   it.
4. gate_value_deg: the output, with the self-lock boundary reported
   alongside.
5. recorded_design_passfail: the recorded design's worst pressure
   angles (from the flip-station-capability-01 record) applied to
   the computed gate, computed publicly.
6. efficiency_rows: loss-fraction data over the recorded sweep.
7. fence_attestation: a stated check that the derivation used no
   number from the failed design.
8. consequence: prospective-only; the recorded outcome is never
   rewritten; the re-stage decision (whether the cam line re-stages
   as a new study under the new gate) is the owner's explicit
   strategy decision, never automatic, with both studies' lineages
   visible.
9. schema_version: 1.0; additive changes only (a meaning change
   would be 2.0, the frozen succession rule).

## Boundary

Contact stress and pin bending are rated-force questions: they stay
behind the existing rated-force/payload trigger. The ruling does
not smuggle a stress gate it cannot derive.

## Status

Schema committed (v1.0); the ruling has not run. It may run as a
desk round in parallel with the six-bar line; neither waits on the
other.
