"""Regressions for the original tabletop brief and independent panel geometry."""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

np = pytest.importorskip("numpy")
torch = pytest.importorskip("torch")
pytest.importorskip("safetensors")
pytest.importorskip("matplotlib")
pytest.importorskip("pandas")

from mechanism_generator.engine import panel, pose_seeds, r25b, r25c
from mechanism_generator.omts.adapter import prepare_plan, UnsupportedFeature
from mechanism_generator.omts.validation import DocumentError
from mechanism_generator.contributions import bundle as contributions

ROOT = Path(__file__).resolve().parents[1]


def document():
    return yaml.safe_load((ROOT / "examples/omts/tabletop_transfer_panel.omts.yaml").read_text(encoding="utf-8"))


def case_args():
    run = prepare_plan(document())["runs"][0]
    parser = r25c.build_parser()
    args = parser.parse_args([*run["arguments"], "--crank_direction", "negative",
                             "--adam_accuracy_steps", "0", "--adam_tradeoff_steps", "0", "--lbfgs_steps", "0"])
    r25c.validate_args(parser, args)
    return np.array(run["positions"]), args


@pytest.fixture(scope="module")
def recovered():
    points, args = case_args()
    seeds, counts = pose_seeds.generate_pose_seeds(points, args.target_orientations_deg, args,
                                                  sample_count=args.pose_tolerance_samples, tolerance_aware=True)
    return points, args, seeds, counts


def test_integrated_initializer_recovers_original_brief_before_seed_truncation(recovered):
    points, args, seeds, counts = recovered
    nominal, _ = pose_seeds.generate_pose_seeds(points, args.target_orientations_deg, args)
    assert nominal == []
    assert len(seeds) == counts["returned_seeds"] == 1
    assert seeds[0]["sample_index"] == 208725
    assert counts["panel_pivot_pass_count"] == counts["panel_screened_count"] == 7
    assert counts["panel_passing_count"] == 1
    # Known witness is used only to verify the result, never supplied to the search.
    witness = json.loads((ROOT / "examples/tabletop-transfer/diagnosis/successful-candidate.json").read_text())
    actual = np.array(seeds[0]["parameters"])
    actual[:4] *= 30
    actual[5] *= 30
    actual[6:8] = actual[6:8] * 30 + [250, 40]
    np.testing.assert_allclose(actual, witness["parameters_mm"], atol=1e-8)


@pytest.mark.parametrize("branch", [-1, 1])
def test_panel_envelope_matches_separately_implemented_torch_geometry(recovered, branch):
    _, args, seeds, _ = recovered
    config = panel.configuration(args)
    p = np.array(seeds[0]["parameters"])
    report = panel.screen(p, branch, config)
    sim = r25b.simulate_four_bar(torch.tensor(p[None]), torch.linspace(0, 2*np.pi, config["steps"], dtype=torch.float64), branch)
    a, b, center = [np.column_stack((sim[x][0].numpy(), sim[y][0].numpy())) for x, y in [("Ax","Ay"),("Bx","By"),("Px","Py")]]
    direction = (b-a) / np.linalg.norm(b-a, axis=1)[:,None]
    normal = np.column_stack((-direction[:,1], direction[:,0]))
    corners = [center + x*direction + y*normal for x in (-25/30,25/30) for y in (-5/30,5/30)]
    outline = np.vstack([a,b,*corners, *[np.column_stack((sim[x][0].numpy(),sim[y][0].numpy())) for x,y in [("O2x","O2y"),("O4x","O4y")]]])
    np.testing.assert_allclose([report["panel_envelope_x_min"], report["panel_envelope_y_min"]], outline.min(axis=0), atol=1e-12)
    np.testing.assert_allclose([report["panel_envelope_x_max"], report["panel_envelope_y_max"]], outline.max(axis=0), atol=1e-12)
    assert report["panel_acceptable"] == (branch == -1)


def test_carrier_and_full_turn_are_screened_beyond_three_targets(recovered):
    _, args, seeds, _ = recovered
    p = seeds[0]["parameters"]
    config = panel.configuration(args)
    assert panel.screen(p, -1, config)["panel_acceptable"]
    # The requested centres remain above this raised floor, while the full turn leaves it.
    config["bounds"][2] = 1.
    assert not panel.screen(p, -1, config)["panel_acceptable"]
    config = panel.configuration(args)
    config["carrier_size"] = [20., 20.]
    assert not panel.screen(p, -1, config)["panel_acceptable"]
    config = panel.configuration(args)
    config["pivot_clearance"] = 1.
    assert not panel.screen(p, -1, config)["panel_acceptable"]
    for bad in ([1, 8, 1, 1, .5, .2, 0, 0, 0], [float("nan")]*9):
        assert not panel.screen(bad, -1, config)["panel_acceptable"]


@pytest.mark.parametrize("flags", [
    ["--panel_bounds", "0", "10", "0", "10"], ["--carrier_size", "1", "1"],
    ["--panel_pivot_clearance", "1"], ["--panel_steps", "360"],
    ["--panel_bounds", "0", "0", "0", "10", "--carrier_size", "1", "1"],
    ["--panel_bounds", "0", "10", "0", "nan", "--carrier_size", "1", "1"],
    ["--panel_bounds", "0", "10", "0", "10", "--carrier_size", "0", "1"],
    ["--panel_bounds", "0", "10", "0", "10", "--carrier_size", "1", "1", "--panel_pivot_clearance", "5"],
    ["--pose_tolerance_samples", "262145"], ["--pose_tolerance_samples", "-1"], ["--pose_dyad_samples", "262145"],
])
def test_invalid_cli_constraints_rejected(flags):
    parser = r25c.build_parser()
    with pytest.raises(SystemExit):
        r25c.validate_args(parser, parser.parse_args(flags))


def test_panel_and_budget_adapter_maps_and_rejects_unsupported_semantics():
    doc = document()
    _, args = case_args()
    assert args.pose_dyad_samples == 4096 and args.pose_tolerance_samples == 262144
    assert panel.configuration(args)["carrier_size"] == [50/30, 10/30]
    doc["tasks"][0]["requirements"]["panel"]["bounds"] = [0, 1, 0, 1]
    doc["tasks"][0]["requirements"]["panel"]["pivot_clearance"] = 1
    with pytest.raises(DocumentError):
        prepare_plan(doc)


def test_preserved_parent_final_gate_exports_and_contribution_round_trip(recovered, tmp_path):
    points, args, _, _ = recovered
    target = torch.tensor(points.flatten(), dtype=torch.float64)
    reference = {"reference_candidate_id":"neural", "reference_acquired_mean_error":0., "reference_acquired_errors":[0.]*3,
                 "shared_mean_budget":1/30, "shared_point_budgets":[1.5/30]*3}
    parents, children, diagnostic = r25c.run_pose_geometry(target, args, reference, tmp_path/"task/history", {})
    assert len(parents) == len(children) == 1
    assert diagnostic["nominal_returned_seeds"] == 0 and diagnostic["tolerance_returned_seeds"] == 1
    candidate = parents[0]
    candidates = parents + children
    r25b.apply_shared_candidate_qualification(candidates, args, reference)
    assert candidate["selection_eligible"] and candidate["pose_acceptable"] and candidate["panel_acceptable"]
    assert not candidate["engineering_acceptable"]  # Preferred transmission goals are still unmet.
    assert candidate["max_error"]*30 < 1e-6 and candidate["max_orientation_error_deg"] < 3
    assert candidate["panel_edge_clearance"]*30 == pytest.approx(.913208, abs=1e-4)
    # A failed or absent panel result must not survive ordinary final selection.
    for remove in (False, True):
        rejected = copy.deepcopy(candidate)
        if remove: rejected.pop("panel_acceptable")
        else: rejected["panel_acceptable"] = False
        r25b.apply_shared_candidate_qualification([rejected], args, reference)
        assert not rejected["selection_eligible"] and rejected["qualification_level"] == "path_acceptable_but_panel_failed"
        assert r25b.select_diverse_candidates([rejected], args) == ([], False)
    r25b.save_candidate_artifacts(candidate, 1, tmp_path/"task", args)
    archive = np.load(next((tmp_path/"task").glob("*.npz")), allow_pickle=False)
    assert archive["panel_acceptable"] and archive["carrier_width"] == 50/30
    r25b.write_csv(tmp_path/"task/all_candidates.csv", [r25b.flat_candidate_row(c) for c in candidates])
    task = dict(directory="task", target_values=target.tolist(), crank_direction="negative",
                panel=panel.configuration(args), pose_initialization=diagnostic,
                target_orientations_deg=args.target_orientations_deg, orientation_tolerances_deg=args.orientation_tolerances_deg,
                orientation_frame="coupler_A_to_B",candidate_count=len(candidates), selected_count=1)
    for field in ("path_acceptable","selection_eligible","engineering_acceptable","orientation_acceptable","pose_acceptable","panel_acceptable"):
        task[field+"_count"] = sum(c[field] for c in candidates)
    manifest=dict(variant="R2.5c",run_status="completed",targets=[task],arguments=vars(args),models=[])
    (tmp_path/"run_manifest.json").write_text(json.dumps(manifest))
    bundle=contributions.build_bundle(tmp_path)
    assert bundle["schema_version"] == "0.5"
    assert bundle["task"][0]["panel"] == task["panel"]
    assert bundle["candidates"][0]["items"][0]["proposal_source"] == pose_seeds.TOLERANCE_METHOD
    for section, key in (("task","panel"),("candidates","panel_required")):
        altered=copy.deepcopy(bundle)
        item=altered[section][0] if section=="task" else altered[section][0]["items"][0]
        item.pop(key)
        with pytest.raises(ValueError): contributions.validate_bundle(altered)
    for change in ("settings", "count", "clearance", "geometry", "diagnostic"):
        altered = copy.deepcopy(bundle)
        if change == "settings": altered["settings"]["panel_bounds"][0] -= 1
        elif change == "count": altered["core"]["tasks"][0]["panel_acceptable_count"] = 0
        elif change == "clearance": altered["candidates"][0]["items"][0]["panel_edge_clearance"] = -1
        elif change == "geometry": altered["candidates"][0]["items"][0]["panel_geometry_valid"] = False
        else: altered["task"][0]["pose_initialization"]["panel_passing_count"] = 0
        with pytest.raises(ValueError): contributions.validate_bundle(altered)
    for keep in ("task", "candidates", None):
        partial={key:value for key,value in bundle.items() if key not in ("task","candidates","settings","provenance") or key==keep}
        contributions.validate_bundle(partial)


def test_separate_slots_keep_nominal_candidates_and_tolerance_sampling_is_reproducible(tmp_path, monkeypatch):
    cases=json.loads((ROOT/"docs/pose-benchmark.json").read_text())["cases"]
    case=next(c for c in cases if c["id"]=="angle_wrap")
    parser=r25c.build_parser()
    args=parser.parse_args(["--branches","both","--phase_mode","ordered","--pose_dyad_seed_count","2"])
    args.target_orientations_deg=case["target_orientations_deg"]
    args.orientation_tolerances_deg=[.25, 1.5, 4.]
    r25c.validate_args(parser,args)
    target=torch.tensor(case["target_points"],dtype=torch.float64).flatten()
    reference={"reference_candidate_id":"neural","reference_acquired_mean_error":.01,"reference_acquired_errors":[.01]*3,"shared_mean_budget":.03,"shared_point_budgets":[.06]*3}
    monkeypatch.setattr(r25c,"run_acquisitions",lambda *a: [])
    monkeypatch.setattr(r25c,"run_tradeoff",lambda *a: [])
    combined, _, counts=r25c.run_pose_geometry(target,args,reference,tmp_path,{})
    assert counts["nominal_returned_seeds"] == counts["tolerance_returned_seeds"] == 2
    assert len({c["candidate_id"] for c in combined}) == 4
    seeds, _=pose_seeds.generate_pose_seeds(case["target_points"],args.target_orientations_deg,args,max_seeds=2)
    assert [c["generator_sample_index"] for c in combined[:2]] == [s["sample_index"] for s in seeds]
    before=np.random.get_state()
    one,_=pose_seeds.generate_pose_seeds(case["target_points"],args.target_orientations_deg,args,tolerance_aware=True)
    two,_=pose_seeds.generate_pose_seeds(case["target_points"],np.array(args.target_orientations_deg)+720,args,tolerance_aware=True)
    np.testing.assert_array_equal(np.random.get_state()[1],before[1])
    assert [s["sample_index"] for s in one] == [s["sample_index"] for s in two]
    for a,b in zip(one,two):
        np.testing.assert_allclose(a["parameters"],b["parameters"],atol=1e-10)
        sim=r25b.simulate_four_bar(torch.tensor([a["parameters"]]),torch.tensor(a["phases_rad"]),a["branch_sign"])
        angles=np.degrees(np.arctan2((sim["By"]-sim["Ay"])[0].numpy(),(sim["Bx"]-sim["Ax"])[0].numpy()))
        errors=np.abs((angles-np.array(args.target_orientations_deg)+180)%360-180)
        assert np.all(errors<=args.orientation_tolerances_deg)
