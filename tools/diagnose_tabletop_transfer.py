"""Reproduce the bounded tabletop-transfer geometry diagnosis from a source checkout.

No training or optimizer run. Requires the released engine's NumPy geometry
helpers and the frozen example data. Writes to a new output directory only.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,hashlib,json,math,sys,time
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
EXAMPLE=ROOT/'examples/tabletop-transfer'
DATA=EXAMPLE/'diagnosis'
sys.path.insert(0,str(ROOT/'src'))
from mechanism_generator.engine import pose_seeds
import benchmark_pose as independent

def load_case():
    brief=json.loads((EXAMPLE/'design-brief.json').read_text(encoding='utf-8'))
    plan=json.loads((DATA/'diagnosis-plan.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((EXAMPLE/'design-brief.json').read_bytes()).hexdigest()==plan['brief_sha256']
    args=SimpleNamespace(**json.loads((DATA/'baseline-arguments.json').read_text(encoding='utf-8')))
    world=(np.array(brief['targets_mm'])-brief['origin_offset_mm'])/brief['scale_mm_per_normalized_unit']
    return brief,args,world,np.array(brief['orientations_deg'])

def construct(args,world,angles,samples=65536,*,offset_mode='positive',mount_deg=0.,s_range=(.01,.99),bound_multiplier=1.,angle_jitter_deg=0.):
    scale=max(float(np.linalg.norm(world[:,None]-world[None,:],axis=-1).max()),args.minimum_target_scale)
    centroid=world.mean(axis=0)
    targets=(world-centroid)/scale
    requested=np.broadcast_to(angles,(samples,3)).copy()
    if angle_jitter_deg:
        requested+=angle_jitter_deg*(2*np.column_stack([pose_seeds._radical_inverse(samples,b) for b in (7,11,13)])-1)
    radians=np.radians(np.remainder(requested-mount_deg,360.))
    direction=np.stack((np.cos(radians),np.sin(radians)),axis=-1)
    normal=np.stack((-np.sin(radians),np.cos(radians)),axis=-1)
    u=np.column_stack([pose_seeds._radical_inverse(samples,b) for b in (2,3,5)])
    moving_min=max(.001/scale,args.moving_link_min_ratio)
    moving_max=max(moving_min+1e-6/scale,args.moving_link_max_ratio)*bound_multiplier
    l3=moving_min+u[:,0]*(moving_max-moving_min)
    s=s_range[0]+u[:,1]*(s_range[1]-s_range[0])
    min_bar=.1/scale
    max_bar=max(min_bar+1e-6/scale,args.bar_length_max_ratio)*bound_multiplier
    bar=min_bar+u[:,2]*(max_bar-min_bar)
    if offset_mode=='negative':bar=-bar
    elif offset_mode!='positive':raise ValueError(offset_mode)
    a=targets[None]-(s*l3)[:,None,None]*direction-bar[:,None,None]*normal
    b=a+l3[:,None,None]*direction
    o2,l2,ok_a=pose_seeds._circumcenter(a)
    o4,l4,ok_b=pose_seeds._circumcenter(b)
    ground=o4-o2;l1=np.linalg.norm(ground,axis=1)
    base=np.arctan2(ground[:,1],ground[:,0])
    phases=(np.arctan2(a[:,:,1]-o2[:,None,1],a[:,:,0]-o2[:,None,0])-base[:,None])%(2*np.pi)
    delta_a=a-o4[:,None];delta_b=b-o4[:,None]
    signs=np.sign(delta_a[:,:,0]*delta_b[:,:,1]-delta_a[:,:,1]*delta_b[:,:,0])
    links=np.column_stack((l1,l2,l3,l4))
    sorted_links=np.sort(links,axis=1)
    grashof=sorted_links[:,1]+sorted_links[:,2]-sorted_links[:,0]-sorted_links[:,3]
    crank=np.minimum.reduce((l1-l2,l3-l2,l4-l2))
    near,far=np.abs(l1-l2),l1+l2
    closure=np.minimum(l3+l4-far,near-np.abs(l3-l4))
    assembly_margin=np.minimum(closure,near)
    with np.errstate(divide='ignore',invalid='ignore'):
        target_cos=(l3[:,None]**2+l4[:,None]**2-(delta_a**2).sum(axis=2))/(2*l3*l4)[:,None]
        target_tx=np.degrees(np.arccos(np.clip(np.abs(target_cos),0,1))).min(axis=1)
        global_cos=(l3[:,None]**2+l4[:,None]**2-np.column_stack((near,far))**2)/(2*l3*l4)[:,None]
        global_tx=np.degrees(np.arccos(np.clip(np.abs(global_cos),0,1))).min(axis=1)
    finite=ok_a&ok_b&np.isfinite(links).all(axis=1)
    ground_min=max(.001/scale,args.ground_link_min_ratio)
    ground_max=max(ground_min+1e-6/scale,args.ground_link_max_ratio)*bound_multiplier
    bounds=((l1>ground_min)&(l1<ground_max)&(links[:,1:]>moving_min).all(axis=1)
            &(links[:,1:]<moving_max).all(axis=1)&(np.abs(o2)<args.base_search_radius_ratio*bound_multiplier).all(axis=1))
    branch=((signs!=0).all(axis=1)&(signs==signs[:,:1]).all(axis=1))
    if args.branches=='negative':branch&=signs[:,0]<0
    elif args.branches=='positive':branch&=signs[:,0]>0
    order={}
    for direction_name,sign in [('positive',1),('negative',-1)]:
        gaps=(sign*(np.roll(phases,-1,axis=1)-phases))%(2*np.pi)
        order[direction_name]=(np.abs(gaps.sum(axis=1)-2*np.pi)<1e-7)&(gaps.min(axis=1)>=math.radians(.25))
    masks={
        'full_cycle_assembly':(near>1e-12)&(closure>=0),
        'assembly_margin':assembly_margin>=args.assembly_margin_ratio,
        'grashof':grashof>=0,
        'grashof_margin':grashof>=args.grashof_margin_ratio,
        'crank_strictly_shortest':crank>0,
        'crank_margin':crank>=max(args.class_margin/scale,args.class_margin_ratio),
        'branch_consistent':branch,
        'target_transmission':target_tx>=args.minimum_target_transmission,
        'global_transmission':global_tx>=args.minimum_global_transmission,
    }
    assert not args.enforce_follower_not_longest
    parameters=np.column_stack((links*scale,s,bar*scale,o2*scale+centroid,base))
    return dict(samples=samples,scale=scale,parameters=parameters,phases=phases,signs=signs,
                finite=finite,bounds=bounds,masks=masks,order=order,target_tx=target_tx,global_tx=global_tx,
                margins={'full_cycle_closure':closure,'assembly':assembly_margin,'grashof':grashof,'crank':crank},
                a=a*scale+centroid,b=b*scale+centroid,mount_deg=mount_deg,constructed_angles=requested)


def report(result):
    mask=result['finite']&result['bounds'];masks=result['masks']
    gate_names=['assembly_margin','grashof_margin','crank_margin']
    gate=mask.copy()
    cumulative={}
    for name in gate_names:
        gate&=masks[name];cumulative[name]=int(gate.sum())
    ablations={}
    for removed in gate_names:
        active=mask.copy()
        for name in gate_names:
            if name!=removed:active&=masks[name]
        ablations['remove_'+removed]=int(active.sum())
    no_margins=mask&masks['full_cycle_assembly']&masks['grashof']&masks['crank_strictly_shortest']
    ablations['remove_all_robustness_margins']=int(no_margins.sum())
    by_direction={}
    for d in ('positive','negative'):
        ordered=gate&masks['branch_consistent']&result['order'][d]
        final=ordered&masks['target_transmission']&masks['global_transmission']
        by_direction[d]={'branch_and_order':int(ordered.sum()),'all_seed_filters':int(final.sum())}
    failures={}
    for key in zip(*[masks[name][mask] for name in gate_names]):
        failed=' + '.join(n for n,passed in zip(gate_names,key) if not passed) or 'none'
        failures[failed]=failures.get(failed,0)+1
    return {'samples':result['samples'],'finite':int(result['finite'].sum()),'in_bounds':int(mask.sum()),
            'individual_passes_among_in_bounds':{k:int((v&mask).sum()) for k,v in masks.items()},
            'cumulative_original_gate':cumulative,'one_gate_removals':ablations,'joint_failures':failures,
            'margin_quantiles_normalized_by_target_span':{k:np.quantile(v[mask],[0,.05,.5,.95,1]).tolist() for k,v in result['margins'].items()},
            'directions':by_direction}


def verify_representatives(result,world,angles,count=64):
    eligible=np.flatnonzero(result['finite']&result['bounds'])
    selected=eligible[np.linspace(0,len(eligible)-1,min(count,len(eligible)),dtype=int)]
    worst_point=0.;worst_angle=0.;assembly_matches=0
    for i in selected:
        p=result['parameters'][i];phases=result['phases'][i]
        # A seed can require different assembly branches at different poses.
        # Verify each independently and keep branch consistency as a separate gate.
        for j in range(3):
            at=independent.analytic_geometry(p,phases[j:j+1],int(result['signs'][i,j]))
            assert at['valid'].all()
            worst_point=max(worst_point,float(np.linalg.norm(at['points'][0]-world[j])))
            worst_angle=max(worst_angle,float(abs(independent.circular_error_deg(at['orientations_deg'][0]+result['mount_deg'],result['constructed_angles'][i,j]))))
        cycle=independent.full_cycle_checks(p)
        assert cycle['full_cycle_assembly']==bool(result['masks']['full_cycle_assembly'][i])
        assert cycle['grashof']==bool(result['masks']['grashof'][i])
        assert cycle['crank_is_strictly_shortest']==bool(result['masks']['crank_strictly_shortest'][i])
        assembly_matches+=1
    assert worst_point<1e-8 and worst_angle<1e-7
    return {'candidates_verified':len(selected),'poses_verified':3*len(selected),'maximum_position_error_normalized':worst_point,
            'maximum_orientation_error_deg':worst_angle,'full_cycle_and_class_agreements':assembly_matches}


def interval_checks(result,direction):
    p=result['parameters'];l1,l2,l3,l4=p[:,:4].T
    sign=1 if direction=='positive' else -1
    phases=result['phases'];span=(sign*(phases[:,2]-phases[:,0]))%(2*np.pi)
    ends=np.sqrt(l1[:,None]**2+l2[:,None]**2-2*l1[:,None]*l2[:,None]*np.cos(phases[:,[0,2]]))
    near=ends.min(axis=1);far=ends.max(axis=1)
    includes_near=(sign*(0-phases[:,0]))%(2*np.pi)<=span
    includes_far=(sign*(np.pi-phases[:,0]))%(2*np.pi)<=span
    near=np.where(includes_near,np.abs(l1-l2),near)
    far=np.where(includes_far,l1+l2,far)
    assembly=(near>1e-12)&(near>=np.abs(l3-l4))&(far<=l3+l4)
    cos=(l3[:,None]**2+l4[:,None]**2-np.column_stack((near,far))**2)/(2*l3*l4)[:,None]
    tx=np.degrees(np.arccos(np.clip(np.max(np.abs(cos),axis=1),0,1)))
    tx=np.where(assembly,tx,0.)
    return assembly,tx


def physical_parameters(result,index,brief):
    p=result['parameters'][index].copy();scale=brief['scale_mm_per_normalized_unit']
    p[:4]*=scale;p[5]*=scale;p[6:8]=p[6:8]*scale+brief['origin_offset_mm']
    return p


def assess_candidate(result,index,direction,brief,*,limited=False):
    p=physical_parameters(result,index,brief)
    branch=int(result['signs'][index,0]);phases=result['phases'][index]
    sign=1 if direction=='positive' else -1
    progress=(sign*(phases-phases[0]))%(2*np.pi)
    at=independent.analytic_geometry(p,phases,branch)
    errors=np.linalg.norm(at['points']-brief['targets_mm'],axis=1)
    angle_errors=np.abs(independent.circular_error_deg(at['orientations_deg']+result['mount_deg'],brief['orientations_deg']))
    assert at['valid'].all() and errors.mean()<=1+1e-7 and errors.max()<=1.5+1e-7 and angle_errors.max()<=3+1e-7
    assert np.all(np.diff(progress)>0)
    cycle=independent.full_cycle_checks(p)
    span=progress[2] if limited else 2*np.pi
    theta=phases[0]+sign*np.linspace(0,span,7201)
    dense=independent.analytic_geometry(p,theta,branch)
    assert dense['valid'].all()
    if not limited:
        assert cycle['full_cycle_assembly'] and cycle['grashof'] and cycle['crank_is_strictly_shortest']
        assert cycle['global_minimum_transmission_deg']>=10-1e-7
    else:assert dense['transmission_deg'].min()>=10-1e-7
    angle=np.radians(dense['orientations_deg']+result['mount_deg'])
    u=np.column_stack((np.cos(angle),np.sin(angle)));v=np.column_stack((-np.sin(angle),np.cos(angle)))
    corners=np.concatenate([dense['points']+x*u+y*v for x in (-25,25) for y in (-5,5)])
    envelope=np.vstack([dense['a'],dense['b'],dense['o2'],dense['o4'],corners])
    lo=envelope.min(axis=0);hi=envelope.max(axis=0)
    fixed=np.vstack([dense['o2'],dense['o4']])
    panel=bool((lo>=0).all() and (hi<=[400,300]).all())
    pivot=bool((fixed>=10).all() and (fixed<=[390,290]).all())
    return {'sample_index':int(index+1),'direction':direction,'branch':branch,'parameters_mm':p.tolist(),
            'phases_rad':phases.tolist(),'phase_progress_deg':np.degrees(progress).tolist(),
            'achieved_points_mm':at['points'].tolist(),'achieved_orientations_deg':at['orientations_deg'].tolist(),
            'position_errors_mm':errors.tolist(),'orientation_errors_deg':angle_errors.tolist(),
            'cycle_checks':cycle,'sampled_motion_minimum_transmission_deg':float(dense['transmission_deg'].min()),
            'target_minimum_transmission_deg':float(at['transmission_deg'].min()),
            'envelope_min_mm':lo.tolist(),'envelope_max_mm':hi.tolist(),'panel_screen_passed':panel,'pivot_clearance_passed':pivot,
            'original_brief_passed':bool(not limited and panel and pivot),
            'relaxed_limited_motion_passed':bool(limited and panel and pivot),
            'limited_reversing_input':limited}


def screen(result,brief,*,limited=False):
    modes={};m=result['masks'];base=result['finite']&result['bounds']
    p=result['parameters'];angle=p[:,8]
    fixed2=p[:,6:8]*brief['scale_mm_per_normalized_unit']+brief['origin_offset_mm']
    fixed4=fixed2+p[:,0,None]*brief['scale_mm_per_normalized_unit']*np.column_stack((np.cos(angle),np.sin(angle)))
    pivots=((fixed2>=10)&(fixed2<=[390,290])&(fixed4>=10)&(fixed4<=[390,290])).all(axis=1)
    for direction in ('positive','negative'):
        mask=base&m['branch_consistent']&result['order'][direction]&m['target_transmission']
        if limited:
            assembly,tx=interval_checks(result,direction)
            mask&=assembly&(tx>=10)
        else:
            mask&=m['assembly_margin']&m['grashof_margin']&m['crank_margin']&m['global_transmission']
        ids=np.flatnonzero(mask&pivots)
        ranked=sorted(ids,key=lambda i:float(result['parameters'][i,:4].sum()))[:128]
        checked=[assess_candidate(result,int(i),direction,brief,limited=limited) for i in ranked]
        passed=[r for r in checked if r['panel_screen_passed'] and r['pivot_clearance_passed']]
        modes[direction]={'survivors_before_panel':int(mask.sum()),'survivors_after_pivot_clearance':len(ids),
                          'panel_screened':len(checked),'panel_passed_among_screened':len(passed),
                          'witnesses':passed[:3],'screened_candidates':checked}
    return modes



def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',required=True,type=Path)
    options=parser.parse_args()
    options.output_dir.mkdir(parents=True,exist_ok=False)
    brief,args,world,angles=load_case()
    configurations=[('baseline',{}),('allowed_tilt_tolerance',{'angle_jitter_deg':3.}),
                    ('opposite_attachment_side',{'offset_mode':'negative'}),
                    ('attachment_before_A',{'s_range':(-1.,.01)}),('attachment_beyond_B',{'s_range':(.99,2.)})]
    records=[]
    for name,settings in configurations:
        r=construct(args,world,angles,**settings)
        stats=report(r)
        checked=verify_representatives(r,world,angles)
        screened=screen(r,brief)
        records.append({'id':name,'settings':settings,'summary':stats,'verification':checked,'screening':screened})
        if name=='baseline':
            baseline=r
            for direction in ('positive','negative'):
                args.crank_direction=direction
                _,original=pose_seeds.generate_pose_seeds(world,angles,args,sample_count=65536)
                assert original['finite_dyads']==stats['finite']
                assert original['within_search_bounds']==stats['in_bounds']
                assert original['full_cycle_robust_crank_shortest']==stats['cumulative_original_gate']['crank_margin']
                assert original['transmission_selection_floors']==stats['directions'][direction]['all_seed_filters']
        print(name+': '+str(sum(q['panel_passed_among_screened'] for q in screened.values()))+' passing full-turn panel screens',flush=True)
    records.append({'id':'limited_reversing_input','brief_relaxed':True,'screening':screen(baseline,brief,limited=True)})
    (options.output_dir/'controlled-comparisons.json').write_text(json.dumps({'experiments':records},indent=2,allow_nan=False)+'\n')
    r=construct(args,world,angles,samples=262144,angle_jitter_deg=3.)
    density={'summary':report(r),'verification':verify_representatives(r,world,angles),'screening':screen(r,brief)}
    (options.output_dir/'tolerance-density-result.json').write_text(json.dumps(density,indent=2,allow_nan=False)+'\n')
    print('Denser allowed-tolerance search: '+str(sum(q['panel_passed_among_screened'] for q in density['screening'].values()))+' passing original-brief panel screens')

if __name__=='__main__':main()
