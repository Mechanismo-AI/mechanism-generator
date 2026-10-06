import hashlib,json
from functools import lru_cache
from pathlib import Path
import torch
from .model import Proposal
from . import chooser,continuation
DIRECTORY=Path(__file__).resolve().parent/'assets'
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
@lru_cache(maxsize=1)
def load():
    manifest=json.loads((DIRECTORY/'manifest.json').read_text(encoding='utf-8'))
    if manifest['schema_version']!=1 or set(manifest['files'])!={'proposal.pt','continuation.json','chooser.json'}:raise ValueError('Unsupported asset manifest')
    for name,digest in manifest['files'].items():
        if sha(DIRECTORY/name)!=digest:raise ValueError('Asset checksum mismatch: '+name)
    cp=torch.load(DIRECTORY/'proposal.pt',map_location='cpu',weights_only=True)
    if set(cp)!={'schema_version','model','stats'} or cp['schema_version']!=1:raise ValueError('Unsupported proposal asset')
    stats=cp['stats'];shapes=dict(feature_mean=(122,),feature_std=(122,),target_mean=(16,),target_std=(16,))
    if set(stats)!=set(shapes):raise ValueError('Wrong proposal statistics')
    for name,shape in shapes.items():
        value=stats[name]
        if value.shape!=shape or value.dtype!=torch.float64 or not torch.isfinite(value).all():raise ValueError('Invalid proposal statistics')
        if name.endswith('_std') and not (value>0).all():raise ValueError('Invalid proposal scale')
    if not all(v.dtype==torch.float64 and torch.isfinite(v).all() for v in cp['model'].values()):raise ValueError('Invalid proposal tensors')
    net=Proposal();net.load_state_dict(cp['model'],strict=True);net.eval()
    selectors=[json.loads((DIRECTORY/name).read_text(encoding='utf-8')) for name in ('continuation.json','chooser.json')]
    for model,names in zip(selectors,(continuation.FEATURE_NAMES,chooser.FEATURES)):
        if model['feature_names']!=names:raise ValueError('Wrong selector feature schema')
        import numpy as np
        if len(model['mean'])!=len(names) or len(model['scale'])!=len(names) or len(model['coefficients'])!=len(names):raise ValueError('Wrong selector dimensions')
        if not np.isfinite([*model['mean'],*model['scale'],*model['coefficients'],model['intercept']]).all() or min(model['scale'])<=0:raise ValueError('Invalid selector parameters')
    return net,stats,*selectors,manifest
