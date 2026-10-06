import math
import numpy as np
from . import continuation as D

LIMITS=D.LIMITS

FEATURES=['log_score',*[f'log_error_{i}' for i in range(6)],'defined',*[f'log_length_{i}' for i in (4,5,6,11,12)],'log_ground','log_attachment_length','log_attachment_height','log_tool_length','log_crank_ground_ratio','log_tool_ground_ratio','random','offset_sin','offset_cos']

def features(initial_raw,before,label):
    r=np.asarray(initial_raw,float);errors=np.array([1e9 if e is None else float(e) for e in before['errors']]);score=float(before['score'])
    assert r.shape==(29,) and np.isfinite(r).all() and errors.shape==(6,)
    mismatch=np.log1p(np.clip(np.r_[score,errors/LIMITS],0,1e9))
    ground=max(float(np.linalg.norm(r[:2]-r[2:4])),1e-12);attachment=float(np.linalg.norm(r[7:9]));tool=float(np.linalg.norm(r[13:15]));random=label=='random';offset=0 if random else int(label.removeprefix('offset'))*math.pi/4
    x=np.r_[mismatch,float(before['defined']),r[[4,5,6,11,12]],np.log1p([ground,attachment,abs(r[8]),tool,math.exp(float(r[4]))/ground,tool/ground]),float(random),math.sin(offset),math.cos(offset)]
    assert len(x)==len(FEATURES) and np.isfinite(x).all();return x

def probabilities(model,x):
    if model['feature_names']!=FEATURES:raise ValueError('Chooser schema mismatch')
    z=(np.asarray(x)-np.array(model['mean']))/np.array(model['scale']);s=z@np.array(model['coefficients'])+model['intercept'];return 1/(1+np.exp(-np.clip(s,-40,40)))

def choose(model,rows):
    p=probabilities(model,np.array([features(r['initial_raw'],r['before'],r['label']) for r in rows]))
    # Candidate order is random then offsets -4..3; stable ties keep that order.
    return int(np.argmax(p))
