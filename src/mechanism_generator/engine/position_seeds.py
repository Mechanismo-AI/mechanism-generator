"""Budget-neutral optional geometric initialization for unordered positions."""
from dataclasses import replace
import math
import time
import torch
from . import r25b as E


def allocate(starts, target, args, target_index):
    """Replace at most four non-balanced variable starts; preserve all others.

    Unsupported tasks and disabled calls return the original objects unchanged.
    Selected slots keep their original refinement profile and assembly branch.
    """
    diagnostics = dict(method='coupled_position_seed_v1', replaced=0, attempts=0,
                       replacements=[], enabled=bool(getattr(args, 'position_geometry', False)))
    if not diagnostics['enabled']:
        diagnostics['status'] = 'disabled'
        return list(starts), diagnostics
    if (args.ground_link_mode != 'optimize' or args.phase_mode != 'unordered'
            or E.has_pose_targets(args) or getattr(args, 'panel_bounds', None) is not None):
        diagnostics['status'] = 'unsupported_task'
        return list(starts), diagnostics
    # Cross-profile portfolios prefer balanced-objective slots. Paired portfolios
    # retain their path/transmission profiles. Each role/branch gets at most one.
    eligible = sorted((i for i,s in enumerate(starts)
                       if s.model_role != 'balanced' and s.perturbation_index == 0),
                      key=lambda i: (starts[i].profile != 'balanced', i))
    slots, seen = [], set()
    for i in eligible:
        key = (starts[i].model_role, starts[i].branch_sign)
        if key not in seen:
            slots.append(i); seen.add(key)
        if len(slots) == 4:
            break
    slots.sort()
    result = list(starts)
    space = E.target_design_space(target, args)
    lo, hi = space['moving_min'], space['moving_max']
    generator = torch.Generator(device='cpu').manual_seed(args.seed + 2026100137 + target_index * 100000)
    grid = torch.linspace(0, 2*math.pi, 722, dtype=target.dtype, device=target.device)[:-1]
    cosine = math.cos(math.radians(15.1))
    started = time.perf_counter()
    for slot in slots:
        original = starts[slot]
        candidate = None
        while diagnostics['attempts'] < 20000:
            diagnostics['attempts'] += 1
            u = torch.rand(9, generator=generator, dtype=torch.float64).to(target)
            ground = space['ground_min'] + u[0]*(space['ground_max']-space['ground_min'])
            raw = lo + u[1:4]*(hi-lo)
            a = raw[1]
            b = torch.minimum(raw[2], torch.maximum(ground,a))
            near = torch.sqrt((a-b).square()+2*a*b*(1-cosine))
            far = torch.sqrt((a-b).square()+2*a*b*(1+cosine))
            cap = torch.stack((ground-near,far-ground,a,b,ground,hi)).min()-1e-7
            if cap < lo:
                continue
            crank = torch.minimum(raw[0],cap)
            p = torch.stack((ground,crank,a,b,u[4],E.MIN_BAR_LEN+u[5]*(space['bar_max']-E.MIN_BAR_LEN),u[6]*0,u[7]*0,u[8]*2*math.pi))
            sim = E.simulate_four_bar(p[None],grid,original.branch_sign)
            if not bool(sim['full_cycle_valid'][0] and sim['valid'].all()):
                continue
            xy = torch.stack((sim['Px'][0],sim['Py'][0]),-1)
            shift = space['centroid']-xy.mean(0)
            p[6] = shift[0].clamp(space['base_x_min'],space['base_x_max'])
            p[7] = shift[1].clamp(space['base_y_min'],space['base_y_max'])
            phases = E.seed_target_phases(p,target,original.branch_sign,args.seed_phase_steps,args)
            encoded = E.encode_refinement_variables(p,phases,target,args.phase_mode,args)
            decoded,phases = E.decode_refinement_variables(encoded,target,args.phase_mode,args)
            checked = E.simulate_four_bar(decoded[None],grid,original.branch_sign)
            if not bool(checked['full_cycle_valid'][0] and checked['valid'].all()):
                continue
            candidate = replace(original,candidate_id=f'geometry_{slot:03d}',model_role='geometric_position',
                                checkpoint_variant='analytic_no_weights',checkpoint_epoch=None,
                                raw_initial=encoded,initial_params=decoded.detach(),initial_phases=phases.detach())
            break
        if candidate is not None:
            result[slot] = candidate
            diagnostics['replacements'].append(dict(slot=slot,original_id=original.candidate_id,
                original_role=original.model_role,new_id=candidate.candidate_id,
                branch=original.branch_sign,profile=original.profile))
            diagnostics['replaced'] += 1
    diagnostics.update(status='allocated' if diagnostics['replaced'] else 'unchanged',
                       generation_seconds=time.perf_counter()-started)
    assert len(result) == len(starts)
    return result, diagnostics
