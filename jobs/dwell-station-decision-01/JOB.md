# dwell-station-decision-01 -- case study A capability-to-spec/decision record

Status: Staged; awaiting run

This job records the dwell-station capability-to-spec/decision step of the
case-study loop (brief -> failure analysis -> capability -> THIS STEP),
which the frozen rule requires to be preceded by the debate round. Both
rounds ran through Jean's chat relay on 2026-10-19 and are folded here;
Jean decides. Nothing in this job re-opens the recorded
dwell-station-capability-01 outcome or its frozen K1-K8 scorecard.

## The decision record (2026-10-19; relayed actor + critic rounds; Jean decides)

1. THE INSTANCE LINE: LEVER + tolerance zoning. The trade is stated
   plainly so the choice is seen, not defaulted: the lever line buys
   footprint margin with a tighter profile class (plus one pivot and the
   lever as parts); the direct line buys class looseness (2.0x at the
   0.10 mm working class) with a ~2x plate. The direct branch's
   precondition -- a real station footprint measurement -- is un-executable
   today (no real line exists for this case study), so the decision is
   between an executable close and a branch whose opening condition cannot
   be met now. The lever line is the first design in this project to clear
   every gate without a cliff edge (case B's Option B cleared by 0.068 mm
   and 0.26 deg; this line holds +149 to +165 mm and passes the 45 deg
   hard gate too), and its manufacturing cost lands on the easiest
   geometry there is: the concentric dwell arc. Physical realism, on the
   record: the direct 464.44 mm major is a ~930 mm diameter cam plate --
   near-meter plates bring balance, inertia and mounting costs this record
   has not priced; renegotiation would rescue the envelope, not the plate
   physics.
2. ZONING: the dwell-arc-zoned class carries from case B's T4 decision.
   The BOUND is frozen: the required class (WC guarantee) is the recorded
   K6 knee, 0.05846 mm (band-lo) / 0.05164 mm (band-hi) -- a property of
   the recorded design that cannot move without new data. The WORKING
   PICK, 0.05 mm, is a declared default parameter, revisable at spec time
   with lineage, guided by the knee curve; freezing a specific procurement
   number now would be precision the project cannot earn (no customer
   exists to bind it). The pick is inside both knees (fail-closed in the
   instrument).
3. THE WIDTH AMENDMENT (the actor's blocking item; the critic's
   provenance demand answered from the record): the recorded design's
   nominal dwell arc is exactly 50.00 deg (the K2-derived allowance is
   0.00 deg, reproduced fail-closed in section [A]), so restating the
   lever line's guaranteed dwell width is a DECLARED AMENDMENT, never a
   restatement. The amendment takes the declared-change discipline:
   - Frozen rule: w = (zero-error guaranteed width) - (zoned-class
     guaranteed width) of the un-biased recorded design at the WORST
     instance (band-hi), rounded UP to the 0.2 deg cycle-tiling multiple
     (never down: a bias must not under-deliver). Derived, not picked.
   - Reason: the amendment converts tolerance-driven erosion of the hold
     window into nominal arc, so the >= 50 deg guarantee rests on the
     construction-exact arc, not on the rise margins, which vanish at the
     knee.
   - The new nominal re-enters the frozen allocation rule (dwell arc +
     remainder proportional to stroke 130:130:260), and the
     headroom/curvature/junction table is re-checked at the new pick
     (section [D], fail-closed).
4. THE TWO BIAS LEVERS, KEPT DISTINCT (never blurred in the record):
   the RADIAL datum-bias lever (case-B lineage) is recorded-and-unfired
   here, with its trigger stated -- its case-B trigger was zero cap
   headroom, and the lever line has +149 to +165 mm, so there is nothing
   to convert. The ANGULAR width-bias (the duration channel's analog) is
   FIRED, as the declared amendment in item 3, with nominal and
   guaranteed widths both reported.
5. THE PIVOT-JOINT CLASS (declared deferral, never silent): the lever
   adds a pivot (clearance/backlash) and a roller-pin fit whose error term
   sits in the position budget in exactly the way the passive guide's
   class does, per the frozen split rule. Its share is not priced in this
   record; the deferral trigger is payload/grasp modeling, where rated
   forces and joint selection arrive together. The 0.3 mm region is NOT
   proven against profile error alone -- the derivation chain below shows
   what is and is not priced.
6. THE DERIVATION CHAIN, visible end to end (every arrow is already
   validated machinery): 0.3 mm hold region -> frozen WC split (passive
   guide class 0.10 mm) -> x-budget 0.20 mm -> S = lambda amplification ->
   required profile class (WC) = x-budget / lambda = the recorded knees
   (0.05846 / 0.05164 mm, the frozen bound) -> working pick 0.05 mm
   (declared default, revisable with lineage). The RSS convention is
   reported alongside (x-budget 0.2828 mm; knees 0.0827 / 0.0730 mm).
7. THE CROSS-SLIDE PAIR TRIGGER, pinned: the pair returns ONLY if line
   architecture demands y-motion; the passive y-guide suffices for the
   single-axis task, and its class enters the 0.3 mm budget via the
   frozen split rule -- the pair-vs-guide choice is visible in the
   budget, not just in prose.
8. THE SPEC-SIDE MAPPING: the class-to-spec mapping mirrors the
   offset_realization precedent -- RECORDED, NEVER GATED. The spec
   speaks in demand units (0.3 mm, 50 deg); the profile class is a
   realization record attached at build time. The dwell-duration
   vocabulary shape waits for the spec step (claim-only-what-exists);
   the recorded predictions carried forward: the sync machinery already
   handles event windows, so duration windows may be nearly free (a
   prediction, not a claim), and the duration knee == position knee
   finding means one tolerance realization serves both channels.
9. THE FALLBACK BRANCH, live with its trigger: DIRECT + envelope
   renegotiation, triggered by a real station footprint measurement
   showing room. The labeled placeholder gives that branch cleaner
   standing than case B's cap had.

## The instrument

`dwell_station_decision.py` (pure standard-library Python, deterministic,
fail-closed) consumes the recorded design READ-ONLY: the sibling
`dwell-station-capability-01/dwell_station_design.py` is imported and
pinned by sha256 (public main b652b75e, the -01 run of record), so the
consumption is provably byte-identical. Sections: [A] fail-closed
reproduction of the recorded oracle (every pinned K-value recomputed
through the recorded machinery); [B] the declared width amendment under
the frozen rule, with the K1-class witnesses re-run on the amended cycle;
[C] the restated duration guarantee (the blocking item), the >= 50 deg
demand check fail-closed; [D] the re-checked
headroom/curvature/junction table, the picked line's gates fail-closed;
[E] the derivation chain and declared deferrals; [F] control.

## Frozen scorecard (written before the run of record)

- S1 ORACLE: the recorded -01 oracle reproduces fail-closed -- allowance
  0.00 deg; allocation 77.50/50.00/77.50/155.00 deg; junction peaks
  350.63/175.32 mm/rad^2; direct major 464.44 mm WIDE-FAIL at 163.0%;
  lever majors 135.76/119.92 mm PASS; knees WC 0.2000/0.0585/0.0516 mm;
  widths at the working class 52.70/0.00/0.00 deg; dwell max |slide|
  exactly 0; stroke exactly 260 mm. Any mismatch aborts.
- S2 AMENDMENT: w_raw = 53.80 - 50.60 = 3.20 deg at the band-hi instance;
  w = 3.20 deg (rounded up to the 0.2 deg tile); amended cycle
  76.70/53.20/76.70/153.40 deg (the frozen allocation rule re-entered);
  K1-class witnesses on the amended cycle (dwell max |slide| exactly 0,
  stroke exactly 260); the zoned pick 0.05 mm inside both knees
  (fail-closed).
- S3 THE RESTATED GUARANTEE (the blocking item): guaranteed dwell width
  at the 0.05 mm zoned class -- band-hi 53.80 deg, band-lo 54.60 deg; at
  the knee (margins vanish) 53.20 deg = the construction-exact arc;
  the >= 50 deg demand met at every class inside the knee, fail-closed,
  with 3.20 deg of declared nominal margin at the knee itself; the direct
  instance on the amended cycle at the working class (55.90 deg) reported
  as data, not the picked line.
- S4 THE RE-CHECKED TABLE: band-lo major 136.53 mm (+148.47 mm headroom),
  band-hi 120.60 mm (+164.40 mm); both PASS the 30 deg target and the
  45 deg hard gate (fail-closed); curvature min |rho| 47.79/42.21 mm
  above the 18.75 mm floor (fail-closed); the direct instance still
  WIDE-FAIL the placeholder (467.09 mm; data); amended junction peaks
  357.99/178.99 mm/rad^2 (the price of the wider dwell arc: faster rises;
  +2.1%/+2.1% vs the recorded cycle, data).
- S5 CONTROL: sha256 read-only witness; no OMTS vocabulary; the recorded
  K1-K8 record untouched; the pair trigger, the fallback trigger, the
  pivot deferral and the derivation chain all on the page.
- S6 DETERMINISM: double-run byte-identical in-process; the machine run
  twice redirected with an empty diff.

## Staging smoke-test reading (disclosed; the machine run after merge is the run of record)

Two staging runs, exit 0 both, byte-identical, diff empty. [A] PASS with
every pinned value reproduced exactly. [B] w_raw 3.20 deg -> w 3.20 deg;
amended cycle 76.70/53.20/76.70/153.40 deg; amended junction peaks
357.99/178.99 mm/rad^2; dwell witness exactly 0.000000 mm over the
1065-sample amended arc; stroke 260.000000 mm. [C] band-hi 53.80 deg /
band-lo 54.60 deg at the zoned class; 53.20 deg at the knee; direct
55.90 deg (data); the >= 50 deg check PASS fail-closed. [D] table as in
S4, no gate moved. [E]/[F] emitted. Honest instrument note (the standing
self-consistency limitation): the staging smoke test runs the same
arithmetic as the run of record, so it cannot catch a wrong frozen
declaration -- the frozen declarations above were desk-checked against
the relayed debate record and the recorded -01 JOB (the PR #62 lesson,
applied to ourselves).

## Machine step after merge (Jean, on the-hub; seconds, no engine)

```
git pull
python3 jobs/dwell-station-decision-01/dwell_station_decision.py > decision_run1.txt 2>&1
python3 jobs/dwell-station-decision-01/dwell_station_decision.py > decision_run2.txt 2>&1
diff decision_run1.txt decision_run2.txt   # must be empty
```

Paste `decision_run1.txt` back (plus the Python version line) for the
S1-S6 reading. Zero divergence from the staging reading is expected (the
deterministic prediction pattern). After the outcome records: case study
A's spec-side step (the OMTS dwell-duration vocabulary question), with
this decision as its input.
