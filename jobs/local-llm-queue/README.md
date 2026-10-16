# local-llm-queue

An async job queue for a locally installed small LLM (e.g. Mistral 7B
Instruct on CPU). Rationale: local CPU inference is slow (single-digit
tokens/second), so it is a "patient clerk" — good at batch work that can
grind unattended (digests, labeling, first-draft prose, pre-validation
linting), useless for latency-sensitive or arithmetic work. The engine,
verifier, and validators remain the only source of truth for numbers.

## Layout

    queue/pending/      drop prompt files here (UTF-8 text, .md)
    queue/processing/   in-flight (crash-safe: reclaim manually if stuck)
    queue/done/         prompt + <name>.answer.md pairs
    queue/failed/       prompts whose backend run failed, with stderr appended

`queue/` is per-machine runtime state (gitignored); each clerk node has
its own. Prompts and answers are never committed.

## Usage

Drain the queue once (e.g. from cron or before bed):

    python jobs/local-llm-queue/queue_worker.py

Poll continuously (e.g. overnight alongside corpus runs):

    python jobs/local-llm-queue/queue_worker.py --loop

Non-ollama backend: pass any command that reads the prompt on stdin and
writes the answer to stdout:

    python jobs/local-llm-queue/queue_worker.py --command llama-cli -m /path/to/mistral-7b.gguf


`--command` takes separate shell words; a single quoted string such as
`--command "ollama run mistral:7b-instruct"` is also accepted and split
with shlex.

**Clerk node shared with other duties (e.g. a TV/streaming box):** the
worker only feeds the backend, so `nice` on the worker is not enough when
the backend is a daemon (ollama runs inference inside the daemon process).
Throttle the daemon instead:

    sudo systemctl edit ollama
    # add:
    [Service]
    Nice=19
    CPUQuota=150%

then `sudo systemctl restart ollama`, and restart the tmux worker under
`nice -n 19` for good measure. Video decode always wins; the clerk just
grinds slower — which the queue is built to tolerate.

## Prompt helpers

- `generate_corpus_digest_prompt.py <corpus-dir> [--name N]` — embeds a
  corpus run's summary.json + per-variant line_result.json into a
  self-contained failure-taxonomy prompt and drops it in THIS machine's
  pending/. Output quality is advisory only; treat the clerk's numbers as
  quotes, never computations. The filename tag is deterministic (corpus
  dir name + summary bytes), so an unchanged corpus regenerates the same
  filename.

- `send_digest.py <corpus-dir> [--name N] [--host HOST] [--remote-queue Q]`
  — the cross-machine handoff: builds the same prompt on the work machine,
  checks the clerk node by ssh for any existing prompt with this name
  (pending/processing/done/failed) and skips if found (idempotent), then
  delivers it into the clerk node's pending/ and verifies arrival. Default
  host `megabox`, default queue `~/mechanism-generator/jobs/local-llm-queue/queue`.
  The answer lands in the clerk node's `done/<name>.answer.md`; read it
  over ssh and review before anything enters the record. On ssh/scp
  failure the command aborts loudly, leaving the prompt in the local
  clone's pending/ so nothing is lost.

## Design notes

- One prompt at a time, oldest filename first, so long jobs do not starve
  short ones you queue later — name files with a sortable prefix
  (e.g. `01-corpus-digest.md`) if order matters.
- Backend failures are data, not crashes: the prompt moves to failed/ with
  stderr appended, and the worker keeps going.
- The worker never modifies the repository and never uploads anything.
- qwen3-family backends emit "Thinking..." chains by default; disable
  thinking (or strip the chains) before treating answers as clean output.
