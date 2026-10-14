"""The corpus-digest prompt builder: exact numbers, not raw JSON.

These tests pin the digest-prompt behavior: the script pre-computes a
compact per-variant failure digest (per-constraint pass counts, signed
distances to windows, lead shortfalls with reversed-order equivalents,
verbatim anchor-probe intervals) so the local LLM only writes prose about
small exact tables. No LLM is required.
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "jobs" / "local-llm-queue" / "generate_corpus_digest_prompt.py"

_spec = importlib.util.spec_from_file_location(
    "generate_corpus_digest_prompt", SCRIPT_PATH)
digest = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(digest)


def _combo(catcher, gate, phases, window_status, lead):
    return {
        "candidates": {"catcher": catcher, "gate": gate},
        "events": [{
            "id": "handoff_window", "mode": "hard",
            "participant_phases_deg": phases,
            "window_deg": [100, 140], "status": window_status,
        }],
        "relations": [{
            "id": "release_before_grab", "type": "ordering", "mode": "hard",
            "achieved_lead_deg": lead, "min_lead_deg": 10, "max_lead_deg": 45,
            "status": "fail",
        }],
        "status": "fail", "soft_failures": [],
    }


def _line_result():
    return {
        "verdict": "failed",
        "combination_count": 4,
        "passing_combination_count": 0,
        "applied_offsets": {"catcher": 340.0},
        "combinations": [
            # window fail: participant 1 far below the window.
            _combo("c1", "g1", [93.8, 18.6], "fail", 284.78),
            # window fail: participant 0 slightly below the window.
            _combo("c1", "g2", [93.8, 117.3], "fail", 247.34),
            # window pass, lead just short of the minimum.
            _combo("c1", "g3", [115.4, 117.3], "pass", 1.88),
            # window pass, lead near 360 (reversed order).
            _combo("c1", "g4", [119.8, 117.3], "pass", 357.49),
        ],
        "anchor_probe": {
            "step_deg": 1.0,
            "tasks": {"catcher": [{"from_deg": 320.0, "to_deg": 351.0,
                                   "passing": 5}],
                      "gate": []},
        },
    }


def test_digest_variant_reports_exact_numbers():
    text = digest.digest_variant("corpus_pair_03", _line_result())
    # verdict and pass count
    assert "verdict=failed, passing 0/4 combinations" in text
    # event: pass count and signed window distance per participant
    assert "event handoff_window (hard): fails in 2/4 combos; window=[100, 140] deg" in text
    assert "participant 0: phase 93.8..119.8 deg" in text
    assert "2/4 phases below window by 6.2 deg" in text
    assert "participant 1: phase 18.6..117.3 deg" in text
    assert "1/4 phases below window by 81.4 deg" in text
    # relation: required band, shortfall, reversed-order equivalent
    assert ("relation release_before_grab (ordering, hard): "
            "fails in 4/4 combos; required lead [10, 45] deg") in text
    assert "achieved lead 1.9..357.5 deg" in text
    assert "1/4 combos short of the minimum by 8.1 deg" in text
    assert "3/4 combos have lead > 180 deg" in text
    assert "equivalent to -112.7..-2.5 deg" in text
    # applied offsets and probe intervals, verbatim
    assert '"catcher": 340.0' in text
    assert '"from_deg": 320.0' in text


def test_digest_omits_absent_sections():
    result = _line_result()
    del result["applied_offsets"]
    del result["anchor_probe"]
    text = digest.digest_variant("corpus_pair_03", result)
    assert "applied_offsets" not in text
    assert "anchor_probe" not in text
    # no soft failures -> no soft_failures line
    assert "soft_failures" not in text


def _corpus_dir(tmp_path, with_result=True):
    corpus = tmp_path / "sync-corpus-03"
    corpus.mkdir()
    rows = [{"task_set_id": "corpus_pair_03", "status": "failed",
             "combination_count": 4,
             "passing_combination_count": 0},
            {"task_set_id": "corpus_pair_04", "status": "no_candidates"}]
    (corpus / "summary.json").write_text(json.dumps(rows), encoding="utf-8")
    if with_result:
        variant = corpus / "corpus_pair_03" / "plan"
        variant.mkdir(parents=True)
        (variant / "line_result.json").write_text(
            json.dumps(_line_result()), encoding="utf-8")
    return corpus


def test_main_writes_compact_prompt(tmp_path, monkeypatch, capsys):
    corpus = _corpus_dir(tmp_path)
    pending = tmp_path / "pending"
    monkeypatch.setattr(digest, "PENDING", pending)
    monkeypatch.setattr(
        "sys.argv", ["generate_corpus_digest_prompt.py", str(corpus),
                     "--name", "digest"])

    assert digest.main() == 0
    out = capsys.readouterr().out
    assert "queued:" in out
    written = list(pending.glob("digest-*.md"))
    assert len(written) == 1
    prompt = written[0].read_text(encoding="utf-8")
    # instructions plus digest, not raw JSON dumps
    assert "DIGEST (computed exactly by script):" in prompt
    assert "using ONLY numbers that appear in the digest" in prompt
    assert "verdict=failed, passing 0/4 combinations" in prompt
    # missing variant falls back to its summary status
    assert "corpus_pair_04: no line_result.json (status in summary: no_candidates)" in prompt
    # compactness: the whole prompt stays far below the raw-JSON scale
    assert len(prompt) < 6000


def test_main_rejects_missing_summary(tmp_path, monkeypatch):
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setattr(digest, "PENDING", tmp_path / "pending")
    monkeypatch.setattr(
        "sys.argv", ["generate_corpus_digest_prompt.py", str(empty)])
    with pytest.raises(SystemExit):
        digest.main()


def test_size_stays_compact_at_full_corpus_scale(tmp_path):
    """25 combinations per variant must not blow the prompt back up."""
    result = _line_result()
    combos = []
    for i in range(25):
        combo = _combo(f"c{i}", f"g{i % 5}", [110.0 + i, 120.0], "fail",
                       300.0 + i)
        combos.append(combo)
    result["combinations"] = combos
    result["combination_count"] = 25
    text = digest.digest_variant("corpus_pair_03", result)
    assert "passing 0/25 combinations" in text
    assert "fails in 25/25 combos" in text
    assert len(text) < 2000
