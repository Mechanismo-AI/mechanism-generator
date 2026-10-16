#!/usr/bin/env python3
"""One-command corpus-digest handoff to the clerk node.

Builds the same digest prompt as generate_corpus_digest_prompt.py on this
machine, then delivers it to the clerk worker's queue on another machine
(default ssh alias "megabox"). Idempotent: if the clerk node already holds
any prompt with this --name prefix in pending/, processing/, done/, or
failed/, the command says so and sends nothing. Fail-closed: ssh/scp
problems abort loudly, and the prompt is left in this clone's
queue/pending/ so nothing is lost.

    python jobs/local-llm-queue/send_digest.py runs/sync-corpus-03 --name corpus03

The answer will appear as <remote-queue>/done/<prompt-name>.answer.md on
the clerk node. Read it over ssh and review it before anything enters the
record: the clerk's numbers are quotes, never computations.
"""

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from generate_corpus_digest_prompt import build_prompt, prompt_tag  # noqa: E402

DEFAULT_HOST = "megabox"
DEFAULT_QUEUE = "~/mechanism-generator/jobs/local-llm-queue/queue"
STATES = ("pending", "processing", "done", "failed")


def die(msg: str) -> None:
    print(f"send_digest: FAIL-CLOSED: {msg}", file=sys.stderr)
    raise SystemExit(1)


def run_remote(host: str, command: str, timeout: float = 30.0) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["ssh", host, command],
            capture_output=True, text=True, timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        die(f"ssh to {host!r} timed out on: {command}")
    except FileNotFoundError:
        die("ssh is not installed on this machine — install openssh-client first")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", type=Path, help="Directory containing summary.json")
    parser.add_argument("--name", default=None,
                        help="Prompt file basename (default: the corpus dir name)")
    parser.add_argument("--host", default=DEFAULT_HOST,
                        help=f"ssh alias of the clerk node (default: {DEFAULT_HOST})")
    parser.add_argument("--remote-queue", default=DEFAULT_QUEUE,
                        help=f"queue dir on the clerk node (default: {DEFAULT_QUEUE})")
    args = parser.parse_args()

    name = args.name or args.corpus_dir.name
    corpus = args.corpus_dir.resolve()
    try:
        prompt = build_prompt(corpus)
        tag = prompt_tag(corpus)
    except (FileNotFoundError, ValueError) as e:
        die(str(e))
    fname = f"{name}-{tag}.md"

    # 1. Reach the clerk node and canonicalize its queue path (expands ~).
    res = run_remote(args.host, f"echo {args.remote_queue}")
    lines = [l.strip() for l in res.stdout.splitlines() if l.strip()]
    if res.returncode != 0 or len(lines) != 1:
        detail = (res.stderr or res.stdout or "no output").strip()
        die(f"cannot reach clerk node {args.host!r}: {detail}")
    queue = lines[0]

    probe = run_remote(args.host, f"test -d {shlex.quote(queue + '/pending')} && echo ok")
    if probe.returncode != 0 or probe.stdout.strip() != "ok":
        detail = (probe.stderr or probe.stdout or "no output").strip()
        die(f"no queue at {queue} on {args.host!r} — is the clerk worker set up there? ({detail})")

    # 2. Idempotency: skip if the clerk node already knows this name.
    pattern = shlex.quote(name + "-*")
    find_cmd = (
        "find "
        + " ".join(shlex.quote(f"{queue}/{state}") for state in STATES)
        + f" -maxdepth 1 -name {pattern} -print -quit 2>/dev/null"
    )
    seen = run_remote(args.host, find_cmd)
    if seen.returncode == 0 and seen.stdout.strip():
        print(f"already known to the clerk: {seen.stdout.strip()}")
        print("nothing sent. Delete it there if you really want a re-digest.")
        return 0

    # 3. Deliver to the clerk's pending/ and verify arrival.
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write(prompt)
        tmp_path = Path(fh.name)
    try:
        scp = subprocess.run(
            ["scp", "-q", str(tmp_path), f"{args.host}:{queue}/pending/{fname}"],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        scp = subprocess.CompletedProcess([], 127, "",
                                           f"{type(e).__name__}: {e}")
    if scp.returncode != 0:
        fallback = HERE / "queue" / "pending"
        fallback.mkdir(parents=True, exist_ok=True)
        local_copy = fallback / fname
        local_copy.write_text(prompt, encoding="utf-8")
        tmp_path.unlink(missing_ok=True)
        die(
            f"scp to {args.host!r} failed ({(scp.stderr or '').strip()}); "
            f"prompt preserved locally at {local_copy} — transfer it by hand or retry."
        )
    tmp_path.unlink(missing_ok=True)

    check = run_remote(args.host, f"test -f {shlex.quote(queue + '/pending/' + fname)} && echo ok")
    if check.returncode != 0 or check.stdout.strip() != "ok":
        die(f"scp reported success but {fname} is not in {queue}/pending/ on {args.host!r} — check by hand before rerunning")

    print(f"delivered: {args.host}:{queue}/pending/{fname}")
    print(f"prompt size: {len(prompt)} chars")
    print(f"the answer will appear at: {args.host}:{queue}/done/{fname}.answer.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
