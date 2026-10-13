import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from lab.common import ROOT,read,write,validate
from lab.aggregate import aggregate
from lab.metrics import percentile,mpjpe_mm
from lab.issues import plans
from lab.benchmark import run

class LabTests(unittest.TestCase):
    def fixture(self):return read(ROOT/'results/sample-pipeline-001.json')
    def measured(self,identifier,latency):
        r=self.fixture();r.update(kind='measured',run_id=identifier,protocol='test',dataset='test-data')
        r['created_at']='2026-10-13T13:00:00+00:00' if identifier=='a' else '2026-10-13T14:00:00+00:00'
        r['provenance']={'checkpoint_sha256':'a'*64,'mhr_sha256':'c'*64,'config_sha256':'d'*64,'upstream_commit':'e'*40}
        r['samples']=[{'id':'image-repeat-0','input_sha256':'b'*64,'latency_ms':latency,'mpjpe_mm':None}]
        r['metrics'].update(latency_p50_ms=latency,latency_p95_ms=latency)
        return r
    def test_sample_schema(self): validate(self.fixture())
    def test_sample_excluded_from_regression(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.fixture();b=self.fixture();b['run_id']='sample-two'
            write(Path(d)/'a.json',a);write(Path(d)/'b.json',b)
            result=aggregate(d);self.assertEqual(result['measured_count'],0);self.assertEqual(plans(result),[])
    def test_missing_inputs_no_metrics(self):
        c=read(ROOT/'experiments/sam3d.local.json');c['upstream']='path-that-does-not-exist'
        r=run(c);self.assertEqual(r['status'],'blocked');self.assertTrue(all(v is None for v in r['metrics'].values()))
    def test_incomplete_metrics_rejected(self):
        r=self.fixture();r['status']='failed'
        with self.assertRaises(ValueError): validate(r)
    def test_duplicate_runs_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            write(Path(d)/'a.json',self.fixture());write(Path(d)/'b.json',self.fixture())
            with self.assertRaises(ValueError):aggregate(d)
    def test_invalid_record_rejected(self):
        r=self.fixture();r['unexpected']=1
        with self.assertRaises(Exception):validate(r)
    def test_nonfinite_rejected(self):
        r=self.fixture();r['metrics']['mpjpe_mm']=float('nan')
        with self.assertRaises(ValueError):validate(r)
    def test_percentiles(self):
        self.assertEqual(percentile([100,120],.5),110);self.assertEqual(percentile([100,120],.95),119);self.assertIsNone(percentile([],.5))
    def test_mpjpe_translation_invariant_and_units(self):
        truth=[[0,0,0] for _ in range(70)];pred=[[1,2,3] for _ in range(70)]
        self.assertEqual(mpjpe_mm(pred,truth),0)
        pred[1][0]+=.07;self.assertAlmostEqual(mpjpe_mm(pred,truth),1)
    def test_mpjpe_wrong_layout_rejected(self):
        with self.assertRaises(ValueError):mpjpe_mm([[0,0,0]],[[0,0,0]])
    def test_mpjpe_uses_hips_not_nose(self):
        truth=[[0,0,0] for _ in range(70)];pred=copy.deepcopy(truth);pred[0][0]=.07
        self.assertAlmostEqual(mpjpe_mm(pred,truth),1)
    def test_inconsistent_metrics_rejected(self):
        r=self.fixture();r['metrics']['latency_p50_ms']=999
        with self.assertRaises(ValueError):validate(r)
    def test_changed_images_not_compared(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.measured('a',100);b=self.measured('b',130);b['samples'][0]['input_sha256']='f'*64
            write(Path(d)/'a.json',a);write(Path(d)/'b.json',b);self.assertEqual(aggregate(d)['comparisons'],[])
    def test_regression_and_incompatible_group(self):
        with tempfile.TemporaryDirectory() as d:
            a=self.measured('a',100);b=self.measured('b',130)
            write(Path(d)/'a.json',a);write(Path(d)/'b.json',b)
            result=aggregate(d);self.assertEqual(result['comparisons'][0]['latency_change_percent'],30);self.assertEqual(len(plans(result)),1)
            b['dataset']='other';write(Path(d)/'b.json',b);self.assertEqual(aggregate(d)['comparisons'],[])
    def test_issue_idempotence(self):
        from lab.issues import main
        data={'comparisons':[{'regression':True,'latest':'b','previous':'a','dataset':'test','latency_change_percent':30}]}
        marker=plans(data)[0]['marker']
        with patch('lab.issues.read',return_value=data),patch('lab.issues.api',return_value=[{'body':marker,'state':'closed'}]) as api,patch.dict('os.environ',{'GITHUB_REPOSITORY':'owner/lab'}),patch('sys.argv',['issues','--publish']):
            main();self.assertEqual(api.call_count,1)

if __name__=='__main__':unittest.main()
