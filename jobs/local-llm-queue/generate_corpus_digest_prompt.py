#!/usr/bin/env python3
"""Build a corpus-digest prompt for the local LLM queue.

Reads a corpus output directory (summary.json plus each variant's
line_result.json produced by jobs/sync-corpus-01/corpus_run.py) and returns
a self-contained prompt; the script pre-computes a compact failure digest
with exact numbers (per-constraint pass counts, distances to windows, lead
shortfalls, reversed-order equivalents, anchor-probe intervals). The LLM is
asked only to write plain-language prose about that digest. No repository
files are modified.

    python generate_corpus_digest_prompt.py ../sync-corpus-03

The CLI drops the prompt into this clone's queue/pending/, for clerk nodes
running on the same machine. To hand a digest to a clerk running on another
machine, use send_digest.py, which builds the same prompt and delivers it.

Prompt filenames carry a deterministic 4-hex tag derived from the corpus
directory name + summary.json bytes, so re-running for an unchanged corpus
regenerates the same filename. (Older releases used a per-process salted
hash() instead, which produced a new filename on every run.)
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
PENDING = HERE / "queue" / "pending"

HEADER = (
    "You are a careful clerk summarizing a mechanism-synchronization experiment.\n"
    "Each variant is a rotate/scaled copy of the same two-task document (a gate\n"
    "task and a catcher task). For each variant, every combination of selected\n"
    "candidates was checked against hard events (a phase window for the handoff)\n"
    "and hard ordering relations (a required lead between release and grab, in\n"
    "degrees of master-cycle phase). The digest below was computed exactly by a\n"
    "script; all numbers in it are trustworthy.\n\n"
    "Write the following, using ONLY numbers that appear in the digest:\n"
    "1. For each variant: 2-3 sentences in plain language saying which\n"
    "   constraint fails, how often, and by how much (quote the numbers).\n"
    "2. Group the variants into failure families (e.g. window overshoot,\n"
    "   reversed order, lead too short) and name the family of each variant.\n"
    "3. One short paragraph on what the anchor_probe intervals mean for fixing\n"
    "   each variant by re-phasing (shifting a task's offset), if probe data is\n"
    "   present.\n"
    "Do not invent numbers, do not recompute anything, and say so explicitly\n"
    "if the digest does not contain what a section asks for.\n\n"
    "DIGEST (computed exactly by script):\n\n"
)


def _combinations(result: dict) -> list:
    combos = result.get("combinations")
    if combos is None:
        combos = result.get("results", [])
    return combos if isinstance(combos, list) else []


def _status_of(entry: dict) -> str:
    return str(entry.get("status", "fail")).lower()


def _fmt(values: list) -> str:
    """Compact min..max for a list of floats."""
    if not values:
        return "n/a"
    lo, hi = min(values), max(values)
    if abs(hi - lo) < 0.05:
        return f"{lo:.1f}"
    return f"{lo:.1f}..{hi:.1f}"


def _dist_to_window(phase: float, window: list) -> float:
    """Signed distance from phase to [lo, hi]; 0 when inside; negative below."""
    lo, hi = window[0], window[1]
    if phase < lo:
        return phase - lo
    if phase > hi:
        return phase - hi
    return 0.0


def digest_variant(name: str, result: dict) -> str:
    """One compact text block per variant, exact numbers only."""
    lines = []
    verdict = result.get("verdict", result.get("status", "unknown"))
    combos = _combinations(result)
    passing = [c for c in combos if _status_of(c) == "pass"]
    offsets = result.get("applied_offsets") or {}
    lines.append(
        f"### variant {name}: verdict={verdict}, passing {len(passing)}/{len(combos)} combinations"
    )
    if offsets:
        lines.append(f"applied_offsets (deg): {json.dumps(offsets)}")

    # Events: per id, how many combos pass, and each participant's phase
    # plus signed distance to the window (negative = below window).
    event_ids: list[str] = []
    for c in combos:
        for e in c.get("events", []):
            if e.get("id") not in event_ids:
                event_ids.append(e.get("id"))
    for eid in event_ids:
        fails = passes = 0
        window = None
        parts: dict = {}
        for c in combos:
            for e in c.get("events", []):
                if e.get("id") != eid:
                    continue
                window = e.get("window_deg", window)
                if _status_of(e) == "pass":
                    passes += 1
                else:
                    fails += 1
                for idx, ph in enumerate(e.get("participant_phases_deg", [])):
                    parts.setdefault(idx, []).append(ph)
        if window is None:
            continue
        lines.append(
            f"event {eid} (hard): fails in {fails}/{len(combos)} combos; window={window} deg"
        )
        for idx in sorted(parts):
            dists = [_dist_to_window(p, window) for p in parts[idx]]
            below = [abs(d) for d in dists if d < -0.05]
            above = [d for d in dists if d > 0.05]
            inside = len(dists) - len(below) - len(above)
            notes = []
            if below:
                notes.append(f"{len(below)}/{len(dists)} phases below window by {_fmt(below)} deg")
            if above:
                notes.append(f"{len(above)}/{len(dists)} phases above window by {_fmt(above)} deg")
            if inside:
                notes.append(f"{inside}/{len(dists)} phases inside")
            lines.append(
                f"  participant {idx}: phase {_fmt(parts[idx])} deg ({'; '.join(notes)})"
            )

    # Relations: per id, pass count, achieved lead range vs required band,
    # with a reversed-order equivalent for leads near 360.
    rel_ids: list[str] = []
    for c in combos:
        for r in c.get("relations", []):
            if r.get("id") not in rel_ids:
                rel_ids.append(r.get("id"))
    for rid in rel_ids:
        fails = passes = 0
        lead = []
        band = None
        for c in combos:
            for r in c.get("relations", []):
                if r.get("id") != rid:
                    continue
                band = (r.get("min_lead_deg"), r.get("max_lead_deg"), band[2] if band else r.get("type"))
                lead.append(float(r.get("achieved_lead_deg", 0.0)))
                if _status_of(r) == "pass":
                    passes += 1
                else:
                    fails += 1
        if band is None:
            continue
        mn, mx, rtype = band
        req = f"[{mn}, {mx}] deg" if mn is not None and mx is not None else "n/a"
        lines.append(
            f"relation {rid} ({rtype or 'ordering'}, hard): fails in {fails}/{len(combos)} combos; required lead {req}"
        )
        lines.append(f"  achieved lead {_fmt(lead)} deg")
        short = [float(mn) - v for v in lead if mn is not None and v < mn]
        over = [v - float(mx) for v in lead if mx is not None and v > mx]
        rev = [v - 360.0 for v in lead if v > 180.0]
        n = len(lead)
        if short:
            lines.append(f"  {len(short)}/{n} combos short of the minimum by {_fmt(short)} deg")
        if over:
            lines.append(f"  {len(over)}/{n} combos exceed the maximum by {_fmt(over)} deg")
        if rev:
            lines.append(
                f"  {len(rev)}/{n} combos have lead > 180 deg (equivalent to {_fmt(rev)} deg, i.e. the pair happens in the reversed order)"
            )

    # Soft failures, verbatim if any.
    soft = []
    for c in combos:
        soft.extend(c.get("soft_failures", []))
    if soft:
        lines.append(f"soft_failures: {json.dumps(soft[:10])}")

    # Anchor probe intervals, verbatim (feasible per-task offset intervals).
    probe = result.get("anchor_probe")
    if probe:
        lines.append(f"anchor_probe (feasible offset intervals per task): {json.dumps(probe.get('tasks', probe))}")

    return "\n".join(lines)


def build_prompt(corpus: Path) -> str:
    """Return the full digest prompt for a corpus output directory.

    Fail-closed: raises FileNotFoundError / ValueError with a clear
    message on missing or malformed inputs; never returns an empty prompt.
    """
    summary_path = corpus / "summary.json"
    if not summary_path.is_file():
        raise FileNotFoundError(f"no summary.json in {corpus}")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"{summary_path}: invalid JSON ({e})") from e

    rows = summary if isinstance(summary, list) else summary.get("variants", [])
    blocks = []
    for row in rows:
        vid = row.get("task_set_id")
        if vid is None:
            continue
        line_result = corpus / vid / "plan" / "line_result.json"
        if line_result.is_file():
            try:
                parsed = json.loads(line_result.read_text(encoding="utf-8"))
            except json.JSONDecodeError as e:
                raise ValueError(f"{line_result}: invalid JSON ({e})") from e
            blocks.append(digest_variant(vid, parsed))
        else:
            blocks.append(f"### variant {vid}: no line_result.json (status in summary: {row.get('status')})")
    if not blocks:
        raise ValueError(f"{summary_path}: no variants with a task_set_id found")
    return HEADER + "\n\n".join(blocks) + "\n"


def prompt_tag(corpus: Path) -> str:
    """Deterministic 4-hex tag from the corpus dir name + summary bytes."""
    h = hashlib.sha1()
    h.update(corpus.name.encode("utf-8"))
    h.update(b"\0")
    h.update((corpus / "summary.json").read_bytes())
    return h.hexdigest()[:4]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("corpus_dir", type=Path, help="Directory containing summary.json")
    parser.add_argument("--name", default="corpus-digest", help="Prompt file basename")
    args = parser.parse_args()
    corpus = args.corpus_dir.resolve()
    try:
        prompt = build_prompt(corpus)
        tag = prompt_tag(corpus)
    except (FileNotFoundError, ValueError) as e:
        parser.error(str(e))

    PENDING.mkdir(parents=True, exist_ok=True)
    out = PENDING / f"{args.name}-{tag}.md"
    out.write_text(prompt, encoding="utf-8")
    print(f"queued: {out}")
    print(f"prompt size: {len(prompt)} chars")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
