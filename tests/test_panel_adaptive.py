import copy,json
from pathlib import Path
import pytest
np=pytest.importorskip('numpy')
torch=pytest.importorskip('torch')
from mechanism_generator.engine import r25c,r25b as E,panel,panel_adaptive as A,panel_refinement as F
from mechanism_generator.contributions import bundle as B

def setup():
    task=json.loads((Path(__file__).resolve().parents[1]/'examples/benchmarks/adaptive-panel-development.json').read_text(encoding='utf-8'))
    args=r25c.build_parser().parse_args(['--panel_position_adaptive','--headless','--no_plots'])
    args.panel_bounds=task['panel_bounds'];args.carrier_size=task['carrier_size'];args.panel_pivot_clearance=task['clearance']
    r25c.validate_args(r25c.build_parser(),args)
    target=torch.tensor(task['targets'],dtype=torch.float64).flatten()
    ref=dict(reference_candidate_id='base',reference_acquired_mean_error=0.,reference_acquired_errors=[0.]*3,shared_mean_budget=.02,shared_point_budgets=[.05]*3)
    return task,args,target,ref

@pytest.mark.parametrize('change,status',[(('panel_position_adaptive',False),'disabled'),(('phase_mode','ordered'),'unsupported_task'),(('target_orientations_deg',[0,0,0]),'unsupported_task'),(('panel_bounds',None),'unsupported_task'),(None,'existing_qualified')])
def test_skip_does_not_sample_or_mutate_existing(tmp_path,monkeypatch,change,status):
    _,args,target,ref=setup()
    if change:setattr(args,*change)
    old=[{'selection_eligible':True,'candidate_id':'preserve_me'}];before=copy.deepcopy(old)
    def fail(*a,**k):raise AssertionError('Unneeded work')
    monkeypatch.setattr(A.panel_position_seeds,'generate',fail)
    monkeypatch.setattr(A.panel_near_seeds,'generate',fail)
    monkeypatch.setattr(F,'refine',fail)
    rng=torch.random.get_rng_state().clone()
    extra,d=A.run(target,args,ref,old,tmp_path/'unused',{})
    assert old==before and extra==[] and d['status']==status
    assert not (tmp_path/'unused').exists() and torch.equal(rng,torch.random.get_rng_state())

@pytest.mark.parametrize('failure',['nonfinite','optimizer_error'])
def test_optimizer_failure_returns_preserved_parent(monkeypatch,failure):
    _,args,target,_=setup();near,_=A.panel_near_seeds.generate(target.reshape(3,2).numpy(),args)
    def bad(raw,*a):
        if failure=='optimizer_error':raise RuntimeError('numerical failure')
        return raw.sum()*float('nan')
    monkeypatch.setattr(F,'objective',bad)
    states,d=F.refine(near[0],target,args)
    assert d['status']==failure and d['adam_steps']==d['lbfgs_evaluations']==0
    assert states and all(torch.isfinite(s).all() for s in states)

def test_line_search_cannot_exceed_hard_evaluation_budget(monkeypatch):
    _,args,target,_=setup();near,_=A.panel_near_seeds.generate(target.reshape(3,2).numpy(),args)
    monkeypatch.setattr(F,'objective',lambda raw,*a:raw.square().sum()*0.)
    class UnboundedLineSearch:
        def __init__(self,parameters,**kwargs):self.parameters=parameters
        def zero_grad(self):
            for p in self.parameters:p.grad=None
        def step(self,closure):
            for _ in range(1000):closure()
    monkeypatch.setattr(torch.optim,'LBFGS',UnboundedLineSearch)
    states,d=F.refine(near[0],target,args)
    assert d['status']=='budget_exhausted' and d['lbfgs_evaluations']==150 and d['adam_steps']==400
    assert states

def test_real_repair_retains_parent_and_survives_selection_and_bundle(tmp_path):
    _,args,target,ref=setup();lineage={}
    candidates,d=A.run(target,args,ref,[],tmp_path/'history',lineage)
    assert d['status']=='refined_qualified'
    assert d['larger_samples']==262144 and d['near_samples']==65536
    assert 1<=d['refinement_starts']<=6
    assert d['adam_steps']<=400*d['refinement_starts'] and d['lbfgs_evaluations']<=150*d['refinement_starts']
    children=[c for c in candidates if c['portfolio_origin']=='panel_position_refined']
    ids={c['candidate_id'] for c in candidates}
    assert all(c['portfolio_parent_candidate_id'] in ids for c in children)
    args.top_k=1;chosen,fallback=E.select_diverse_candidates(candidates,args)
    assert len(chosen)==1 and not fallback and chosen[0]['selection_eligible']
    E.save_candidate_artifacts(chosen[0],1,tmp_path,args)
    E.write_csv(tmp_path/'all_candidates.csv',[E.flat_candidate_row(c) for c in candidates])
    task=dict(directory='.',target_values=target.tolist(),crank_direction=args.crank_direction,panel=panel.configuration(args),
              panel_adaptive_initialization=d,candidate_count=len(candidates),selected_count=1)
    for field in ('path_acceptable','selection_eligible','engineering_acceptable','panel_acceptable'):
        task[field+'_count']=sum(c[field] for c in candidates)
    (tmp_path/'run_manifest.json').write_text(json.dumps(dict(variant='R2.5c',run_status='completed',targets=[task],arguments=vars(args),models=[])),encoding='utf-8')
    bundle=B.build_bundle(tmp_path);assert bundle['schema_version']=='0.8'
    assert bundle['task'][0]['panel_adaptive_initialization']['refinement_starts']==d['refinement_starts']
    for field,value in [('enabled',False),('near_samples',0),('refinement_starts',0),('source_sha256','f'*64),('status','existing_qualified')]:
        bad=copy.deepcopy(bundle);bad['task'][0]['panel_adaptive_initialization'][field]=value
        with pytest.raises(ValueError):B.validate_bundle(bad)
    bad=copy.deepcopy(bundle)
    child=next(c for c in bad['candidates'][0]['items'] if c['portfolio_origin']=='panel_position_refined')
    child.pop('portfolio_parent_candidate_id')
    with pytest.raises(ValueError):B.validate_bundle(bad)
