import math
import numpy as np
import torch
from . import model as M

def calibrate(raw,target,tool=False):
    result=raw.copy();br=target['branches']
    if tool:
        bases=[]
        for x,y in ((0,0),(1,0),(0,1)):
            r=result.copy();r[13:15]=[x,y]
            q,v,a,_=M.batch_coefficients(torch.tensor(r[None],dtype=M.F.DT),br)
            bases.append([z.detach().numpy()[0,:,:2] for z in (q,v,a)])
        matrices=[];rhs=[]
        for j,(key,tol) in enumerate(zip(('q','v','a'),(.01,.02,.05))):
            dx=(bases[1][j]-bases[0][j]).reshape(-1);dy=(bases[2][j]-bases[0][j]).reshape(-1)
            trans=np.tile(np.eye(2),(12,1)) if j==0 else np.zeros((24,2))
            matrices.append(np.column_stack((trans,dx,dy))/tol)
            rhs.append((target[key].numpy()[0,:,:2]-bases[0][j]).reshape(-1)/tol)
        fitted=np.linalg.lstsq(np.vstack(matrices),np.concatenate(rhs),rcond=None)[0]
        for k in (0,2,9):result[k:k+2]+=fitted[:2]
        result[13:15]=fitted[2:]
    q,_,_,_=M.batch_coefficients(torch.tensor(result[None],dtype=M.F.DT),br)
    delta=target['q'][0,:,2].numpy()-q.detach().numpy()[0,:,2]
    result[15]+=math.atan2(np.sin(delta).sum(),np.cos(delta).sum())
    return result
