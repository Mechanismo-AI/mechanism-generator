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

## Usage

Drain the queue once (e.g. from cron or before bed):

    python jobs/local-llm-queue/queue_worker.py

Poll continuously (e.g. overnight alongside corpus runs):

    python jobs/local-llm-queue/queue_worker.py --loop

Non-ollama backend: pass any command that reads the prompt on stdin and
writes the answer to stdout:

    python jobs/local-llm-queue/queue_worker.py --command llama-cli -m /path/to/mistral-7b.gguf

## Prompt helpers

- `generate_corpus_digest_prompt.py <corpus-dir>` — embeds a corpus run's
  summary.json + per-variant line_result.json into a self-contained
  failure-taxonomy prompt and drops it in pending/. Output quality is
  advisory only; treat the clerk's numbers as quotes, never computations.

## Design notes

- One prompt at a time, oldest filename first, so long jobs do not starve
  short ones you queue later — name files with a sortable prefix
  (e.g. `01-corpus-digest.md`) if order matters.
- Backend failures are data, not crashes: the prompt moves to failed/ with
  stderr appended, and the worker keeps going.
- The worker never modifies the repository and never uploads anything.
