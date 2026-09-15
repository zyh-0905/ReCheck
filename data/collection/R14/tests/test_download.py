import hashlib
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
import download_public as d

PIN='593e686f4d0c2e9fcae5ae664c16a7687907cf97'

def payload(path):
    if path == 'README.md':
        return b'---\nlicense: apache-2.0\n---\nTEST FIXTURE, NOT REAL RESEARCH DATA\n'
    if 'aggregate' in path:
        return b'{"metrics": {}, "synthetic_software_fixture": true}'
    trial=int(Path(path).stem.split('_')[1])
    return json.dumps({'trial_id':trial,'samples':[], 'total_samples':0,
                       'synthetic_software_fixture':True}, indent=2).encode()+b'\n'

def fake_fetch(url):
    path=url.split('/resolve/'+PIN+'/')[1]
    return payload(path), {'x-repo-commit': PIN}

class CollectorTests(unittest.TestCase):
    def test_pin_and_roster(self):
        paths=d.planned_paths()
        self.assertEqual(d.REVISION,PIN)
        self.assertEqual(len(paths),109)
        self.assertEqual(len(set(paths)),109)
        self.assertEqual(sum('/trial_' in p for p in paths),96)
    def test_all_model_persona_trial_cells(self):
        p=set(d.planned_paths())
        for model in ('gpt_4_1','gpt_4o','gpt_4o_mini','gpt_5','mistral_large_2411','mistral_nemo'):
            for persona in ('expert','nonexpert'):
                for n in range(8):
                    self.assertIn(f'toolsandbox/{model}/{persona}/trial_{n}_results.json',p)
    def test_no_pickle_or_model_weights(self):
        self.assertTrue(d.planned_paths())
        self.assertTrue(all(p.endswith('.json') or p=='README.md' for p in d.planned_paths()))
    def test_source_is_fixed_https(self):
        u=d.source_url('toolsandbox/gpt_4_1/expert/trial_0_results.json')
        self.assertEqual(u, 'https://huggingface.co/datasets/SAP/agent-quality-inspect/resolve/'+PIN+'/toolsandbox/gpt_4_1/expert/trial_0_results.json')
    def test_path_traversal_rejected(self):
        with self.assertRaises(ValueError): d.source_url('../secret.json')
    def test_foreign_file_rejected(self):
        with self.assertRaises(ValueError): d.source_url('toolsandbox/model.pkl')
    def test_valid_json_metadata(self):
        p='toolsandbox/gpt_4_1/expert/trial_0_results.json'
        m=d.validate_payload(p,payload(p))
        self.assertEqual(m['sample_count'],0)
        self.assertEqual(m['trial_id'],0)
    def test_html_not_json(self):
        with self.assertRaises(ValueError): d.validate_payload('toolsandbox/gpt_4_1/expert/trial_0_results.json',b'<html>login</html>')
    def test_wrong_trial_rejected(self):
        with self.assertRaises(ValueError):
            d.validate_payload('toolsandbox/gpt_4_1/expert/trial_1_results.json',b'{"samples":[],"trial_id":0}')
    def test_incomplete_json_rejected(self):
        with self.assertRaises(ValueError): d.validate_payload('toolsandbox/gpt_4_1/expert/trial_0_results.json',b'{')
    def test_changed_commit_rejected(self):
        with self.assertRaises(ValueError): d.validate_commit({'x-repo-commit':'a'*40})
    def test_complete_raw_archive(self):
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)/'data'
            result=d.collect(out,fetch=fake_fetch,quiet=True)
            self.assertEqual(result['status'],'COMPLETE')
            self.assertEqual(result['trial_files'],96)
            zpath=Path(result['archive'])
            with zipfile.ZipFile(zpath) as z:
                self.assertEqual(z.read('raw/README.md'),payload('README.md'))
                manifest=json.loads(z.read('MANIFEST.json'))
                self.assertEqual(len(manifest['files']),109)
                for r in manifest['files']:
                    self.assertEqual(hashlib.sha256(z.read('raw/'+r['path'])).hexdigest(),r['sha256'])
            self.assertTrue(d.verify_archive(zpath)['verified'])
    def test_no_overwrite_no_fetch(self):
        with tempfile.TemporaryDirectory() as td:
            called=[]
            with self.assertRaises(FileExistsError):
                d.collect(Path(td), fetch=lambda u:called.append(u),quiet=True)
            self.assertEqual(called,[])
    def test_transport_failure_partial_zip(self):
        with tempfile.TemporaryDirectory() as td:
            seen=[]
            def fail_second(u):
                seen.append(u)
                if len(seen)==2: raise OSError('test network fail')
                return fake_fetch(u)
            r=d.collect(Path(td)/'out',fetch=fail_second,quiet=True)
            self.assertEqual(r['status'],'INCOMPLETE')
            self.assertEqual(len(seen),2)
            self.assertTrue(Path(r['archive']).exists())
            self.assertTrue(d.verify_archive(Path(r['archive']))['verified'])
    def test_file_byte_limit(self):
        old=d.MAX_FILE_BYTES
        try:
            d.MAX_FILE_BYTES=8
            with tempfile.TemporaryDirectory() as td:
                r=d.collect(Path(td)/'out',fetch=fake_fetch,quiet=True)
                self.assertEqual(r['status'],'INCOMPLETE')
                self.assertEqual(r['acquired_files'],0)
        finally: d.MAX_FILE_BYTES=old
    def test_manifest_detects_tamper(self):
        with tempfile.TemporaryDirectory() as td:
            r=d.collect(Path(td)/'out',fetch=fake_fetch,quiet=True)
            src=Path(r['archive']); dst=Path(td)/'bad.zip'
            with zipfile.ZipFile(src) as a, zipfile.ZipFile(dst,'w') as b:
                for name in a.namelist():
                    body=a.read(name)
                    if name=='raw/README.md': body+=b'tampered'
                    b.writestr(name,body)
            with self.assertRaises(ValueError): d.verify_archive(dst)

if __name__=='__main__': unittest.main()
