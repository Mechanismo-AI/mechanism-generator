import math
import numpy as np

LIMITS=np.array([.01,1.,.02,.05,math.radians(2),math.radians(5)])

FEATURE_NAMES=['log_score100',*[f'log_error100_{i}' for i in range(6)],'log_score_improvement',*[f'log_error_improvement_{i}' for i in range(6)],'defined100','defined50','pose_pass100']

def features(checks):
    if len(checks)!=2 or [c['evaluations'] for c in checks]!=[50,100]:raise ValueError('Requires exactly the 50 and 100 evaluation diagnostics')
    a,b=[c['metrics'] for c in checks]
    def logs(m):
        errors=np.array([1e9 if e is None else float(e) for e in m['errors']]);score=float(m['score'])
        if errors.shape!=(6,) or not np.isfinite(errors).all() or (errors<0).any() or not math.isfinite(score) or score<0:raise ValueError('Invalid diagnostics')
        return np.log1p(np.clip(np.r_[score,errors/LIMITS],0,1e9))
    x,y=logs(a),logs(b)
    return np.r_[y,x-y,float(b['defined']),float(a['defined']),float(b['pose_pass'])]

def probability(model,x):
    if model['feature_names']!=FEATURE_NAMES:raise ValueError('Wrong feature schema')
    z=(np.asarray(x)-np.array(model['mean']))/np.array(model['scale']);score=z@np.array(model['coefficients'])+model['intercept']
    return 1/(1+np.exp(-np.clip(score,-40,40)))

def choose(model,checks):return bool(probability(model,features(checks))>=.5)
