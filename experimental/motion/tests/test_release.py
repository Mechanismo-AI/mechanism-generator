import copy,json,os,shutil,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import torch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
if os.environ.get('MOTION_TEST_INSTALLED')!='1':sys.path.insert(0,str(ROOT/'src'))
from mechanism_motion import solve,engine,assets,qualification
from mechanism_motion.__main__ import main
torch.set_num_threads(1)
FIXTURES=ROOT/'tests/fixtures'
EXACT=os.environ.get('MOTION_TEST_EXACT')=='1'

class ReleaseTests(unittest.TestCase):
    def assert_initial_close(self,actual,expected):
        if isinstance(expected,dict):
            self.assertEqual(set(actual),set(expected))
            for key in expected:self.assert_initial_close(actual[key],expected[key])
        elif isinstance(expected,list):
            self.assertEqual(len(actual),len(expected))
            for a,b in zip(actual,expected):self.assert_initial_close(a,b)
        elif isinstance(expected,float):np.testing.assert_allclose(actual,expected,rtol=1e-8,atol=1e-10)
        else:self.assertEqual(actual,expected)

    def test_frozen_regressions(self):
        for path in sorted(FIXTURES.glob('case-*.json')):
            f=json.loads(path.read_text())
            for chooser in (True,False):
                with self.subTest(case=f['case'],chooser=chooser):
                    out=solve(f['input'],f['seed'],use_chooser=chooser)
                    expected=f['chooser' if chooser else 'baseline']
                    for key in ('qualified','objective_evaluations'):self.assertEqual(out[key],expected[key])
                    self.assertLessEqual(out['objective_evaluations'],200)
                    target=engine.validate(f['input'])
                    for a,b in zip(out['runs'],expected['runs']):
                        self.assertEqual(a['evaluations'],b['evaluations'])
                        for key in ('pose_pass','combined_pass','defined'):self.assertEqual(a['metrics'][key],b['metrics'][key])
                        self.assertEqual(a['metrics'],qualification.assess(np.asarray(a['raw']),target))
                        if EXACT:
                            for key in ('raw','metrics'):self.assertEqual(a[key],b[key])
                    self.assertEqual(len(out['runs']),len(expected['runs']))
                    if chooser:
                        self.assertEqual(out['selected_label'],f['selected_label'])
                        self.assertEqual(len(out['pool']),len(f['pool']))
                        for a,b in zip(out['pool'],f['pool']):
                            for key in ('initial_raw','before','ranking_prediction'):
                                if EXACT:self.assertEqual(a[key],b[key])
                                else:self.assert_initial_close(a[key],b[key])

    def test_invalid_inputs(self):
        p=json.loads((FIXTURES/'case-00.json').read_text())['input']
        for value in ({},'1',None,True,float('nan'),float('inf'),10**1000):
            for key in ('theta_rad','branches','q','v','a'):
                q=copy.deepcopy(p)
                if key in ('q','v','a'):q[key][0][0]=value
                else:q[key][0]=value
                with self.subTest(key=key,value=type(value).__name__),self.assertRaises(ValueError):engine.validate(q)
        for key in p:
            q=copy.deepcopy(p);q[key]={}
            with self.assertRaises(ValueError):engine.validate(q)
        for seed in (-1,True,1.5,2**63):
            with self.assertRaises(ValueError):solve(p,seed)

    def test_cli_preserves_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'result.json.tmp';source.write_text('{}')
            alias=Path(directory)/'alias.json';os.link(source,alias)
            for output in (source,source.parent/'..'/source.parent.name/source.name,alias):
                with patch.object(sys,'argv',['mechanism-motion',str(source),'--output',str(output)]),patch('mechanism_motion.__main__.solve') as solver,self.assertRaises(SystemExit) as error:
                    main()
                self.assertEqual(error.exception.code,2);solver.assert_not_called();self.assertEqual(source.read_text(),'{}')
            result=dict(qualified=False,objective_evaluations=0,status='experimental')
            with patch.object(sys,'argv',['mechanism-motion',str(source),'--output',str(source.parent/'result.json')]),patch('mechanism_motion.__main__.solve',return_value=result):main()
            self.assertEqual(source.read_text(),'{}')
            self.assertEqual(json.loads((source.parent/'result.json').read_text()),result)

    def test_corrupt_assets(self):
        original=assets.DIRECTORY
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'assets';shutil.copytree(original,destination)
            try:
                assets.DIRECTORY=destination;assets.load.cache_clear()
                with (destination/'proposal.pt').open('ab') as stream:stream.write(b'corrupt')
                with self.assertRaisesRegex(ValueError,'checksum'):assets.load()
                shutil.copy2(original/'proposal.pt',destination/'proposal.pt')
                model=json.loads((destination/'chooser.json').read_text());model['feature_names']=[]
                (destination/'chooser.json').write_text(json.dumps(model))
                manifest=json.loads((destination/'manifest.json').read_text());manifest['files']['chooser.json']=assets.sha(destination/'chooser.json')
                (destination/'manifest.json').write_text(json.dumps(manifest))
                with self.assertRaisesRegex(ValueError,'feature schema'):assets.load()
            finally:assets.DIRECTORY=original;assets.load.cache_clear()

    def test_cli_malformed_input(self):
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'input.json';output=Path(directory)/'output.json'
            payload=json.loads((FIXTURES/'case-00.json').read_text())['input'];payload['q']={}
            source.write_text(json.dumps(payload));before=source.read_bytes()
            with patch.object(sys,'argv',['mechanism-motion',str(source),'--output',str(output)]),self.assertRaises(SystemExit) as error:main()
            self.assertEqual(error.exception.code,2);self.assertFalse(output.exists());self.assertEqual(before,source.read_bytes())

if __name__=='__main__':unittest.main()
