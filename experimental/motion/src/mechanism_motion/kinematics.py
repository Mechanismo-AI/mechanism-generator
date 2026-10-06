import math
import numpy as np
import torch
from . import simulation as N
DT=torch.float64

def wrap(a):return np.arctan2(np.sin(a),np.cos(a))

def forward(m,theta,family):
    if family=='six':s=N.simulate(m,theta)
    else:
        A=np.array(m['O'])+m['crank']*np.column_stack((np.cos(theta),np.sin(theta)))
        B=N.circle(A,m['Q'],m['coupler'],m['rocker'],m['branches'][0]);u=(B-A)/m['coupler']
        s=dict(A=A,B=B,O=np.broadcast_to(m['O'],A.shape),Q=np.broadcast_to(m['Q'],A.shape),
               P=A+m['tool'][0]*u+m['tool'][1]*N.perp(u),angle=np.arctan2(u[:,1],u[:,0]))
    s['angle']=s['angle']+m.get('mounting',0.)
    return s

def random_mechanism(rng,family):
    m=dict(O=[0.,0.],Q=[float(rng.uniform(3.5,5)),0.],crank=float(rng.uniform(.4,1.1)),
           coupler=float(rng.uniform(3,4.5)),rocker=float(rng.uniform(2.5,4)),mounting=0.,
           tool=rng.uniform([.5,-.8],[2.5,.8]).tolist(),branches=[int(rng.choice([-1,1])),int(rng.choice([-1,1]))])
    if family=='six':m.update(R=rng.uniform([-2,-2],[6,4]).tolist(),attachment=rng.uniform([1,.3],[3,1.3]).tolist(),
                             extension=float(rng.uniform(2.5,5)),output_rocker=float(rng.uniform(2.5,5)))
    return m

def normalized(task):
    p=np.asarray(task['positions'],float);center=p.mean(0);scale=np.linalg.norm(np.ptp(p,axis=0))
    if p.shape!=(12,2) or scale<=1e-9 or not np.isfinite(p).all():raise ValueError('Expected 12 finite distinct poses')
    a=np.asarray(task['orientations_rad'],float)
    if a.shape!=(12,) or not np.isfinite(a).all():raise ValueError('Expected 12 directed angles')
    return (p-center)/scale,a,center,scale

def encode(m,theta,family):
    x=[*m['O'],*m['Q'],*np.log([m['crank'],m['coupler'],m['rocker']])]
    if family=='six':x += [*m['attachment'],*m['R'],math.log(m['extension']),math.log(m['output_rocker'])]
    x += [*m['tool'],m['mounting'],theta[0],*np.zeros(12)]
    return x

def decode(x,family,branches,direction):
    x=np.asarray(x);m=dict(O=x[:2].tolist(),Q=x[2:4].tolist(),crank=float(np.exp(np.clip(x[4],-5,4))),
          coupler=float(np.exp(np.clip(x[5],-5,4))),rocker=float(np.exp(np.clip(x[6],-5,4))),branches=list(map(int,branches)))
    if family=='six':
        m.update(attachment=x[7:9].tolist(),R=x[9:11].tolist(),extension=float(np.exp(np.clip(x[11],-5,4))),output_rocker=float(np.exp(np.clip(x[12],-5,4))));i=13
    else:i=7
    m.update(tool=x[i:i+2].tolist(),mounting=float(x[i+2]));g=x[i+4:];g=np.exp(g-g.max());g/=g.sum()
    theta=x[i+3]+direction*2*np.pi*np.r_[0,np.cumsum(g)[:-1]]
    return m,theta

def tp(x):return torch.stack((-x[...,1],x[...,0]),dim=-1)

def tcircle(a,b,r,s,sign):
    delta=b-a;d=torch.linalg.vector_norm(delta,dim=-1).clamp_min(1e-8);u=delta/d[...,None]
    along=(r*r-s*s+d*d)/(2*d);h2=r*r-along*along
    point=a+along[...,None]*u+sign[...,None]*torch.sqrt(h2.clamp_min(1e-10))[...,None]*tp(u)
    cosine=(r*r+s*s-d*d)/(2*r*s)
    penalty=torch.relu((r-s).abs()+.015-d).square()+torch.relu(d+.015-r-s).square()
    penalty=penalty+torch.relu(cosine.abs()-math.cos(math.radians(16))).square()
    return point,penalty

def tforward(x,family,branches,theta):
    O=x[:,None,:2];Q=x[:,None,2:4];l=torch.exp(x[:,4:7].clamp(-5,4));r,c,k=(l[:,j,None] for j in range(3))
    A=O+r[...,None]*torch.stack((torch.cos(theta),torch.sin(theta)),dim=-1)
    B,pen=tcircle(A,Q,c,k,branches[:,0,None]);u=(B-A)/c[...,None]
    if family=='six':
        D=A+x[:,None,7,None]*u+x[:,None,8,None]*tp(u);R=x[:,None,9:11]
        e=torch.exp(x[:,11,None].clamp(-5,4));h=torch.exp(x[:,12,None].clamp(-5,4))
        C,more=tcircle(D,R,e,h,branches[:,1,None]);u=(C-D)/e[...,None];A=D;pen=pen+more;i=13
    else:i=7
    P=A+x[:,None,i,None]*u+x[:,None,i+1,None]*tp(u)
    angle=torch.atan2(u[...,1],u[...,0])+x[:,None,i+2]
    return P,angle,pen

def evaluate(x,family,branches,direction,task):
    m,ph=decode(x,family,branches,direction);p,a,center,scale=normalized(task)
    result=dict(mechanism_normalized=m,phases_rad=ph.tolist(),direction=int(direction),normalization=dict(center=center.tolist(),scale=float(scale)),qualified=False)
    try:
        fit=forward(m,ph,family);full=forward(m,np.linspace(0,2*np.pi,7201),family)
        pos=np.linalg.norm(fit['P']-p,axis=-1);ang=np.degrees(np.abs(wrap(fit['angle']-a)))
        if family=='six':audit=N.audit(m,full);tx=min(audit['minimum_transmission_deg']);res=audit['max_length_residual'];regular=audit['min_driven_singular_value']>1e-4
        else:
            v=full['A']-full['B'];w=full['Q']-full['B'];cos=np.sum(v*w,axis=-1)/(np.linalg.norm(v,axis=-1)*np.linalg.norm(w,axis=-1))
            tx=float(np.degrees(np.arccos(np.clip(abs(cos),0,1))).min())
            res=max(float(np.max(abs(np.linalg.norm(full[b]-full[c],axis=-1)-m[k]))) for b,c,k in [('A','O','crank'),('B','A','coupler'),('B','Q','rocker')]);regular=tx>0
            audit=dict(max_length_residual=res,minimum_transmission_deg=[tx])
        lengths=[m[k] for k in ('crank','coupler','rocker')+(('extension','output_rocker') if family=='six' else ())]
        vals=np.concatenate([np.array(m[k]).reshape(-1) for k in ('O','Q','tool')+(('R','attachment') if family=='six' else ())])
        bounded=min(lengths)>=.05 and max(lengths)<=20 and np.max(np.abs(vals))<=20 and np.linalg.norm(np.array(m['O'])-m['Q'])>=.05
        if family=='six':bounded=bounded and abs(m['attachment'][1])>=.02
        gaps=np.diff(np.r_[0,(ph-ph[0])*direction,2*np.pi])[1:]/(2*np.pi)
        qualified=bounded and regular and res<1e-8 and tx>=15 and min(gaps)>=.002 and pos.max()<=task['position_tolerance'] and ang.max()<=task['orientation_tolerance_deg']
        result.update(qualified=bool(qualified),maximum_position_error=float(pos.max()),rms_position_error=float(np.sqrt(np.mean(pos*pos))),maximum_orientation_error_deg=float(ang.max()),audit=audit,bounded=bool(bounded),minimum_phase_gap_fraction=float(min(gaps)),score=float(max(pos.max()/task['position_tolerance'],ang.max()/task['orientation_tolerance_deg'])))
    except (ValueError,FloatingPointError):result['rejection']='undefined assembly'
    return result
