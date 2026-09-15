"""Contribution boundaries: useful failures stay local until an explicit review."""
import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import urllib.request
import webbrowser

import pytest

from mechanism_generator.contributions import bundle as contributions
from mechanism_generator.contributions.cli import main


PRIVATE = "PRIVATE-CANARY-do-not-share"


@pytest.fixture
def recorded_run(tmp_path):
    run = tmp_path / "run"
    target = run / "private-target"
    target.mkdir(parents=True)
    rows = [
        {"candidate_id": PRIVATE + "-failed", "mean_error": "inf", "max_error": "NaN",
         "physical_feasible": "False", "path_acceptable": "False", "selection_eligible": "False",
         "engineering_acceptable": "False", "qualification_level": "not_physical", "l1": "6.5"},
        {"candidate_id": PRIVATE + "-selected", "mean_error": "0.125", "max_error": "0.25",
         "physical_feasible": "True", "path_acceptable": "True", "selection_eligible": "True",
         "engineering_acceptable": "False", "qualification_level": "selection_acceptable",
         "selected_rank": "1", "portfolio_parent_candidate_id": PRIVATE + "-failed"},
        {"candidate_id": PRIVATE + "-path-only", "mean_error": "0.2", "max_error": "0.3",
         "physical_feasible": "true", "path_acceptable": "true", "selection_eligible": "false",
         "engineering_acceptable": "false", "qualification_level": "path_acceptable_but_robustness_failed",
         "shared_path_reference_candidate_id": PRIVATE + "-selected"},
    ]
    for row in rows:
        row.update({"history_path": PRIVATE, "notes": PRIVATE, "checkpoint_variant": PRIVATE,
                    "model_role": "balanced", "profile": "balanced", "portfolio_origin": "fixed"})
    columns = list(dict.fromkeys(key for row in rows for key in row))
    with (target / "all_candidates.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    manifest = {
        "variant": "R2.5c hybrid portfolio", "label": PRIVATE, "script": PRIVATE,
        "script_sha256": "a" * 64, "engine_sha256": "b" * 64,
        "arguments": {"seed": 17, "quick": True, "adam_lr": 0.04, "output_root": PRIVATE,
                      "balanced_model": PRIVATE, "label": PRIVATE, "device": PRIVATE},
        "models": [{"role": "balanced", "sha256": "c" * 64, "path": PRIVATE},
                   {"role": "path", "sha256": PRIVATE, "path": PRIVATE}],
        "targets": [{"label": PRIVATE, "directory": "private-target", "candidate_count": 3,
                     "path_acceptable_count": 2, "selection_eligible_count": 1,
                     "engineering_acceptable_count": 0, "selected_count": 1,
                     "target_values": [-6, 2, -2, 6, 0.5, 3.5], "extra": PRIVATE}],
    }
    (run / "run_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return run


def change_manifest(run, edit):
    path = run / "run_manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    edit(manifest)
    path.write_text(json.dumps(manifest), encoding="utf-8")


def reviewed(local):
    return {
        "schema_version": "0.1", "kind": "submission", "core": copy.deepcopy(local["core"]),
        "contributor": {"pseudonym": "A designer", "application": "Three-position handling."},
        "consent": {"terms_version": "1", "license": "Apache-2.0", "rights_confirmed": True,
                    "public_sharing_and_training": True},
    }


def make_symlink(link: Path, destination: Path):
    try:
        link.symlink_to(destination, target_is_directory=destination.is_dir())
    except (OSError, NotImplementedError):
        pytest.skip("Creating symbolic links is not available to this test account")


def test_export_allowlist_removes_source_identity_paths_and_unknown_fields(recorded_run):
    result = contributions.build_bundle(recorded_run)
    assert PRIVATE not in json.dumps(result)
    assert "private-target" not in json.dumps(result)
    assert result["settings"] == {"seed": 17, "quick": True, "adam_lr": 0.04}
    assert result["provenance"] == {
        "engine_sha256": "a" * 64, "parent_engine_sha256": "b" * 64,
        "models": [{"role": "balanced", "sha256": "c" * 64}],
    }
    assert result["task"] == [{"task_id": "task-0001", "target_values": [-6, 2, -2, 6, 0.5, 3.5]}]
    assert result["core"]["validation_status"] == "unreviewed"


def test_failed_candidates_survive_with_finite_metrics_and_remapped_lineage(recorded_run):
    result = contributions.build_bundle(recorded_run)
    failed, selected, path_only = result["candidates"][0]["items"]
    assert failed["candidate_id"] == "candidate-0001"
    assert failed["physical_feasible"] is False
    assert failed["qualification_level"] == "not_physical"
    assert failed["l1"] == 6.5
    assert "mean_error" not in failed and "max_error" not in failed
    assert selected["mean_error"] == 0.125
    assert selected["portfolio_parent_candidate_id"] == failed["candidate_id"]
    assert path_only["shared_path_reference_candidate_id"] == selected["candidate_id"]
    assert path_only["selection_eligible"] is False
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("status", [None, "partial", "completed"])
def test_recorded_status_is_preserved_without_inferring_completion(recorded_run, status):
    if status is not None:
        change_manifest(recorded_run, lambda manifest: manifest.update(run_status=status))
    result = contributions.build_bundle(recorded_run)
    assert result["core"]["run_status"] == (status or "unknown")
    assert len(result["core"]["tasks"]) == len(result["candidates"]) == 1


def test_completed_run_with_no_eligible_candidates_can_be_shared(recorded_run):
    change_manifest(recorded_run, lambda manifest: manifest.update(run_status="completed"))
    result = contributions.build_bundle(recorded_run)
    outcome = result["core"]["tasks"][0]
    outcome.update(selection_eligible_count=0, selected_count=0)
    for item in result["candidates"][0]["items"]:
        item["selection_eligible"] = False
        item.pop("selected_rank", None)
    contributions.validate_bundle(result)
    assert outcome["candidate_count"] == 3


def test_submission_can_omit_every_optional_section_but_retains_outcome(recorded_run):
    local = contributions.build_bundle(recorded_run)
    submission = reviewed(local)
    contributions.validate_bundle(submission)
    assert submission["core"] == local["core"]
    assert set(submission) == {"schema_version", "kind", "core", "contributor", "consent"}


@pytest.mark.parametrize("field,value", [
    ("rights_confirmed", False), ("public_sharing_and_training", False),
    ("license", "All rights reserved"), ("terms_version", "0"),
])
def test_submission_rejects_missing_or_changed_permission(recorded_run, field, value):
    submission = reviewed(contributions.build_bundle(recorded_run))
    submission["consent"][field] = value
    with pytest.raises(ValueError):
        contributions.validate_bundle(submission)
    del submission["consent"][field]
    with pytest.raises(ValueError):
        contributions.validate_bundle(submission)


def test_local_bundle_cannot_claim_submission_consent(recorded_run):
    local = contributions.build_bundle(recorded_run)
    local["consent"] = reviewed(local)["consent"]
    with pytest.raises(ValueError):
        contributions.validate_bundle(local)


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_validation_refuses_nonfinite_metrics(recorded_run, value):
    result = contributions.build_bundle(recorded_run)
    result["candidates"][0]["items"][0]["mean_error"] = value
    with pytest.raises(ValueError, match="Non-finite"):
        contributions.validate_bundle(result)


@pytest.mark.parametrize("problem", ["unknown_field", "duplicate_task", "duplicate_candidate", "dangling_parent", "missing_candidate", "selected_exceeds_eligible"])
def test_validation_refuses_inconsistent_or_unrecognized_records(recorded_run, problem):
    result = contributions.build_bundle(recorded_run)
    items = result["candidates"][0]["items"]
    if problem == "unknown_field":
        items[0]["private_log"] = PRIVATE
    elif problem == "duplicate_task":
        result["core"]["tasks"].append(copy.deepcopy(result["core"]["tasks"][0]))
    elif problem == "duplicate_candidate":
        items[1]["candidate_id"] = items[0]["candidate_id"]
    elif problem == "dangling_parent":
        items[1]["portfolio_parent_candidate_id"] = "candidate-9999"
    elif problem == "missing_candidate":
        items.pop()
    else:
        result["core"]["tasks"][0]["selected_count"] = 2
    with pytest.raises(ValueError):
        contributions.validate_bundle(result)


@pytest.mark.parametrize("field,count", [
    ("path_acceptable_count", 1), ("selection_eligible_count", 2),
    ("engineering_acceptable_count", 1),
])
def test_validation_checks_outcome_against_included_candidate_flags(recorded_run, field, count):
    result = contributions.build_bundle(recorded_run)
    result["core"]["tasks"][0][field] = count
    with pytest.raises(ValueError):
        contributions.validate_bundle(result)


@pytest.mark.parametrize("external_path", ["../outside", "absolute"])
def test_manifest_cannot_read_candidates_outside_run(recorded_run, external_path):
    directory = str(recorded_run.parent / "outside") if external_path == "absolute" else external_path
    change_manifest(recorded_run, lambda manifest: manifest["targets"][0].update(directory=directory))
    with pytest.raises(ValueError, match="relative path|outside"):
        contributions.build_bundle(recorded_run)


@pytest.mark.parametrize("artifact", ["run_manifest.json", "private-target/all_candidates.csv"])
def test_input_symlinks_cannot_escape_run(recorded_run, artifact):
    inside = recorded_run / artifact
    outside = recorded_run.parent / "outside-input"
    outside.write_bytes(inside.read_bytes())
    inside.unlink()
    make_symlink(inside, outside)
    with pytest.raises(ValueError, match="outside"):
        contributions.build_bundle(recorded_run)


@pytest.mark.parametrize("artifact", ["contribution", "contribution/bundle.json", "contribution/review.html"])
def test_output_symlinks_are_refused_without_overwriting_destination(recorded_run, artifact):
    outside = recorded_run.parent / "outside-output"
    if artifact == "contribution":
        outside.mkdir()
        sentinel = outside / "bundle.json"
    else:
        (recorded_run / "contribution").mkdir()
        sentinel = outside
    sentinel.write_text("KEEP", encoding="utf-8")
    make_symlink(recorded_run / artifact, outside)
    with pytest.raises(ValueError, match="symbolic link"):
        contributions.prepare_bundle(recorded_run)
    assert sentinel.read_text(encoding="utf-8") == "KEEP"


@pytest.mark.skipif(os.name != "nt", reason="Directory junctions are a Windows feature")
def test_output_junction_cannot_redirect_bundle_writes(recorded_run):
    outside = recorded_run.parent / "outside-output"
    outside.mkdir()
    sentinel = outside / "bundle.json"
    sentinel.write_text("KEEP", encoding="utf-8")
    output = recorded_run / "contribution"
    created = subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(output), str(outside)],
        capture_output=True, check=False,
    )
    if created.returncode:
        pytest.skip("Creating directory junctions is not available to this test account")
    assert output.resolve() == outside.resolve()
    with pytest.raises(ValueError):
        contributions.prepare_bundle(recorded_run)
    assert sentinel.read_text(encoding="utf-8") == "KEEP"
    assert not (outside / "review.html").exists()


def test_prepare_and_validate_cli_do_not_open_browser_or_connect_to_network(recorded_run, monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        pytest.fail("Local preparation or validation attempted an external action")
    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(socket, "create_connection", forbidden)
    monkeypatch.setattr(urllib.request, "urlopen", forbidden)
    monkeypatch.setattr(webbrowser, "open", forbidden)
    assert main(["prepare", str(recorded_run)]) == 0
    page = recorded_run / "contribution" / "review.html"
    bundle = page.with_name("bundle.json")
    assert page.is_file()
    assert PRIVATE not in page.read_text(encoding="utf-8")
    assert "__BUNDLE_JSON__" not in page.read_text(encoding="utf-8")
    assert main(["validate", str(bundle)]) == 0
    assert hashlib.sha256(bundle.read_bytes()).hexdigest() in capsys.readouterr().out


def test_invalid_cli_input_does_not_echo_untrusted_values(tmp_path, capsys):
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"credentials": PRIVATE}), encoding="utf-8")
    assert main(["validate", str(source)]) == 2
    output = capsys.readouterr()
    assert PRIVATE not in output.out + output.err
    assert "nothing was uploaded" in output.err


def test_json_reader_refuses_duplicate_fields_and_oversized_input(tmp_path):
    source = tmp_path / "input.json"
    source.write_text('{"kind": "local", "kind": "submission"}', encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate"):
        contributions.read_json(source)
    with source.open("wb") as stream:
        stream.truncate(contributions.MAX_BYTES + 1)
    with pytest.raises(ValueError, match="20 MiB"):
        contributions.read_json(source)
