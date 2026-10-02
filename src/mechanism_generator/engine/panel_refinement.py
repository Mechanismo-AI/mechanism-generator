"""Bounded panel-aware optimization; callers qualify all returned snapshots."""
import math
import torch
from . import r25b as E

def vertices(p,theta,branch,carrier):
    sim=E.simulate_four_bar(p[None],theta,branch)
    def xy(x,y):return torch.stack((sim[x][0],sim[y][0]),dim=-1)
    a,b,center=xy('Ax','Ay'),xy('Bx','By'),xy('Px','Py')
    direction=(b-a)/p[2];normal=torch.stack((-direction[:,1],direction[:,0]),dim=-1)
    corners=[center+sx*carrier[0]*.5*direction+sy*carrier[1]*.5*normal for sx in (-1,1) for sy in (-1,1)]
    pivots=torch.stack((xy('O2x','O2y')[0],xy('O4x','O4y')[0]))
    return torch.cat([a,b,pivots,*corners]),pivots,sim

def objective(raw,target,args,branch,theta):
    p,ph=E.decode_refinement_variables(raw,target,'unordered',args)
    scale=E.target_design_space(target,args)['scale']
    v,pivots,sim=vertices(p,theta,branch,args.carrier_size)
    xmin,xmax,ymin,ymax=args.panel_bounds
    low=raw.new_tensor([xmin,ymin]);high=raw.new_tensor([xmax,ymax]);margin=.002*scale
    edge=torch.cat(((low+margin-v).flatten(),(v-high+margin).flatten()))/scale
    pivot=torch.cat(((low+args.panel_pivot_clearance+margin-pivots).flatten(),(pivots-high+args.panel_pivot_clearance+margin).flatten()))/scale
    panel_loss=torch.relu(edge).square().max()+torch.relu(pivot).square().max()
    at=E.simulate_four_bar(p[None],ph,branch)
    xy=torch.stack((at['Px'][0],at['Py'][0]),dim=-1)
    errors=(xy-target.reshape(3,2))/scale
    path=errors.square().sum(-1).mean()+errors.square().sum(-1).max()
    constraints=E.mechanism_constraint_tensors(p[None],scale,args)
    robust=E.robustness_terms(p,sim,constraints,scale,args)['penalty']
    l1,l2,l3,l4=p[:4]
    d2=torch.stack(((l1-l2).square(),(l1+l2).square()))
    cos=(l3.square()+l4.square()-d2)/(2*l3*l4)
    # Analytic whole-cycle extrema, with a one-degree cushion over the hard floors.
    tx=torch.relu(cos.abs()-math.cos(math.radians(args.minimum_global_transmission+1))).square().sum()
    tq=math.sin(math.radians(args.minimum_target_transmission+1))**2
    tx=tx+torch.relu(tq-at['transmission_q'][0]).square().sum()
    return path+4*panel_loss+10*robust+10*tx


class _StopOptimization(Exception):
    pass


def refine(seed, target, args):
    """Return preserved snapshots under hard step/evaluation limits, even on failure."""
    p = torch.tensor(seed['parameters'], dtype=target.dtype, device=target.device)
    phases = torch.tensor(seed['phases_rad'], dtype=target.dtype, device=target.device)
    raw = E.encode_refinement_variables(p, phases, target, 'unordered', args).detach().requires_grad_(True)
    theta = torch.linspace(0, 2*math.pi, 361, dtype=raw.dtype, device=raw.device)
    snapshots = [raw.detach().clone()]
    counts = dict(adam_steps=0, lbfgs_evaluations=0, status='completed')

    def backward(optimizer):
        optimizer.zero_grad()
        loss = objective(raw, target, args, seed['branch_sign'], theta)
        if not torch.isfinite(loss):
            counts['status'] = 'nonfinite'
            raise _StopOptimization
        loss.backward()
        if raw.grad is None or not torch.isfinite(raw.grad).all():
            counts['status'] = 'nonfinite'
            raise _StopOptimization
        return loss

    try:
        adam = torch.optim.Adam([raw], lr=.025)
        for i in range(400):
            backward(adam)
            torch.nn.utils.clip_grad_norm_([raw], 10.)
            adam.step()
            counts['adam_steps'] += 1
            if (i+1) % 50 == 0 and torch.isfinite(raw).all():
                snapshots.append(raw.detach().clone())
        lbfgs = torch.optim.LBFGS([raw], lr=.5, max_iter=100, max_eval=150,
            line_search_fn='strong_wolfe', tolerance_grad=1e-10, tolerance_change=1e-12)

        def closure():
            if counts['lbfgs_evaluations'] >= 150:
                counts['status'] = 'budget_exhausted'
                raise _StopOptimization
            counts['lbfgs_evaluations'] += 1
            return backward(lbfgs)

        lbfgs.step(closure)
    except _StopOptimization:
        pass
    except RuntimeError:
        # Optional numerical failure must not discard existing portfolio results.
        counts['status'] = 'optimizer_error'
    if torch.isfinite(raw).all():
        snapshots.append(raw.detach().clone())
    return snapshots, counts
