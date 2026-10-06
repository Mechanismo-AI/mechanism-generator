import math,time
import numpy as np
import torch
from . import assets,calibration,chooser,kinematics,model,qualification,refinement,targets
KEYS={'theta_rad','branches','q','v','a'}
def validate(payload):
    if not isinstance(payload,dict) or set(payload)!=KEYS:raise ValueError('Input must contain exactly theta_rad, branches, q, v and a')
    def numbers(value, shape, name):
        if shape:
            if not isinstance(value,list) or len(value)!=shape[0]:raise ValueError(f'{name} must have shape {shape}')
            for item in value:numbers(item,shape[1:],name)
        elif isinstance(value,bool) or not isinstance(value,(int,float)):
            raise ValueError(f'{name} must contain JSON numbers')
        else:
            try:finite=math.isfinite(value)
            except OverflowError:finite=False
            if not finite:raise ValueError(f'{name} must contain finite numbers')
    for name,shape in [('theta_rad',(12,)),('branches',(2,)),('q',(12,3)),('v',(12,3)),('a',(12,3))]:numbers(payload[name],shape,name)
    return targets.target_from_payload(payload)
def proposal(target,net,stats):
    with torch.no_grad():raw=net(target['features'],stats,'derivative').numpy()[0]
    if not np.isfinite(raw).all():raise ValueError('Nonfinite proposal')
    return raw
def solve(payload,random_seed=580000000,use_chooser=True):
    if isinstance(random_seed,bool) or not isinstance(random_seed,int) or random_seed<0 or random_seed>2**63-1:raise ValueError('random_seed must be an integer from 0 through 2^63-1')
    if not isinstance(use_chooser,bool):raise ValueError('use_chooser must be boolean')
    target=validate(payload);net,stats,continuation,candidate_model,manifest=assets.load();start=time.perf_counter();issues=[];pool=[];selected_label=None
    raw=proposal(target,net,stats);best,d=refinement.learned_refine(raw,target,continuation);runs=[dict(initializer='original',raw=best.tolist(),**d)]
    if not d['metrics']['combined_pass'] and d['evaluations']<=100:
        try:
            raw,info=qualification.random_start(target,random_seed);pool.append(dict(label='random',initial_raw=raw.tolist(),before=qualification.assess(raw,target)))
        except RuntimeError as exc:
            if str(exc)!='Insufficient baseline proposals':raise
            issues.append('Random proposal limit reached')
        if use_chooser:
            for k in range(-4,4):
                shifted=dict(theta_rad=model.PHASE.tolist(),branches=target['branches'][0].tolist(),**{key:target[key][0].tolist() for key in ('q','v','a')})
                for q in shifted['q']:q[2]-=k*math.pi/4
                raw=calibration.calibrate(proposal(targets.target_from_payload(shifted),net,stats),target,tool=False)
                pool.append(dict(label=f'offset{k:+d}',initial_raw=raw.tolist(),before=qualification.assess(raw,target)))
        if pool:
            scores=chooser.probabilities(candidate_model,np.array([chooser.features(r['initial_raw'],r['before'],r['label']) for r in pool])) if use_chooser else np.array([0.])
            index=chooser.choose(candidate_model,pool) if use_chooser else 0
            for candidate,score in zip(pool,scores):candidate['ranking_prediction']=float(score)
            selected=pool[index];selected_label=selected['label'];best,d=refinement.fallback_refine(np.array(selected['initial_raw']),target)
            runs.append(dict(initializer=selected_label,raw=best.tolist(),**d))
    selected=min(runs,key=lambda r:(not r['metrics']['combined_pass'],r['metrics']['score']));used=sum(r['evaluations'] for r in runs)
    if used>200:raise RuntimeError('Refinement budget exceeded')
    mechanism,phases=kinematics.decode(selected['raw'],'six',payload['branches'],1)
    return dict(schema_version=1,status='experimental',qualified=selected['metrics']['combined_pass'],objective_evaluations=used,maximum_objective_evaluations=200,mechanism_normalized=mechanism,phases_rad=phases.tolist(),selected=selected,runs=runs,pool=pool,selected_label=selected_label,issues=issues,random_seed=random_seed,use_chooser=use_chooser,seconds=time.perf_counter()-start,
      asset_sha256=manifest['files'],convention='q, v and a are pose and first/second derivatives with respect to increasing crank angle in radians; spatial values use the input normalized length unit.',capacity='unrated',operating_speed='unrated',collision_clearance='unchecked')
