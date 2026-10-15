# Evidence jobs

Each directory under `jobs` is a self-contained evidence job: a
`JOB.md` (for the queue, a `README.md`) with the purpose, the run
commands, and -- once executed -- the recorded outcome read against a
prediction scorecard written BEFORE the run. Failures,
zero-selection results, and refuted predictions are recorded as data,
not errors, and recorded outcomes are never rewritten. Corpus outputs
land in `runs/` (gitignored, maintainer-local).

| Job | Role | Status |
| --- | --- | --- |
| [sync-pair-eval-01](sync-pair-eval-01/JOB.md) | First end-to-end engine runs of the synchronized pair; produced the S4 verifier fixtures | Served; superseded by the corpus runs |
| [sync-corpus-01](sync-corpus-01/JOB.md) | The corpus driver (`corpus_run.py`) and the applied-offsets follow-up; shared by every later corpus | Driver in active use |
| [sync-corpus-05](sync-corpus-05/JOB.md) | G5 capstone: the pair sharing one keep-out zone (sampled-occupancy gating) | Run recorded |
| [sync-corpus-06](sync-corpus-06/JOB.md) | Anchor-probe pass: single-task offsets over the G5 pools | Run recorded |
| [sync-corpus-07](sync-corpus-07/JOB.md) | Z3 capstone: the screened corpus on fresh engine runs, against a frozen scorecard | Run recorded |
| [sync-corpus-08](sync-corpus-08/JOB.md) | Re-time probe over the screened pools plus the hand-declared 15/15 confirm; post-joint-search outcome appended | Run recorded |
| [local-llm-queue](local-llm-queue/README.md) | A patient-clerk queue for a local small LLM (digests, labeling, first drafts) | Active tooling |

Recorded outcomes are data about the state of the tools when the run
happened. Where a later revision changed a capability -- e.g. the
joint offset search (PR #30) now composes relations over derived
region events, which `omts propose-offsets` refused before -- the job
files say so and point forward; earlier sections are never rewritten.
