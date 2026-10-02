import copy,csv,json
import pytest
from test_contributions import recorded_run,change_manifest
from mechanism_generator.contributions import bundle as B

def add_position(run):
    def edit(m):
        m['arguments']['position_geometry']=True
        m['targets'][0]['position_initialization']=dict(method='coupled_position_seed_v1',enabled=True,
            status='allocated',replaced=2,attempts=4,source_sha256='d'*64,replacements=[{'private':'must not copy'}])
    change_manifest(run,edit)
    path=run/'private-target/all_candidates.csv'
    with path.open(newline='') as f:rows=list(csv.DictReader(f))
    rows[1]['model_role']='geometric_position';rows[1]['portfolio_origin']='variable'
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)

def test_local_bundle_preserves_position_origin_and_diagnostics(recorded_run):
    add_position(recorded_run);bundle=B.build_bundle(recorded_run)
    assert bundle['schema_version']=='0.7'
    assert bundle['settings']['position_geometry'] is True
    assert bundle['task'][0]['position_initialization']['replaced']==2
    assert 'replacements' not in bundle['task'][0]['position_initialization']
    assert bundle['provenance']['position_initialization_sha256']=='d'*64
    assert bundle['candidates'][0]['items'][1]['model_role']=='geometric_position'
    B.validate_bundle(bundle)

@pytest.mark.parametrize('field,value',[('enabled',False),('attempts',0),('status','disabled'),('source_sha256','e'*64)])
def test_inconsistent_position_metadata_rejected(recorded_run,field,value):
    add_position(recorded_run);bundle=B.build_bundle(recorded_run)
    bundle['task'][0]['position_initialization'][field]=value
    with pytest.raises(ValueError):B.validate_bundle(bundle)

@pytest.mark.parametrize('version',['0.5','0.6'])
def test_previous_schema_still_valid(recorded_run,version):
    bundle=B.build_bundle(recorded_run);bundle['schema_version']=version
    B.validate_bundle(bundle)
