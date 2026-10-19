# Strategy: framework and generator -- 2026-10-19

## The strategy sentence

The product of this project is generated mechanisms you can trust. The grading
framework -- OMTS demands, frozen scorecards, fail-closed instruments, the
debate loop, and the recorded outcome ledger -- is what makes that trust
possible. Candidate generators, learned or analytic, are suppliers graded
inside the framework; the framework is generator-agnostic by construction.

Two readings of that sentence are settled and worth naming.

First, the record to date: the learned components have been suppliers that
failed out-of-distribution twice (the learned initializer, and the chooser
restarts in the six-bar runs), while analytic synthesis delivered both HELD
gates in the closed case studies. Those are supplier grades, not verdicts on
the modeling line. That is exactly what a framework is for: grading suppliers
honestly while the product claim stays untouched.

Second, "generator" does not mean only the learned line. Analytic synthesis
is a generator too -- currently the winning supplier. Every closed case study
is the strategy sentence cashing out: a recorded, graded mechanism that exists
because a supplier ran inside the framework.

## Generator-agnostic principle (frozen)

Instruments grade candidates through OMTS demands and recorded outcomes,
never through family-specific hooks.

The reciprocity this implies is part of the rule: the framework must not
become generator-hostile by accretion. Every instrument frozen to date was
built around a mechanism family under study; if the instruments only know
how to grade cams and four-bars, generator-agnostic is a claim, not a
property. The admission test is: when a new-family generator stages, the
existing grading instruments must score its proposals with zero instrument
modification. Failing that test is a finding about the instruments, recorded
as such.

## Ordering (amended, 2026-10-19)

The generation frontier has three recorded candidates: (1) learned proposals
over the new families the case studies opened (cam and six-bar parameter
spaces); (2) the generalization diagnosis on the existing four-bar niche
(mounting-angle representation consistency, the recorded live blocker); (3)
the flipper case study as another analytic synthesis line.

The settled ordering:

- The flipper case study runs next. It is designed as the downstream
  consumer of the learned-proposal line: its recorded outcomes must be a
  machine-readable solution corpus -- parameter vectors, demand points,
  solutions, and gate results as data rows, not job prose. Analytic
  characterizations of small, bounded spaces with exact ground truth are the
  ideal regime for a first learned proposer; the flipper's close, success or
  honest analytic failure, manufactures that corpus either way.
- The generalization diagnosis (2) runs in parallel as desk analysis against
  existing recorded data, not new runs. It commits to a frozen answer schema
  before it runs (for example: "the niche is representation-limited, not
  data-limited"), so its trigger condition cannot be satisfied by vague
  prose. It is never left silently standing.
- The learned-proposal line (1) waits for the trigger below, then enters
  through the admission gate below.

Scope honesty, recorded with the ordering: a learned proposer in an
exact-solution space can at best match closed-form. The long-term case for
learned generation lives in regimes analytic synthesis does not reach --
mixed demands, multi-objective tasks, noisy envelopes. The corpus's job is
to make the first step gradeable, never to prove replacement.

## Trigger (frozen)

The mechanism is an explicit owner decision, with a default tripwire so
silence cannot become the decision. The generation investment fires when
both of these hold:

(a) the flipper case study closes -- success or honest analytic failure,
    either way with a machine-readable recorded solution corpus; and
(b) the generalization diagnosis has a recorded answer in its frozen schema,
    even if that answer is "the niche is representation-limited, not
    data-limited."

At that point the "one more case study" argument is spent: there is labeled
data from a second family and a diagnosis of the first. Past the tripwire,
further harvesting is deferral, not evidence-gathering. When the trigger
fires, the next staged item must be the B1 admission-gate work, unless the
owner explicitly overrides with a recorded reason.

## B1 admission gate (frozen minimum)

A first trained cam/six-bar proposal is admissible only if:

1. Zero instrument modification. The proposal is graded by the existing
   instruments unmodified -- the generator-agnostic admission test.
2. Closed-form head-to-head. It is scored against the recorded analytic
   solutions of its family on the same recorded demands; it must beat, or
   honestly lose to, closed-form synthesis, and both numbers go in the
   table.
3. Determinism control. Fixed seeds, declared initialization, byte-identical
   reruns.
4. Supplier-output labeling. The proposal is labeled a supplier output, not
   a generator capability, until it wins a head-to-head.
5. OOD control. The learned component is exercised on the recorded failure
   modes -- a demand outside its training distribution -- with its fallback
   behavior recorded.
6. Initializer head-to-head. It is also compared against the existing
   non-learned initialization on the same seeds; contribution is measured,
   not assumed (the recorded precedent: a learned component can be worse
   than random restart).
7. Lineage recording. The training corpus's provenance (which recorded
   runs, which families) and the trained artifact's identity hash go in the
   record.

A first admissible run does not need to win. It needs to be gradeable --
which is the framework's whole claim.
