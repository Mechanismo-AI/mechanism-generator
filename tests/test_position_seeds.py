import copy
import pytest
torch = pytest.importorskip('torch')
from mechanism_generator.engine import r25b as E, r25c, position_seeds

def fixture():
    args=r25c.build_parser().parse_args(['--position_geometry'])
    target=torch.tensor([-2.,2.,-1.5,2.5,-1.,2.2],dtype=torch.float64)
    p=torch.tensor([1.,.2,1.,.8,.4,.15,-2.,2.,.1],dtype=torch.float64)
    phases=E.seed_target_phases(p,target,-1.,721,args)
    raw=E.encode_refinement_variables(p,phases,target,'unordered',args)
    starts=[E.StartSpec(f's{i}',role,role,'test',None,branch,0,raw.clone(),p.clone(),phases.clone())
            for i,(role,branch) in enumerate((r,b) for r in ('balanced','path','transmission') for b in (-1.,1.))]
    return args,target,starts

def test_same_budget_preserved_profiles_and_balanced_starts():
    args,target,starts=fixture()
    result,info=position_seeds.allocate(starts,target,args,0)
    again,other=position_seeds.allocate(starts,target,args,0)
    assert info['replaced']==4 and len(result)==len(starts)==6
    assert result[0] is starts[0] and result[1] is starts[1]
    space=E.target_design_space(target,args)
    for old,new,repeated in zip(starts[2:],result[2:],again[2:]):
        assert old.model_role != 'geometric_position'
        assert old.profile==new.profile and old.branch_sign==new.branch_sign
        assert torch.equal(new.raw_initial,repeated.raw_initial)
        p=new.initial_params
        # Analytic full-turn closure, independent of the simulator's grid.
        assert p[0]+p[1] <= p[2]+p[3]
        assert abs(p[0]-p[1]) >= abs(p[2]-p[3])
        assert p[1] < p[[0,2,3]].min()
        assert space['ground_min']<=p[0]<=space['ground_max']
        assert (p[1:4]>=space['moving_min']).all() and (p[1:4]<=space['moving_max']).all()

@pytest.mark.parametrize('field,value',[('position_geometry',False),('ground_link_mode','fixed'),
    ('phase_mode','ordered'),('target_orientations_deg',[0.,0.,0.]),('panel_bounds',[-5,5,-5,5])])
def test_unsupported_or_disabled_keeps_same_objects(field,value):
    args,target,starts=fixture();setattr(args,field,value)
    result,info=position_seeds.allocate(starts,target,args,0)
    assert info['replaced']==0
    assert all(a is b for a,b in zip(starts,result))

def test_balanced_only_has_no_replaceable_slots():
    args,target,starts=fixture()
    result,info=position_seeds.allocate(starts[:2],target,args,0)
    assert info['replaced']==0 and all(a is b for a,b in zip(starts,result))

def test_cross_profiles_replace_only_four_balanced_profile_slots():
    from dataclasses import replace
    args,target,paired=fixture()
    starts=[replace(s,profile=profile,candidate_id=f'{s.candidate_id}_{profile}')
            for s in paired for profile in ('accuracy','balanced','transmission')]
    result,info=position_seeds.allocate(starts,target,args,0)
    assert len(result)==18 and info['replaced']==4
    for before,after in zip(starts,result):
        if before is not after:
            assert before.model_role!='balanced' and before.profile=='balanced'
        elif before.model_role=='balanced':
            assert before is after
