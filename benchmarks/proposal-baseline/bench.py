"""Proposal-baseline benchmark: do the learned proposal models beat random starts?

Runs the unmodified public engine (r25c/r25b) three ways on the same tasks:

  learned      published proposal models, untouched
  random       one random proposal per start, same design space and projection
  random_pool  best of 128 random proposals, ranked by distance to the targets
  geometric    published models plus the engine's existing analytic position
               starter (--position_geometry: circumcentre construction, no model)

Only r25b.predict_initial_params is replaced. Start counts, phase seeding,
refinement, physical checks and qualification are identical across arms.

Usage (from the repository root, engine installed, models downloaded):

  python benchmarks/proposal-baseline/bench.py smoke                 # ~minutes, checks the harness
  python benchmarks/proposal-baseline/bench.py corpus                # writes the frozen task corpus
  python benchmarks/proposal-baseline/bench.py run --workers 6       # resumable; rerun to continue
  python benchmarks/proposal-baseline/bench.py summarize             # prints and writes summary.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ARMS = ("learned", "random", "random_pool", "geometric")
CORPUS_SEED = 20261023
POOL_SIZE = 128


# ---------------------------------------------------------------- helpers
def _engine():
    from mechanism_generator.engine import r25b, r25c
    return r25b, r25c


def _default_args():
    _, r25c = _engine()
    return r25c.build_parser().parse_args(["--targets", "0", "0", "1", "0", "0", "1"])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------- corpus
def make_corpus(count: int, seed: int) -> list:
    """Random valid crank-rockers inside the engine's design space; targets are
    three coupler points. The witness is recorded but never given to the solver."""
    import torch
    E, _ = _engine()
    args = _default_args()
    g = torch.Generator().manual_seed(seed)
    dt = torch.float64

    def U(lo, hi):
        return float(lo + (hi - lo) * torch.rand((), generator=g, dtype=dt))

    theta = torch.linspace(0.0, E.TWO_PI, 721, dtype=dt)[:-1]
    tasks, attempts = [], 0
    while len(tasks) < count:
        attempts += 1
        if attempts > 200000:
            raise RuntimeError(f"corpus generation stalled at {len(tasks)} tasks")
        l1 = U(3.0, 9.0)
        l2 = U(0.15, 0.45) * l1
        l3, l4 = U(0.5, 1.6) * l1, U(0.5, 1.6) * l1
        links = sorted([l1, l2, l3, l4])
        if l2 != links[0] or links[0] + links[3] > 0.95 * (links[1] + links[2]):
            continue  # require crank-rocker with Grashof margin
        params = [l1, l2, l3, l4, U(0.0, 1.0), U(0.1, 1.0) * l1,
                  U(-3.0, 3.0), U(-3.0, 3.0), U(0.0, E.TWO_PI)]
        branch = 1.0 if U(0.0, 1.0) < 0.5 else -1.0
        sim = E.simulate_four_bar(torch.tensor([params], dtype=dt), theta, branch)
        if not bool(sim["valid"].all()):
            continue
        idx = sorted(int(i) for i in torch.randperm(720, generator=g)[:3])
        gaps = [idx[1] - idx[0], idx[2] - idx[1], 720 - idx[2] + idx[0]]
        if min(gaps) < 60:  # at least 30 deg of crank between targets
            continue
        pts = [(float(sim["Px"][0, i]), float(sim["Py"][0, i])) for i in idx]
        target = torch.tensor([c for p in pts for c in p], dtype=dt)
        space = E.target_design_space(target, args)
        s = {k: float(v) for k, v in space.items() if v.numel() == 1}
        cx, cy = (float(v) for v in space["centroid"])
        ok = (s["ground_min"] <= l1 <= s["ground_max"]
              and all(s["moving_min"] <= v <= s["moving_max"] for v in (l2, l3, l4))
              and params[5] <= s["bar_max"]
              and s["base_x_min"] <= params[6] <= s["base_x_max"]
              and s["base_y_min"] <= params[7] <= s["base_y_max"]
              and s["scale"] >= 1.0)
        if not ok:
            continue
        tasks.append({
            "id": f"t{len(tasks):03d}",
            "targets": [round(c, 9) for c in target.tolist()],
            "witness": {"params": params, "branch": branch,
                        "phase_deg": [i * 0.5 for i in idx]},
        })
    return tasks


def cmd_corpus(a):
    path = Path(a.corpus)
    if path.exists():
        sys.exit(f"{path} exists; corpora are frozen. Delete it deliberately to regenerate.")
    tasks = make_corpus(a.count, CORPUS_SEED)
    path.write_text(json.dumps({"seed": CORPUS_SEED, "count": len(tasks), "tasks": tasks}, indent=1))
    print(f"wrote {path} ({len(tasks)} tasks) sha256={_sha256(path)}")


# ---------------------------------------------------------------- one run
def _install_random_proposals(pool: int):
    import torch
    E, _ = _engine()
    state = {"calls": 0}
    dt = torch.float64

    def proposal(role, target, args):
        state["calls"] += 1
        key = hashlib.sha256((repr(target.tolist()) + f"|{args.seed}|{state['calls']}").encode()).digest()
        g = torch.Generator().manual_seed(int.from_bytes(key[:8], "little"))
        space = E.target_design_space(target, args)

        def U(lo, hi):
            lo, hi = float(lo), float(hi)
            return lo + (hi - lo) * torch.rand((), generator=g, dtype=dt)

        def draw():
            lo, hi = math.log(float(space["moving_min"])), math.log(float(space["moving_max"]))
            vec = torch.stack([torch.exp(U(lo, hi)), torch.exp(U(lo, hi)), torch.exp(U(lo, hi)),
                               U(0.0, 1.0), U(E.MIN_BAR_LEN, space["bar_max"]),
                               U(space["base_x_min"], space["base_x_max"]),
                               U(space["base_y_min"], space["base_y_max"]),
                               U(0.0, E.TWO_PI)])
            return E.project_proposal_parameters(vec.to(target), target, args)

        if pool <= 1:
            return draw()
        cands = torch.stack([draw() for _ in range(pool)])
        theta = torch.linspace(0.0, E.TWO_PI, 361, dtype=target.dtype, device=target.device)[:-1]
        txy = target.reshape(3, 2)
        best = None
        for sign in (-1.0, 1.0):
            sim = E.simulate_four_bar(cands, theta, sign)
            d2 = ((sim["Px"][:, None, :] - txy[None, :, 0, None]).square()
                  + (sim["Py"][:, None, :] - txy[None, :, 1, None]).square())
            d2 = torch.where(sim["valid"][:, None, :], d2, torch.full_like(d2, E.INVALID_DISTANCE ** 2))
            score = d2.min(dim=2).values.sum(dim=1)
            best = score if best is None else torch.minimum(best, score)
        return cands[int(best.argmin())]

    E.predict_initial_params = proposal


def cmd_one(a):
    """Run one task under one arm in this process (called as a subprocess)."""
    for var in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS"):
        os.environ.setdefault(var, "1")
    import torch
    torch.set_num_threads(1)
    from mechanism_generator.engine.models import verify
    _, r25c = _engine()
    if a.arm == "random":
        _install_random_proposals(1)
    elif a.arm == "random_pool":
        _install_random_proposals(POOL_SIZE)
    paths = verify(Path(a.models))
    argv = ["--targets", *[repr(v) for v in a.targets], "--branches", "both", "--device", "cpu",
            "--headless", "--output_root", a.out, "--seed", "101"]
    if a.quick:
        argv.append("--quick")
    if a.arm == "geometric":
        argv.append("--position_geometry")
    for role, path in paths.items():
        argv += [f"--{role}_model", str(path)]
    sys.argv = ["mechanism-generate", *argv]
    return r25c.main()


# ---------------------------------------------------------------- batch
def _result_path(root: Path, task_id: str, arm: str) -> Path:
    return root / f"{task_id}_{arm}.json"


def _extract(out_dir: Path) -> dict:
    manifests = sorted(out_dir.rglob("run_manifest.json"))
    if not manifests:
        return {"status": "no_manifest"}
    t = json.loads(manifests[-1].read_text())["targets"][0]
    ref = t.get("selection_reference", {}) or {}
    sel = t.get("selected", []) or []
    best = min(sel, key=lambda r: r.get("mean_error", math.inf)) if sel else {}
    return {
        "status": "ok",
        "candidates": t.get("candidate_count"),
        "path_acceptable": t.get("path_acceptable_count"),
        "selection_eligible": t.get("selection_eligible_count"),
        "engineering_acceptable": t.get("engineering_acceptable_count"),
        "selected": t.get("selected_count"),
        "best_selected_mean_error": best.get("mean_error"),
        "best_selected_max_error": best.get("max_error"),
        "reference_mean_error": ref.get("reference_acquired_mean_error"),
        "runtime_seconds": t.get("runtime_seconds"),
    }


def _run_job(task, arm, a, root: Path):
    res = _result_path(root, task["id"], arm)
    if res.exists():
        return "skip"
    out = root / "o" / f"{task['id']}{arm[0]}{'p' if arm == 'random_pool' else ''}"
    log = root / "logs" / f"{task['id']}_{arm}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(Path(__file__).resolve()), "_one", "--arm", arm, "--models", a.models,
           "--out", str(out), "--targets", *[repr(v) for v in task["targets"]]]
    if a.quick:
        cmd.append("--quick")
    env = {**os.environ, "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1"}
    started = time.time()
    with open(log, "w") as fh:
        code = subprocess.call(cmd, stdout=fh, stderr=subprocess.STDOUT, env=env)
    record = {"task": task["id"], "arm": arm, "exit_code": code,
              "wall_seconds": round(time.time() - started, 2), **_extract(out)}
    res.write_text(json.dumps(record))
    return f"{task['id']} {arm} exit={code} eligible={record.get('selection_eligible')} {record['wall_seconds']}s"


def _run_batch(tasks, a, root: Path):
    root.mkdir(parents=True, exist_ok=True)
    jobs = [(t, arm) for t in tasks for arm in a.arms]
    print(f"{len(jobs)} jobs, {a.workers} workers, results in {root}")
    with ThreadPoolExecutor(max_workers=a.workers) as pool:
        for msg in pool.map(lambda j: _run_job(j[0], j[1], a, root), jobs):
            if msg != "skip":
                print(msg, flush=True)


def cmd_run(a):
    corpus = json.loads(Path(a.corpus).read_text())
    root = Path(a.results)
    meta = root / "corpus_sha256.txt"
    root.mkdir(parents=True, exist_ok=True)
    digest = _sha256(Path(a.corpus))
    if meta.exists() and meta.read_text().strip() != digest:
        sys.exit("results directory belongs to a different corpus; use a new --results directory")
    meta.write_text(digest)
    tasks = corpus["tasks"][: a.limit] if a.limit else corpus["tasks"]
    _run_batch(tasks, a, root)


def cmd_smoke(a):
    a.quick = True
    a.arms = list(ARMS)
    tasks = make_corpus(2, CORPUS_SEED + 1)
    _run_batch(tasks, a, Path(a.results))
    cmd_summarize(a)


# ---------------------------------------------------------------- summary
def _binom_two_sided(k: int, n: int) -> float:
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(0, min(k, n - k) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def cmd_summarize(a):
    root = Path(a.results)
    rows = [json.loads(p.read_text()) for p in sorted(root.glob("t*_*.json"))]
    by = {}
    for r in rows:
        by.setdefault(r["task"], {})[r["arm"]] = r
    complete = sorted(t for t, d in by.items() if all(arm in d for arm in ARMS))
    summary = {"results_dir": str(root), "complete_tasks": len(complete),
               "corpus_sha256": (root / "corpus_sha256.txt").read_text().strip()
               if (root / "corpus_sha256.txt").exists() else None, "arms": {}, "paired_vs_learned": {}}
    metrics = ("selection_eligible", "engineering_acceptable")
    for arm in ARMS:
        recs = [by[t][arm] for t in complete]
        errs = sorted(r["best_selected_mean_error"] for r in recs if r.get("best_selected_mean_error") is not None)
        times = sorted(r["wall_seconds"] for r in recs)
        summary["arms"][arm] = {
            **{m: sum(1 for r in recs if (r.get(m) or 0) > 0) for m in metrics},
            "crashed": sum(1 for r in recs if r["exit_code"] != 0 or r.get("status") != "ok"),
            "median_best_mean_error": errs[len(errs) // 2] if errs else None,
            "median_wall_seconds": times[len(times) // 2] if times else None,
        }
    for arm in ARMS[1:]:
        summary["paired_vs_learned"][arm] = {}
        for m in metrics:
            gains = [t for t in complete if (by[t][arm].get(m) or 0) > 0 and not (by[t]["learned"].get(m) or 0) > 0]
            losses = [t for t in complete if not (by[t][arm].get(m) or 0) > 0 and (by[t]["learned"].get(m) or 0) > 0]
            summary["paired_vs_learned"][arm][m] = {
                "baseline_wins": len(gains), "learned_wins": len(losses),
                "exact_p_two_sided": round(_binom_two_sided(len(gains), len(gains) + len(losses)), 4),
                "baseline_win_tasks": gains, "learned_win_tasks": losses}
    (root / "summary.json").write_text(json.dumps(summary, indent=1))
    print(json.dumps(summary, indent=1))


# ---------------------------------------------------------------- cli
def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--models", default="models")
    common.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    common.add_argument("--quick", action="store_true")
    common.add_argument("--arms", nargs="+", choices=ARMS, default=list(ARMS))
    s = sub.add_parser("corpus"); s.add_argument("--corpus", default=str(HERE / "corpus.json")); s.add_argument("--count", type=int, default=60)
    s = sub.add_parser("run", parents=[common]); s.add_argument("--corpus", default=str(HERE / "corpus.json")); s.add_argument("--results", default="runs/pb"); s.add_argument("--limit", type=int, default=0)
    s = sub.add_parser("smoke", parents=[common]); s.add_argument("--results", default="runs/pb-smoke")
    s = sub.add_parser("summarize"); s.add_argument("--results", default="runs/pb")
    s = sub.add_parser("_one"); s.add_argument("--arm", choices=ARMS, required=True); s.add_argument("--models", required=True)
    s.add_argument("--out", required=True); s.add_argument("--targets", type=float, nargs=6, required=True); s.add_argument("--quick", action="store_true")
    a = p.parse_args()
    return {"corpus": cmd_corpus, "run": cmd_run, "smoke": cmd_smoke, "summarize": cmd_summarize, "_one": cmd_one}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main() or 0)
