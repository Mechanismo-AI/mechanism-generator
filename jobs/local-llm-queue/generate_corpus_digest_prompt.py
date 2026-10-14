#!/usr/bin/env python3
"""Build a corpus-digest prompt for the local LLM queue.

Reads a corpus output directory (summary.json plus each variant's
line_result.json produced by jobs/sync-corpus-01/corpus_run.py) and writes a
self-contained prompt into queue/pending/ asking for a plain-language
failure taxonomy. No repository files are modified.

    python generate_corpus_digest_prompt.py ../sync-corpus-03
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PENDING = HERE / "queue" / "pending"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", type=Path, help="Directory containing summary.json")
    parser.add_argument("--name", default="corpus-digest", help="Prompt file basename")
    args = parser.parse_args()
    corpus = args.corpus_dir.resolve()
    summary_path = corpus / "summary.json"
    if not summary_path.is_file():
        parser.error(f"no summary.json in {corpus}")
    payload = {"summary": json.loads(summary_path.read_text(encoding="utf-8")), "variants": {}}
    for variant_dir in sorted(p for p in corpus.iterdir() if p.is_dir()):
        line_result = variant_dir / "plan" / "line_result.json"
        if line_result.is_file():
            payload["variants"][variant_dir.name] = json.loads(line_result.read_text(encoding="utf-8"))
    PENDING.mkdir(parents=True, exist_ok=True)
    prompt = (
        "You are analyzing results of a mechanism-synchronization experiment. "
        "Each variant is a rotate/scaled copy of the same two-task document "
        "(a gate task and a catcher task, checked over all selected-candidate "
        "combinations). Failure entries carry (relation, expected, actual, delta) "
        "in degrees of master-cycle phase.\n\n"
        "Produce: (1) one sentence per variant saying what actually failed and "
        "by how much; (2) a taxonomy grouping variants by failure kind; (3) any "
        "pattern connecting failure size to the variant's rotation/scale. "
        "Do not invent numbers; quote only what appears in the data.\n\n"
        "DATA:\n" + json.dumps(payload, indent=2)
    )
    out = PENDING / f"{args.name}-{abs(hash(str(corpus))) % 10000:04d}.md"
    out.write_text(prompt, encoding="utf-8")
    print(f"queued: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
