"""Panel parents survive real qualification, ranking and artifact export."""
import copy,json
import pytest
np=pytest.importorskip('numpy')
torch=pytest.importorskip('torch')
from mechanism_generator.engine import r25b as E,r25c,panel_position_seeds as seeds,panel
from mechanism_generator.contributions import bundle as B

def setup():
    args=r25c.build_parser().parse_args(['--panel_position_geometry','--headless','--no_plots'])
    args.panel_bounds=[-8.504761812353228,4.105248013726108,-3.287339195381227,8.649791375650194]
    args.carrier_size=[.7786025293563396,.4671615176138037];args.panel_pivot_clearance=.1946506323390849
    target=torch.tensor([-4.6658019174,2.7044757058,-5.0186242864,1.3258305475,-1.2216646372,2.1852750718],dtype=torch.float64)
    reference=dict(reference_candidate_id='baseline',reference_acquired_mean_error=0.,reference_acquired_errors=[0.]*3,
                   shared_mean_budget=.02,shared_point_budgets=[.05]*3)
    return args,target,reference

def test_preserved_parents_qualify_select_and_export(tmp_path):
    args,target,ref=setup();lineage={}
    parents,d=r25c.run_panel_position_geometry(target,args,ref,tmp_path/'seeds',lineage)
    assert len(parents)==d['evaluated_seed_count']==6
    E.apply_shared_candidate_qualification(parents,args,ref)
    assert all(p['selection_eligible'] for p in parents)
    assert all(p['mean_error']<1e-7 and p['panel_acceptable'] for p in parents)
    # Even the smallest output budget must retain a qualifying result.
    args.top_k=1
    selected,fallback=E.select_diverse_candidates(parents,args)
    selected=r25c.ensure_fixed_representatives(selected,[],args)
    assert len(selected)==1 and not fallback and selected[0]['selection_eligible']
    E.save_candidate_artifacts(selected[0],1,tmp_path,args)
    assert list(tmp_path.glob('*.json'))
    assert set(lineage)=={p['candidate_id'] for p in parents}
    again,other=seeds.generate(target.reshape(3,2).numpy(),args)
    original,_=seeds.generate(target.reshape(3,2).numpy(),args)
    assert again==original
    E.write_csv(tmp_path/'all_candidates.csv',[E.flat_candidate_row(c) for c in parents])
    task=dict(directory='.',target_values=target.tolist(),crank_direction=args.crank_direction,
              panel=panel.configuration(args),panel_position_initialization=d,candidate_count=len(parents),selected_count=1)
    for field in ('path_acceptable','selection_eligible','engineering_acceptable','panel_acceptable'):
        task[field+'_count']=sum(c[field] for c in parents)
    (tmp_path/'run_manifest.json').write_text(json.dumps(dict(variant='R2.5c',run_status='completed',targets=[task],arguments=vars(args),models=[])),encoding='utf-8')
    bundle=B.build_bundle(tmp_path)
    assert bundle['schema_version']=='0.7'
    assert bundle['task'][0]['panel_position_initialization']['evaluated_seed_count']==6
    assert all(c['model_role']=='panel_geometry' for c in bundle['candidates'][0]['items'])
    for field,value in [('enabled',False),('panel_passing_count',0),('source_sha256','f'*64),('status','unsupported_task')]:
        broken=copy.deepcopy(bundle);broken['task'][0]['panel_position_initialization'][field]=value
        with pytest.raises(ValueError):B.validate_bundle(broken)
    for field in ('proposal_source','generator_sample_index','panel_required'):
        broken=copy.deepcopy(bundle);broken['candidates'][0]['items'][0].pop(field)
        with pytest.raises(ValueError):B.validate_bundle(broken)

@pytest.mark.parametrize('field,value',[('panel_position_geometry',False),('phase_mode','ordered'),('target_orientations_deg',[0.,0.,0.]),('panel_bounds',None),('ground_link_mode','fixed')])
def test_bypass_does_not_sample_or_change_rng(tmp_path,monkeypatch,field,value):
    args,target,ref=setup();setattr(args,field,value)
    def fail(*a,**k):raise AssertionError('unsupported search sampled')
    monkeypatch.setattr(seeds,'generate',fail)
    before=torch.random.get_rng_state().clone();lineage={}
    parents,d=r25c.run_panel_position_geometry(target,args,ref,tmp_path/'unused',lineage)
    assert parents==[] and not lineage and not (tmp_path/'unused').exists()
    assert torch.equal(before,torch.random.get_rng_state())
    assert d['status']==('disabled' if field=='panel_position_geometry' else 'unsupported_task')

@pytest.mark.parametrize('branches', ['positive','negative'])
def test_requested_branch_is_respected(branches):
    args,target,_=setup();args.branches=branches
    found,_=seeds.generate(target.reshape(3,2).numpy(),args)
    assert found and all(s['branch_sign']==(1 if branches=='positive' else -1) for s in found)

def test_empty_search_and_invalid_inputs():
    args,target,_=setup();args.panel_bounds=[-.01,.01,-.01,.01];args.panel_pivot_clearance=0.
    found,_=seeds.generate(target.reshape(3,2).numpy(),args);assert found==[]
    for kwargs in ({'sample_count':-1},{'sample_count':True},{'max_seeds':7}):
        with pytest.raises(ValueError):seeds.generate(target.reshape(3,2).numpy(),args,**kwargs)
    found,_=seeds.generate([[0.,0.]]*3,args,sample_count=512);assert found==[]
