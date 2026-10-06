import math,time
import numpy as np
import torch
from . import model as M

def assess(raw,target):
    q,v,a,_=M.batch_coefficients(torch.tensor(raw[None],dtype=M.F.DT),target['branches'])
    q,v,a=[x.detach().numpy()[0] for x in (q,v,a)]
    tq,tv,ta=[target[k].numpy()[0] for k in ('q','v','a')]
    errors=[np.linalg.norm(q[:,:2]-tq[:,:2],axis=-1).max(),np.degrees(abs(M.F.wrap(q[:,2]-tq[:,2]))).max(),
      np.linalg.norm(v[:,:2]-tv[:,:2],axis=-1).max(),np.linalg.norm(a[:,:2]-ta[:,:2],axis=-1).max(),abs(v[:,2]-tv[:,2]).max(),abs(a[:,2]-ta[:,2]).max()]
    limits=[.01,1,.02,.05,math.radians(2),math.radians(5)]
    task=dict(positions=tq[:,:2].tolist(),orientations_rad=tq[:,2].tolist(),position_tolerance=.01,orientation_tolerance_deg=1.)
    ev=M.F.evaluate(raw,'six',target['branches'][0].numpy().astype(int),1,task)
    finite=bool(np.isfinite(errors).all())
    return dict(pose_pass=bool(ev['qualified']),combined_pass=bool(ev['qualified'] and finite and np.all(np.array(errors)<=limits)),
      errors=[float(x) if np.isfinite(x) else None for x in errors],score=float(max(np.array(errors)/limits)) if finite else 1e9,
      defined='rejection' not in ev)

def random_start(target,seed):
    began=time.perf_counter();rng=np.random.default_rng(seed);pool=[];attempts=0
    p=target['q'][0,:,:2].numpy();a=target['q'][0,:,2].numpy();br=target['branches'][0].numpy().astype(int).tolist()
    while len(pool)<128:
        attempts+=1
        if attempts>20000:raise RuntimeError('Insufficient baseline proposals')
        m=M.F.random_mechanism(rng,'six');m['branches']=br
        try:
            M.F.forward(m,np.linspace(0,2*np.pi,721),'six');s=M.F.forward(m,M.PHASE,'six');z=s['P']-s['P'].mean(0)
            scale=np.sum(z*p)/np.sum(z*z)
            if not .01<scale<20:continue
            shift=-scale*s['P'].mean(0)
            for k in ('O','Q','R'):m[k]=(scale*np.array(m[k])+shift).tolist()
            for k in ('crank','coupler','rocker','extension','output_rocker'):m[k]*=scale
            for k in ('attachment','tool'):m[k]=(scale*np.array(m[k])).tolist()
            delta=a-s['angle'];offset=math.atan2(np.sin(delta).sum(),np.cos(delta).sum());m['mounting']+=offset
            cost=float(np.mean(np.sum((scale*z-p)**2,axis=-1))+.3*np.mean(M.F.wrap(s['angle']+offset-a)**2))
            pool.append((cost,np.array(M.F.encode(m,M.PHASE,'six'))))
        except ValueError:continue
    return min(pool,key=lambda x:x[0])[1],dict(seconds=time.perf_counter()-began,proposals=128,attempts=attempts)
