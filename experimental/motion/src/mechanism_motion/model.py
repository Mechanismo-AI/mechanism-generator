import numpy as np
import torch
from . import kinematics as F
PHASE=np.arange(12)*2*np.pi/12

def batch_coefficients(raw,branches):
    theta=torch.tensor(PHASE,dtype=raw.dtype).expand(len(raw),-1).clone().requires_grad_(True)
    p,phi,pen=F.tforward(raw,'six',branches,theta);q=torch.cat((p,phi[...,None]),-1);first=[];second=[]
    for k in range(3):
        v=torch.autograd.grad(q[...,k].sum(),theta,create_graph=True,retain_graph=True)[0]
        a=torch.autograd.grad(v.sum(),theta,create_graph=True,retain_graph=True)[0];first.append(v);second.append(a)
    return q,torch.stack(first,-1),torch.stack(second,-1),pen

class Proposal(torch.nn.Module):
    def __init__(self):
        super().__init__();self.net=torch.nn.Sequential(torch.nn.Linear(122,128),torch.nn.SiLU(),torch.nn.Linear(128,128),torch.nn.SiLU(),torch.nn.Linear(128,16))
        torch.nn.init.zeros_(self.net[-1].weight);torch.nn.init.zeros_(self.net[-1].bias);self.double()
    def forward(self,features,stats,mode):
        x=(features-stats['feature_mean'])/stats['feature_std']
        if mode=='pose':
            x=x.clone();x[:,:120].reshape(-1,12,10)[...,4:]=0
        y=self.net(x);geom=stats['target_mean']+stats['target_std']*y
        # Shared representation: 16 geometric parameters + fixed theta0/gaps.
        return torch.cat((geom,torch.zeros((len(x),13),dtype=x.dtype)),dim=-1)
