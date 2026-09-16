import copy
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from mechanism_generator.omts import DocumentError, validate_document
from mechanism_generator.omts.adapter import UnsupportedFeature, prepare_plan, write_plan
from mechanism_generator.omts.cli import main


def option(run, flag):
    return run["arguments"][run["arguments"].index(flag) + 1]


def test_independent_tasks_retain_different_requirements(task_document):
    second = copy.deepcopy(task_document["tasks"][0])
    second["id"] = "second"
    second["requirements"]["path"]["max_mean_error"] = 0.01
    second["requirements"]["transmission"]["selection_min_global"] = 22
    second["search"]["seed"] = 42
    second["mechanism_search"]["portfolio"]["bridge_perturbations"] = 2
    task_document["tasks"].append(second)
    runs = prepare_plan(task_document)["runs"]
    assert [float(option(run, "--max_mean_error")) for run in runs] == [0.05, 0.01]
    assert [int(option(run, "--minimum_global_transmission")) for run in runs] == [10, 22]
    assert [int(option(run, "--seed")) for run in runs] == [101, 42]
    assert option(runs[1], "--portfolio_bridge_perturbations") == "2"
    assert runs[0]["targets_file"] != runs[1]["targets_file"]


def test_ordered_indices_control_csv_position_order(task_document, tmp_path):
    motion = task_document["tasks"][0]["motion"]
    motion["order_policy"] = "ordered"
    for target, index in zip(motion["targets"], (20, 30, 10)):
        target["occurrence"]["order_index"] = index
    output = tmp_path / "plan"
    write_plan(task_document, output)
    plan = json.loads((output / "run_plan.json").read_text())
    run = plan["runs"][0]
    assert run["target_ids"] == ["T3", "T1", "T2"]
    assert option(run, "--phase_mode") == "ordered"
    with (output / run["targets_file"]).open(newline="") as stream:
        rows = list(csv.reader(stream))
    assert [float(value) for value in rows[1][1:]] == [0.5, 3.5, -6, 2, -2, 6]


def test_stricter_equal_target_tolerance_is_enforced(task_document):
    for target in task_document["tasks"][0]["motion"]["targets"]:
        target["tolerance"]["position"] = 0.01
    assert float(option(prepare_plan(task_document)["runs"][0], "--max_point_error")) == 0.01


def test_unequal_target_tolerances_are_rejected(task_document):
    task_document["tasks"][0]["motion"]["targets"][1]["tolerance"]["position"] = 0.01
    with pytest.raises(UnsupportedFeature, match="identical"):
        prepare_plan(task_document)


@pytest.mark.parametrize("field,value", [
    ("max_mean_error", 0), ("max_point_error", 0)
])
def test_exact_path_requests_cannot_disable_checks(task_document, field, value):
    task_document["tasks"][0]["requirements"]["path"][field] = value
    with pytest.raises(UnsupportedFeature, match="disable checks"):
        prepare_plan(task_document)


def test_semantic_validation_is_also_used_by_adapter(task_document, tmp_path):
    task_document["tasks"].append(copy.deepcopy(task_document["tasks"][0]))
    output = tmp_path / "must-not-exist"
    with pytest.raises(DocumentError, match="duplicate ID"):
        write_plan(task_document, output)
    assert not output.exists()


@pytest.mark.parametrize("replacement", [
    {"mode": "fixed", "value": 6},
    {"mode": "optimize", "bounds": [3, 8]},
    {"mode": "portfolio", "fixed_values": [6, 7]},
    {"mode": "portfolio", "fixed_values": [6], "variable_bounds": [3, 8]},
])
def test_ground_constraints_are_never_silently_weakened(task_document, replacement):
    task_document["tasks"][0]["mechanism_search"]["ground_link"] = replacement
    assert validate_document(task_document) == []
    with pytest.raises(UnsupportedFeature):
        prepare_plan(task_document)


@pytest.mark.parametrize("section,key,value", [
    ("search", "candidate_budget", 100),
    ("search", "time_budget_seconds", 10),
    ("search", "implementation_profile", "other"),
    ("mechanism_search", "max_actuators", 0),
    ("mechanism_search", "bounds", {"l2": [1, 4]}),
    ("mechanism_search", "profiles", ["accuracy"]),
    ("motion", "cycle", {"period": 1.2}),
    ("motion", "cycle", {"direction": "bidirectional"}),
    ("requirements", "compactness", {"mode": "hard", "max_link_ratio": 2}),
    ("requirements", "path", {"mode": "soft", "weight": 5}),
    ("requirements", "transmission", {"mode": "hard", "min_at_targets": 30}),
    ("requirements", "assembly", {"min_margin": 1}),
    ("requirements", "collision_free", {"required": True, "mode": "hard"}),
])
def test_unsupported_operational_fields_fail_closed(task_document, section, key, value):
    task_document["tasks"][0][section][key] = value
    assert validate_document(task_document) == []
    with pytest.raises(UnsupportedFeature):
        prepare_plan(task_document)


@pytest.mark.parametrize("section,key,value", [
    ("units", "length", "mm"),
    ("units", "angle", "rad"),
    ("coordinate_system", "handedness", "left"),
    ("outputs", "formats", ["json", "step"]),
    ("outputs", "include_histories", False),
    ("outputs", "requested_validation_level", "mechanically_screened"),
    ("outputs", "pareto_objectives", ["energy"]),
])
def test_units_and_outputs_are_checked(task_document, section, key, value):
    task_document[section][key] = value
    if key == "angle":
        task_document["tasks"][0]["requirements"].pop("transmission")
    with pytest.raises(DocumentError):
        prepare_plan(task_document)


def test_capabilities_policy_and_extensions_checked(task_document):
    for key, value in (("capabilities_required", ["dwell"]), ("unsupported_feature_policy", "ignore"), ("extensions", {"vendor.constraint": 1})):
        document = copy.deepcopy(task_document)
        document[key] = value
        with pytest.raises(UnsupportedFeature):
            prepare_plan(document)


def test_future_example_is_valid_but_cannot_be_adapted(future_document, tmp_path):
    assert validate_document(future_document) == []
    output = tmp_path / "plan"
    with pytest.raises(UnsupportedFeature):
        write_plan(future_document, output)
    assert not output.exists()


def test_continuation_noise_and_output_flags_are_propagated(task_document):
    task = task_document["tasks"][0]
    task["search"].update(parameter_noise=0.3, phase_noise=7, perturbations_per_model=2)
    task["mechanism_search"]["ground_link"].update(release=False, trust_fraction=0.1)
    task["mechanism_search"]["portfolio"].update(skip_release=True, trust_fraction=0.1)
    task["mechanism_search"]["assembly_branches"] = ["crossed"]
    task["requirements"]["classification"]["follower_not_longest"] = True
    task_document["outputs"]["formats"].append("png")
    run = prepare_plan(task_document)["runs"][0]
    assert option(run, "--parameter_noise") == "0.3"
    assert option(run, "--phase_noise_deg") == "7"
    assert option(run, "--portfolio_l1_trust_fraction") == "0.1"
    assert option(run, "--branches") == "positive"
    assert "--no_plots" not in run["arguments"]
    assert "--portfolio_skip_release" in run["arguments"]
    assert "--enforce_follower_not_longest" in run["arguments"]


def test_qualification_and_conflicting_controls(task_document):
    run = prepare_plan(task_document)["runs"][0]
    assert option(run, "--portfolio_guarantee_fixed_count") == "0"
    assert "--strict_qualification" in run["arguments"]
    assert "--allow_unqualified_fallback" not in run["arguments"]
    for key, value in (("guarantee_fixed_count", 1), ("skip_release", True), ("trust_fraction", 0.5)):
        document = copy.deepcopy(task_document)
        document["tasks"][0]["mechanism_search"]["portfolio"][key] = value
        with pytest.raises(UnsupportedFeature):
            prepare_plan(document)
    task_document["tasks"][0]["search"]["top_k"] = 1
    with pytest.raises(UnsupportedFeature, match="top_k conflicts"):
        prepare_plan(task_document)


def test_plan_is_deterministic_portable_and_never_overwritten(task_document, tmp_path):
    before = copy.deepcopy(task_document)
    assert prepare_plan(task_document) == prepare_plan(copy.deepcopy(task_document))
    output = tmp_path / "spaces and $characters" / "plan"
    plan_path = write_plan(task_document, output)
    original = plan_path.read_bytes()
    assert str(tmp_path) not in original.decode()
    assert json.loads(original)["status"] == "prepared_not_evaluated"
    assert task_document == before
    with pytest.raises(FileExistsError):
        write_plan(task_document, output)
    assert plan_path.read_bytes() == original


def test_generated_runner_uses_argument_arrays_and_anchored_paths(task_document, tmp_path):
    output = tmp_path / "plan with spaces $()"
    write_plan(task_document, output)
    package_root = tmp_path / "package with spaces"
    package = package_root / "mechanism_generator"
    engine = package / "engine"
    engine.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (engine / "__init__.py").write_text("")
    stub = engine / "__main__.py"
    stub.write_text(
        'import json, pathlib, sys\n'
        'a = sys.argv[1:]\n'
        'assert pathlib.Path(a[a.index("--targets_file")+1]).is_file()\n'
        'pathlib.Path("invocation.json").write_text(json.dumps(a))\n', encoding="utf-8")
    # A subprocess integration double tests launch behavior, not optimizer quality.
    plan_path = output / "run_plan.json"
    plan = json.loads(plan_path.read_text())
    plan["expected_engine_artifacts"] = {stub.name: hashlib.sha256(stub.read_bytes()).hexdigest()}
    models = tmp_path / "models with spaces"
    models.mkdir()
    model = models / "balanced.safetensors"
    model.write_bytes(b"test double")
    plan["expected_artifacts"] = {model.name: hashlib.sha256(model.read_bytes()).hexdigest()}
    plan_path.write_text(json.dumps(plan))
    env = dict(os.environ, PYTHONPATH=str(package_root))
    result = subprocess.run([sys.executable, str(output / "run_r25c.py"), "--models-directory", str(models)],
                            cwd=tmp_path, capture_output=True, text=True, env=env)
    assert result.returncode == 0, result.stderr
    arguments = json.loads((output / "invocation.json").read_text())
    assert arguments[arguments.index("--targets_file") + 1] == str(output / "tasks/task-001/targets.csv")
    assert arguments[arguments.index("--output_root") + 1] == str(output / "results/task-001")
    stub.write_text('raise RuntimeError("must never run after hash mismatch")')
    result = subprocess.run([sys.executable, str(output / "run_r25c.py"), "--models-directory", str(models)], capture_output=True, text=True, env=env)
    assert result.returncode != 0
    assert "mismatched engine artifact" in result.stderr


def test_cli_distinguishes_validation_from_adaptation(tmp_path, future_document, capsys):
    source = tmp_path / "future.json"
    source.write_text(json.dumps(future_document))
    assert main(["validate", str(source)]) == 0
    assert "feasibility are not evaluated" in capsys.readouterr().out
    output = tmp_path / "rejected"
    assert main(["adapt", str(source), "--output-dir", str(output)]) == 1
    assert "unsupported" in capsys.readouterr().err
    assert not output.exists()
