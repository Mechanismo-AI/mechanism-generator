import math
import numpy as np
import torch
from . import model as M
from . import qualification as T
from . import continuation as S

def fallback_refine(raw,target):
    """Check best objective candidate at 50; continue SAME LBFGS call to 100."""
    x=torch.tensor(raw[:16],dtype=M.F.DT,requires_grad=True);tail=torch.zeros(13,dtype=M.F.DT)
    best=raw.copy();bestval=float('inf');used=0;reason='optimizer_returned';checks=[]
    opt=torch.optim.LBFGS([x],lr=.5,max_iter=150,max_eval=100,tolerance_grad=1e-10,tolerance_change=1e-12,line_search_fn='strong_wolfe')
    class Stop(Exception):pass
    def closure():
        nonlocal best,bestval,used,reason
        if used>=100:reason='evaluation_limit';raise Stop()
        used+=1;opt.zero_grad();full=torch.cat((x,tail))[None]
        q,v,a,_=M.batch_coefficients(full,target['branches'])
        loss=((q[...,:2]-target['q'][...,:2])/.01).square().sum(-1).mean()+2*(1-torch.cos(q[...,2]-target['q'][...,2])).mean()/math.radians(1)**2
        loss+=((v[...,:2]-target['v'][...,:2])/.02).square().sum(-1).mean()+((a[...,:2]-target['a'][...,:2])/.05).square().sum(-1).mean()
        loss+=((v[...,2]-target['v'][...,2])/math.radians(2)).square().mean()+((a[...,2]-target['a'][...,2])/math.radians(5)).square().mean()
        _,_,pen=M.F.tforward(full,'six',target['branches'],torch.linspace(0,2*np.pi,181,dtype=M.F.DT)[None])
        loss+=10000*(pen.mean()+pen.max())
        if not torch.isfinite(loss):reason='nonfinite_loss';raise Stop()
        loss.backward()
        if not torch.isfinite(x.grad).all():reason='nonfinite_gradient';raise Stop()
        val=float(loss.detach())
        if val<bestval:bestval=val;best=full.detach().numpy()[0].copy()
        if used==50:
            metrics=T.assess(best,target);checks.append(dict(evaluations=used,metrics=metrics))
            if metrics['combined_pass']:reason='qualified_at_50';raise Stop()
        return loss
    try:opt.step(closure)
    except Stop:pass
    except RuntimeError as exc:reason='optimizer_error: '+str(exc)
    metrics=T.assess(best,target)
    if not checks or checks[-1]['evaluations']!=used:checks.append(dict(evaluations=used,metrics=metrics))
    return best,dict(evaluations=used,reason=reason,checks=checks,metrics=metrics)

def learned_refine(raw,target,model,cap=200,objective="mean",stop_on_pass=True):
    """Check best objective candidate at 50; continue SAME LBFGS call to 100."""
    x=torch.tensor(raw[:16],dtype=M.F.DT,requires_grad=True);tail=torch.zeros(13,dtype=M.F.DT)
    best=raw.copy();bestval=float('inf');used=0;reason='optimizer_returned';checks=[]
    opt=torch.optim.LBFGS([x],lr=.5,max_iter=cap,max_eval=cap,tolerance_grad=1e-10,tolerance_change=1e-12,line_search_fn='strong_wolfe')
    class Stop(Exception):pass
    def closure():
        nonlocal best,bestval,used,reason
        if used>=cap:reason='evaluation_limit';raise Stop()
        used+=1;opt.zero_grad();full=torch.cat((x,tail))[None]
        q,v,a,_=M.batch_coefficients(full,target['branches'])
        loss=((q[...,:2]-target['q'][...,:2])/.01).square().sum(-1).mean()+2*(1-torch.cos(q[...,2]-target['q'][...,2])).mean()/math.radians(1)**2
        loss+=((v[...,:2]-target['v'][...,:2])/.02).square().sum(-1).mean()+((a[...,:2]-target['a'][...,:2])/.05).square().sum(-1).mean()
        loss+=((v[...,2]-target['v'][...,2])/math.radians(2)).square().mean()+((a[...,2]-target['a'][...,2])/math.radians(5)).square().mean()
        _,_,pen=M.F.tforward(full,'six',target['branches'],torch.linspace(0,2*np.pi,181,dtype=M.F.DT)[None])
        if objective=='worst':
            e=torch.cat((((q[...,:2]-target['q'][...,:2])/.01).square().sum(-1).reshape(-1),
              (2*(1-torch.cos(q[...,2]-target['q'][...,2]))/math.radians(1)**2).reshape(-1),
              ((v[...,:2]-target['v'][...,:2])/.02).square().sum(-1).reshape(-1),
              ((a[...,:2]-target['a'][...,:2])/.05).square().sum(-1).reshape(-1),
              ((v[...,2]-target['v'][...,2])/math.radians(2)).square().reshape(-1),
              ((a[...,2]-target['a'][...,2])/math.radians(5)).square().reshape(-1)))
            loss=.25*loss+e.max()
        loss+=10000*(pen.mean()+pen.max())
        if not torch.isfinite(loss):reason='nonfinite_loss';raise Stop()
        loss.backward()
        if not torch.isfinite(x.grad).all():reason='nonfinite_gradient';raise Stop()
        val=float(loss.detach())
        if val<bestval:bestval=val;best=full.detach().numpy()[0].copy()
        if used%50==0:
            metrics=T.assess(best,target);checks.append(dict(evaluations=used,metrics=metrics,raw=best.tolist()))
            if stop_on_pass and metrics['combined_pass']:reason='qualified';raise Stop()
            if used==100:
                decision=S.choose(model,checks)
                checks[-1]['continue_decision']=decision
                if not decision:reason='restart_selected_at100';raise Stop()
        return loss
    try:opt.step(closure)
    except Stop:pass
    except RuntimeError as exc:reason='optimizer_error: '+str(exc)
    metrics=T.assess(best,target)
    if not checks or checks[-1]['evaluations']!=used:checks.append(dict(evaluations=used,metrics=metrics,raw=best.tolist()))
    return best,dict(evaluations=used,reason=reason,checks=checks,metrics=metrics)
