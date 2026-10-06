import numpy as np

LINKS = [('O','Q','R'), ('O','A'), ('A','B','D'), ('B','Q'), ('D','C'), ('C','R')]

EDGES = [('O','A'),('A','B'),('B','Q'),('A','D'),('B','D'),('D','C'),('C','R')]

def perp(x): return np.stack((-x[...,1],x[...,0]),axis=-1)

def circle(a,b,r,s,sign):
    if sign not in (-1,1) or min(r,s)<=0: raise ValueError('Invalid radius or branch')
    a,b=np.broadcast_arrays(np.asarray(a,float),np.asarray(b,float))
    delta=b-a;distance=np.linalg.norm(delta,axis=-1)
    if np.any(distance<=1e-12): raise ValueError('Coincident circle centres')
    unit=delta/distance[...,None];along=(r*r-s*s+distance**2)/(2*distance)
    h2=r*r-along**2
    if np.any(h2<=1e-12): raise ValueError('Unreachable or tangent assembly')
    return a+along[...,None]*unit+sign*np.sqrt(h2)[...,None]*perp(unit)

def simulate(m,theta):
    theta=np.asarray(theta,float)
    if not np.isfinite(theta).all(): raise ValueError('Nonfinite phase')
    O,Q,R=(np.asarray(m[k],float) for k in ('O','Q','R'))
    A=O+m['crank']*np.stack((np.cos(theta),np.sin(theta)),axis=-1)
    B=circle(A,Q,m['coupler'],m['rocker'],m['branches'][0])
    u=(B-A)/m['coupler'];D=A+m['attachment'][0]*u+m['attachment'][1]*perp(u)
    C=circle(D,R,m['extension'],m['output_rocker'],m['branches'][1])
    v=(C-D)/m['extension'];P=D+m['tool'][0]*v+m['tool'][1]*perp(v)
    return dict(O=np.broadcast_to(O,A.shape),Q=np.broadcast_to(Q,A.shape),R=np.broadcast_to(R,A.shape),
                A=A,B=B,D=D,C=C,P=P,angle=np.arctan2(v[...,1],v[...,0]))

def audit(m,s):
    """Independent distance constraints and rigidity Jacobian, not circle formulas."""
    lengths=[m['crank'],m['coupler'],m['rocker'],np.linalg.norm(m['attachment']),
             np.linalg.norm(np.array(m['attachment'])-[m['coupler'],0]),m['extension'],m['output_rocker']]
    scale=max(lengths);residual=max(float(np.max(np.abs(np.linalg.norm(s[b]-s[a],axis=-1)-d))) for (a,b),d in zip(EDGES,lengths))
    sigmas=[];driven=[]
    for i in np.linspace(0,len(s['A'])-1,33,dtype=int):
        j=np.zeros((7,8));moving=['A','B','D','C']
        for row,(a,b) in enumerate(EDGES):
            v=(s[b][i]-s[a][i])/np.linalg.norm(s[b][i]-s[a][i])
            if a in moving:j[row,2*moving.index(a):2*moving.index(a)+2]=-v
            if b in moving:j[row,2*moving.index(b):2*moving.index(b)+2]=v
        sigmas.append(np.linalg.svd(j,compute_uv=False)[-1])
        drive=np.zeros(8);drive[:2]=perp((s['A'][i]-s['O'][i])/m['crank'])
        driven.append(np.linalg.svd(np.vstack((j,drive)),compute_uv=False)[-1])
    transmission=[]
    for x,y,z in [('A','B','Q'),('D','C','R')]:
        v=s[x]-s[y];w=s[z]-s[y]
        cosine=np.sum(v*w,axis=-1)/(np.linalg.norm(v,axis=-1)*np.linalg.norm(w,axis=-1))
        transmission.append(float(np.degrees(np.arccos(np.clip(np.abs(cosine),0,1))).min()))
    return dict(max_length_residual=residual,min_constraint_singular_value=float(min(sigmas)),
                min_driven_singular_value=float(min(driven)),minimum_transmission_deg=transmission,
                cycle_return_error=max(float(np.linalg.norm(s[k][-1]-s[k][0])) for k in ('A','B','D','C','P')),
                maximum_sample_step_over_scale=max(float(np.linalg.norm(np.diff(s[k],axis=0),axis=-1).max()/scale) for k in ('A','B','D','C','P')))
