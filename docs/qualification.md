# Qualification and success

There are three separate questions:

1. Is this a valid OMTS document? Schema and semantic validation answer this.
2. Can an implementation represent these requirements? Adapter capability checks
   answer this for a restricted subset.
3. Does a generated mechanism satisfy them? Only actual evaluation can answer this.

`omts validate` answers the first question. `omts adapt` also answers the second
and produces a plan with status `prepared_not_evaluated`. Neither establishes the
third. Even accepting `requested_validation_level: kinematic_candidate` expresses
the request, not an achieved result.

OMTS's vocabulary includes kinematic, mechanically screened, dynamically evaluated,
structurally evaluated, and prototype validated outputs. The public engine performs
kinematic checks only. The adapter rejects requests above `kinematic_candidate`.

In the historical R2.5c outputs, read `selection_eligible`, `engineering_acceptable`,
and `qualification_level`. Physical assembly alone is not path accuracy or adequate
transmission. The historical label `engineering_acceptable` describes that engine's
kinematic thresholds; it is not proof of dynamic, structural, or prototype validity.

The historical engine can reserve an unqualified fixed-reference mechanism in its
selected exports. This adapter sets `--portfolio_guarantee_fixed_count 0` and
`--strict_qualification` so those references cannot bypass qualified selection.
The public alpha also fixes the engine so fixed reservation considers only eligible
candidates, and rejects unqualified fallback. Raw `all_candidates` and stage reports can still
contain rejected mechanisms. Count eligible candidates, not output files.

Fewer than `top_k` results, including none, is a valid outcome. An exported plan or
nonempty result directory does not establish success.
