"""Escalate panel search only after the existing portfolio has no qualified result."""
from pathlib import Path
import hashlib
import time
import torch
from . import r25b as E, panel_position_seeds, panel_near_seeds, panel_refinement

METHOD = 'adaptive_panel_position_v1'
LARGER = 'panel_position_larger_dyad_v1'
NEAR = 'panel_position_near_miss_v1'
REFINED = 'panel_position_refinement_v1'


def source_hash():
    paths = [Path(__file__), Path(panel_position_seeds.__file__), Path(panel_near_seeds.__file__), Path(panel_refinement.__file__)]
    return hashlib.sha256(b''.join(p.name.encode()+b'\0'+p.read_bytes()+b'\0' for p in paths)).hexdigest()


def evaluate(seed, target, args, reference, identity, origin, method, directory, raw=None, parent=None):
    p = torch.tensor(seed['parameters'], dtype=target.dtype, device=target.device)
    phases = torch.tensor(seed['phases_rad'], dtype=target.dtype, device=target.device)
    initial = E.encode_refinement_variables(p, phases, target, 'unordered', args)
    start = E.StartSpec(identity, 'panel_geometry', 'balanced', method, None,
                       float(seed['branch_sign']), 0, initial, p, phases)
    c = E.evaluate_selected_candidate(dict(start=start, raw_selected=initial if raw is None else raw,
        mean_budget=reference['shared_mean_budget'], point_budget=reference['shared_point_budgets'],
        selection_reason='panel_adaptive_candidate', acquired_mean_error=0., acquired_errors=[0.,0.,0.],
        history_path=str(directory/f'history_{identity}.csv')), target, args)
    c.update(acquired_mean_error=c['mean_error'], proposal_source=method,
             generator_sample_index=int(seed['sample_index']), portfolio_origin=origin,
             portfolio_parent_candidate_id=parent or '',
             portfolio_lineage=f"{origin}:halton_sample={seed['sample_index']}")
    for i in (1,2,3):
        c[f'acquired_error_{i}'] = c[f'error_{i}']
    E.apply_shared_candidate_qualification([c], args, reference)
    return c


def run(target, args, reference, existing, directory, lineage):
    """Return additional candidates only; never change or replace existing ones."""
    began = time.perf_counter()
    d = dict(method=METHOD, enabled=bool(getattr(args,'panel_position_adaptive',False)), status='disabled',
             source_sha256=source_hash(), larger_samples=0, larger_candidates=0, near_samples=0,
             near_candidates=0, refinement_starts=0, refined_candidates=0, adam_steps=0,
             lbfgs_evaluations=0, optimizer_failures=0, runtime_seconds=0.)
    added = []

    def finish(status):
        d.update(status=status, runtime_seconds=time.perf_counter()-began)
        return added, d

    def retain(c):
        directory.mkdir(parents=True, exist_ok=True)
        E.write_csv(directory/f"history_{c['candidate_id']}.csv", [{k:c[k] for k in (
            'candidate_id','proposal_source','mean_error','max_error','physical_feasible','panel_acceptable','selection_eligible')}])
        lineage[c['candidate_id']] = dict(origin=c['portfolio_origin'],
            parent_candidate_id=c['portfolio_parent_candidate_id'], lineage=c['portfolio_lineage'])
        added.append(c)

    if not d['enabled']:
        return finish('disabled')
    if (args.ground_link_mode != 'optimize' or args.phase_mode != 'unordered'
            or E.has_pose_targets(args) or getattr(args,'panel_bounds',None) is None):
        return finish('unsupported_task')
    if any(c.get('selection_eligible',False) for c in existing):
        return finish('existing_qualified')

    points = target.detach().cpu().reshape(3,2).numpy()
    large, counts = panel_position_seeds.generate(points,args,sample_count=262144)
    d['larger_samples'] = counts['attempted_samples']
    for i,seed in enumerate(large,1):
        retain(evaluate(seed,target,args,reference,f'panel_larger_{i:03d}',
                        'panel_position_larger',LARGER,directory))
    d['larger_candidates'] = len(large)
    if any(c['selection_eligible'] for c in added):
        return finish('larger_qualified')

    near, counts = panel_near_seeds.generate(points,args)
    d['near_samples'] = counts['attempted_samples']
    parents = []
    for i,seed in enumerate(near,1):
        c = evaluate(seed,target,args,reference,f'panel_near_{i:03d}',
                     'panel_position_near_miss',NEAR,directory)
        retain(c);parents.append(c)
    d['near_candidates'] = len(parents)
    if any(c['selection_eligible'] for c in parents):
        return finish('near_qualified')

    for i,(seed,parent) in enumerate(zip(near,parents),1):
        states, counts = panel_refinement.refine(seed,target,args)
        d['refinement_starts'] += 1
        d['adam_steps'] += counts['adam_steps']
        d['lbfgs_evaluations'] += counts['lbfgs_evaluations']
        d['optimizer_failures'] += counts['status'] in ('nonfinite','optimizer_error')
        checked = [evaluate(seed,target,args,reference,f'panel_refined_{i:03d}',
                   'panel_position_refined',REFINED,directory,raw=state,parent=parent['candidate_id']) for state in states]
        best = min(checked, key=lambda c:(not c['selection_eligible'],
                   max(0.,-c['panel_edge_clearance']),c['mean_error']))
        retain(best);d['refined_candidates'] += 1
        if best['selection_eligible']:
            return finish('refined_qualified')
    return finish('exhausted')
