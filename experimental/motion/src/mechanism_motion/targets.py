import numpy as np
import torch
from . import model as M

def target_from_payload(payload):
    """Only requested motion and branches enter inference; no witness geometry."""
    theta=np.asarray(payload['theta_rad'],float)
    if theta.shape!=(12,) or not np.allclose(theta,M.PHASE,rtol=0,atol=1e-10):
        raise ValueError('Requires twelve equally spaced increasing crank angles starting at zero')
    arrays={k:np.asarray(payload[k],float) for k in ('q','v','a')}
    if any(x.shape!=(12,3) or not np.isfinite(x).all() for x in arrays.values()):
        raise ValueError('q, v and a must each contain twelve finite [x,y,angle] rows')
    p=arrays['q'][:,:2]
    if np.max(abs(p.mean(0)))>1e-8 or abs(np.linalg.norm(np.ptp(p,axis=0))-1)>1e-8:
        raise ValueError('Position targets must be centered and normalized to unit bounding-box diagonal')
    br=np.asarray(payload['branches'],float)
    if br.shape!=(2,) or not np.isin(br,[-1,1]).all():raise ValueError('Requires two known assembly branch signs')
    data={k:torch.tensor(x[None],dtype=M.F.DT) for k,x in arrays.items()}
    data['branches']=torch.tensor(br[None],dtype=M.F.DT)
    q,v,a=(data[k] for k in ('q','v','a'))
    data['features']=torch.cat((q[...,:2],torch.cos(q[...,2:3]),torch.sin(q[...,2:3]),v[...,:2],a[...,:2],v[...,2:3],a[...,2:3]),-1).reshape(1,120)
    data['features']=torch.cat((data['features'],data['branches']),-1)
    return data
