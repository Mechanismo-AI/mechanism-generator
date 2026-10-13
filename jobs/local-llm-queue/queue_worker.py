#!/usr/bin/env python3
"""Drain a local-LLM prompt queue with an arbitrary inference backend.

Prompts are plain UTF-8 text files dropped into queue/pending/. For each
prompt (oldest first by filename): move it to processing/, pipe its content
to the backend command on stdin, capture stdout into an answer file next to
the prompt in done/, and log the run. A backend failure moves the prompt
to failed/ with the captured stderr — nothing is lost.

The backend is whatever you have installed locally (ollama, llama.cpp,
LM Studio CLI, ...). The default assumes ollama:

    python queue_worker.py                      # drain queue once
    python queue_worker.py --loop               # keep polling
    python queue_worker.py --command llama-cli -m mistral-7b-instruct-v0.3.Q4_K_M.gguf

Answers land in queue/done/<same-name>.answer.md, so results can be read
in the morning alongside the corpus runs. This worker never modifies the
repository and never uploads anything.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE = Path(__file__).resolve().parent / "queue"
PENDING = QUEUE / "pending"
PROCESSING = QUEUE / "processing"
DONE = QUEUE / "done"
FAILED = QUEUE / "failed"


def ensure_dirs() -> None:
    for directory in (PENDING, PROCESSING, DONE, FAILED):
        directory.mkdir(parents=True, exist_ok=True)


def drain_once(command: list[str], timeout: float) -> tuple[int, int]:
    """Process every pending prompt. Returns (ok, failed)."""
    ok = failed = 0
    while True:
        prompts = sorted(PENDING.glob("*.md"))
        if not prompts:
            return ok, failed
        prompt_path = prompts[0]
        claim = PROCESSING / prompt_path.name
        shutil.move(str(prompt_path), str(claim))
        started = time.monotonic()
        answer_path = DONE / (claim.stem + ".answer.md")
        try:
            result = subprocess.run(
                command,
                input=claim.read_text(encoding="utf-8"),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            if result.returncode != 0 or not result.stdout.strip():
                raise RuntimeError(
                    f"backend exited {result.returncode}; stderr:\n{result.stderr[:4000]}"
                )
            answer_path.write_text(
                f"<!-- answered {time.strftime('%Y-%m-%d %H:%M:%S')} in "
                f"{time.monotonic() - started:.0f}s -->\n\n" + result.stdout,
                encoding="utf-8",
            )
            shutil.move(str(claim), str(DONE / claim.name))
            ok += 1
            print(f"done: {claim.name} -> {answer_path.name}", flush=True)
        except Exception as exc:  # backend failure is data, not a crash
            (FAILED / claim.name).write_text(
                claim.read_text(encoding="utf-8") + f"\n\n<!-- ERROR: {exc} -->\n",
                encoding="utf-8",
            )
            claim.unlink(missing_ok=True)
            failed += 1
            print(f"failed: {claim.name}: {exc}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--command",
        nargs=argparse.REMAINDER,
        default=["ollama", "run", "mistral:7b-instruct"],
        help="Backend command reading the prompt on stdin. Default: ollama mistral:7b-instruct",
    )
    parser.add_argument("--loop", action="store_true", help="Keep polling instead of draining once")
    parser.add_argument("--poll-seconds", type=float, default=30.0)
    parser.add_argument("--timeout", type=float, default=3600.0, help="Per-prompt backend timeout")
    args = parser.parse_args()
    ensure_dirs()
    command = args.command
    if not command:
        parser.error("--command needs at least the backend program name")
    print(f"backend: {shlex.join(command)}", flush=True)
    while True:
        ok, failed = drain_once(command, args.timeout)
        if not args.loop:
            return 1 if failed else 0
        if ok == 0 and failed == 0:
            time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
