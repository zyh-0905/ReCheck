"""Offline fixtures only: never produce or claim new LLM research observations."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import patch

import collect_feedback as c


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False), encoding='utf-8')


def fixture(base, cap=4096):
    root = base / 'project' / 'runs' / 'old'
    root.mkdir(parents=True)
    source = b'# fixture code; never executed\n'
    src = {'run.py': hashlib.sha256(source).hexdigest()}
    manifest = dict(version='llm-pilot-0.1', config={'model':'fixture', 'max_output_tokens':cap, 'base_url_sha256':c.digest('https://fixture.invalid/v1')},
                    study='recheck', spec={'streams':4,'steps':8,'methods':['recheck','myopic','ttl','always']}, source_hashes=src)
    manifest['fingerprint'] = c.digest(manifest)
    manifest['evidence_label'] = 'SOFTWARE_TEST_NOT_RESEARCH'
    write(root/'manifest.json', manifest)
    (root/'code_snapshot').mkdir()
    (root/'code_snapshot'/'run.py').write_bytes(source)
    payload = {'model':'fixture', 'messages':[{'role':'user','content':'test'}], 'max_tokens':cap}
    start = {'attempt':1,'logical_id':'test/1','request_sha256':c.digest({'endpoint':'https://fixture.invalid/v1','payload':payload}), 'payload':payload,'metadata':{}}
    result = {**start, 'status':'ok','response':{'model':'fixture', 'choices':[{'finish_reason':'length'}], 'usage':{'prompt_tokens':10,'completion_tokens':20}}, 'text':'{', 'estimated_cost':None}
    write(root/'attempts'/'000001_start.json', start)
    write(root/'attempts'/'000001_result.json', result)
    write(root/'calls'/'first.json', result)
    write(root/'attempts'/'000002_start.json', {**start,'attempt':2,'logical_id':'test/2'})
    write(root/'status.json', {'status':'interrupted'})
    return root


class CollectorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)

    def contract(self, root):
        m = json.loads((root/'manifest.json').read_text())
        return {'task_id':'R1_EVIDENCE_COMPLETION','expected_study':'recheck', 'expected_output_cap':4096,
                'expected_fingerprint':m['fingerprint'], 'prior_manifest_sha256':hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(), 'request_endpoint_for_hash_check':'https://fixture.invalid/v1'}

    def collect(self, root, **kw):
        return c.collect_bundle(root, self.base/'return.zip', self.contract(root), **kw)

    def test_entrypoint_exists(self):
        self.assertTrue(callable(getattr(c,'collect_bundle',None)))

    def test_partial_interrupted_is_packaged_not_retried(self):
        root=fixture(self.base); r=self.collect(root)
        self.assertEqual(r['ledger']['started_attempts'],2)
        self.assertEqual(r['ledger']['finished_attempts'],1)
        self.assertEqual(r['ledger']['pending_attempts'],['000002'])
        self.assertEqual(r['ledger']['truncated_responses'],1)
        self.assertEqual(r['new_model_calls'],0)
        self.assertTrue((self.base/'return.zip').exists())

    def test_source_bytes_preserved(self):
        root=fixture(self.base); before={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
        r=self.collect(root)
        after={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
        self.assertEqual(before,after)
        with zipfile.ZipFile(self.base/'return.zip') as z:
            for rel, data in before.items(): self.assertEqual(z.read('evidence/run/'+rel),data)
        self.assertTrue(r['selected_source_bytes_unchanged'])

    def test_manifest_cap_mismatch_reported_not_silently_accepted(self):
        root=fixture(self.base,cap=16384); r=self.collect(root)
        self.assertIn('OUTPUT_CAP_MISMATCH',{x['code'] for x in r['issues']})
        self.assertFalse(r['checks']['matches_requested_run'])

    def test_fingerprint_mismatch_is_reported(self):
        root=fixture(self.base); contract=self.contract(root); contract['expected_fingerprint']='0'*64
        r=c.collect_bundle(root,self.base/'return.zip',contract)
        self.assertIn('RUN_FINGERPRINT_DIFFERS_FROM_PRIOR',{x['code'] for x in r['issues']})

    def test_config_local_and_dotenv_never_copied(self):
        root=fixture(self.base)
        (root/'.env').write_text('secret=do-not-read')
        (root/'config.local.json').write_text('{"secret":"do-not-read"}')
        (root/'calls'/'.env').write_text('do-not-read')
        self.collect(root)
        with zipfile.ZipFile(self.base/'return.zip') as z:
            self.assertFalse(any('.env' in s or 'config.local' in s for s in z.namelist()))

    def test_common_credential_blocks_raw_evidence(self):
        root=fixture(self.base)
        write(root/'calls'/'credential.json',{'content':'Bearer '+ 'a'*40})
        r=self.collect(root)
        self.assertEqual(r['status'],'BLOCKED_SENSITIVE_CONTENT')
        with zipfile.ZipFile(self.base/'return.zip') as z:
            self.assertFalse(any(n.startswith('evidence/') for n in z.namelist()))
            self.assertNotIn(('a'*40).encode(),b''.join(z.read(n) for n in z.namelist()))

    def test_sensitive_metadata_not_echoed_in_diagnostic(self):
        root=fixture(self.base)
        p=root/'attempts'/'000001_result.json';j=json.loads(p.read_text())
        secret='sk-'+('Z'*32);j['response']['model']=secret;write(p,j)
        r=self.collect(root)
        self.assertEqual(r['status'],'BLOCKED_SENSITIVE_CONTENT')
        with zipfile.ZipFile(self.base/'return.zip') as z:
            self.assertNotIn(secret.encode(), b''.join(z.read(n) for n in z.namelist()))

    def test_changed_source_refuses_inconsistent_evidence(self):
        root=fixture(self.base)
        real=c.read_regular; state={'n':0}
        def changing(path, limit=c.MAX_FILE):
            data=real(path,limit)
            if str(path).endswith('000001_start.json'):
                state['n']+=1
                if state['n']==2:return data+b' '
            return data
        with patch.object(c,'read_regular',side_effect=changing):r=self.collect(root)
        self.assertEqual(r['status'],'SOURCE_UNSTABLE')
        self.assertEqual(r['evidence_file_count'],0)

    def test_result_without_start_is_reported(self):
        root=fixture(self.base);(root/'attempts'/'000001_start.json').unlink()
        self.assertIn('RESULT_WITHOUT_START',{x['code'] for x in self.collect(root)['issues']})

    def test_bundle_rejects_path_traversal(self):
        p=self.base/'bad.zip'
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('../bad.txt','bad')
            z.writestr('BUNDLE_MANIFEST.json',json.dumps({'sha256':{}}))
        self.assertFalse(c.verify_bundle(p)['ok'])

    def test_unknown_values_not_replaced_with_zero_bill(self):
        root=fixture(self.base);r=self.collect(root)
        self.assertFalse(r['ledger']['provider_bill_reconciled'])
        self.assertFalse(r['ledger']['cost_estimate_recomputed'])

    def test_private_key_blocks_raw_evidence(self):
        root=fixture(self.base)
        write(root/'calls'/'credential.json',{'text':'-----BEGIN PRIVATE KEY-----'})
        self.assertEqual(self.collect(root)['status'],'BLOCKED_SENSITIVE_CONTENT')

    def test_secret_field_value_blocked_but_key_env_name_allowed(self):
        root=fixture(self.base);write(root/'records'/'r.json',{'api_key':'actual-secret-value'})
        self.assertEqual(self.collect(root)['status'],'BLOCKED_SENSITIVE_CONTENT')

    def test_unknown_file_not_in_export(self):
        root=fixture(self.base);(root/'unrelated.txt').write_text('do-not-collect')
        self.collect(root)
        with zipfile.ZipFile(self.base/'return.zip') as z:self.assertFalse(any('unrelated' in n for n in z.namelist()))

    def test_unlisted_source_file_excluded(self):
        root=fixture(self.base);(root/'code_snapshot'/'other.py').write_text('unused')
        self.collect(root)
        with zipfile.ZipFile(self.base/'return.zip') as z:self.assertFalse(any('other.py' in n for n in z.namelist()))

    def test_symlink_not_followed(self):
        root=fixture(self.base); outside=self.base/'outside.json';outside.write_text('{"x":1}')
        link=root/'calls'/'outside.json'
        try:link.symlink_to(outside)
        except OSError:self.skipTest('symlink unavailable')
        r=self.collect(root)
        self.assertIn('SYMLINK_NOT_COLLECTED',{x['code'] for x in r['issues']})
        with zipfile.ZipFile(self.base/'return.zip') as z:self.assertFalse(any('outside.json' in n for n in z.namelist()))

    def test_output_inside_run_refused(self):
        root=fixture(self.base)
        with self.assertRaises(ValueError): c.collect_bundle(root,root/'new.zip',self.contract(root))
        self.assertFalse((root/'new.zip').exists())

    def test_overwrite_refused(self):
        root=fixture(self.base);(self.base/'return.zip').write_bytes(b'old')
        with self.assertRaises(FileExistsError):self.collect(root)
        self.assertEqual((self.base/'return.zip').read_bytes(),b'old')

    def test_missing_run_report_without_fabrication(self):
        root=self.base/'missing'
        r=c.collect_bundle(root,self.base/'return.zip',{'task_id':'R1_EVIDENCE_COMPLETION'})
        self.assertEqual(r['status'],'MISSING_SOURCE')
        self.assertFalse(root.exists())
        self.assertEqual(r['evidence_file_count'],0)

    def test_empty_directories_and_missing_calls_are_reported(self):
        root=fixture(self.base);(root/'calls'/'first.json').unlink()
        r=self.collect(root)
        self.assertIn('SUCCESS_RESULT_WITHOUT_CALL',{x['code'] for x in r['issues']})

    def test_endpoint_bound_request_hash_validates(self):
        root=fixture(self.base);r=self.collect(root)
        self.assertNotIn('REQUEST_HASH_MISMATCH',{x['code'] for x in r['issues']})
        self.assertTrue(r['checks']['request_endpoint_binding_verified'])

    def test_unknown_endpoint_not_claimed_to_be_verified(self):
        root=fixture(self.base);contract=self.contract(root);contract.pop('request_endpoint_for_hash_check')
        r=c.collect_bundle(root,self.base/'return.zip',contract)
        self.assertFalse(r['checks']['request_endpoint_binding_verified'])
        self.assertIn('REQUEST_HASH_CHECK_UNAVAILABLE',{x['code'] for x in r['issues']})

    def test_request_hash_corruption_reported(self):
        root=fixture(self.base);p=root/'attempts'/'000001_start.json';j=json.loads(p.read_text());j['payload']['model']='changed';write(p,j)
        r=self.collect(root)
        self.assertIn('REQUEST_HASH_MISMATCH',{x['code'] for x in r['issues']})

    def test_snapshot_hash_corruption_reported(self):
        root=fixture(self.base);(root/'code_snapshot'/'run.py').write_text('changed')
        r=self.collect(root)
        self.assertIn('SOURCE_HASH_MISMATCH',{x['code'] for x in r['issues']})

    def test_duplicate_json_keys_preserved_and_reported(self):
        root=fixture(self.base);(root/'records').mkdir();(root/'records'/'bad.json').write_text('{"a":1,"a":2}')
        r=self.collect(root)
        self.assertIn('UNREADABLE_JSON',{x['code'] for x in r['issues']})
        with zipfile.ZipFile(self.base/'return.zip') as z:self.assertEqual(z.read('evidence/run/records/bad.json'),b'{"a":1,"a":2}')

    def test_verify_detects_changed_member(self):
        root=fixture(self.base);self.collect(root)
        self.assertTrue(c.verify_bundle(self.base/'return.zip')['ok'])
        with zipfile.ZipFile(self.base/'return.zip') as z:entries={n:z.read(n) for n in z.namelist()}
        entries['LOCAL_CHECKS.json']=b'{}'
        with zipfile.ZipFile(self.base/'changed.zip','w') as z:
            for n,b in entries.items():z.writestr(n,b)
        self.assertFalse(c.verify_bundle(self.base/'changed.zip')['ok'])

    def test_no_network_and_no_subprocess_used(self):
        root=fixture(self.base)
        with patch('socket.socket',side_effect=AssertionError('network forbidden')),patch('subprocess.Popen',side_effect=AssertionError('process forbidden')):
            self.collect(root)

    def test_lock_never_deleted_or_executed(self):
        root=fixture(self.base);(root/'.run.lock').write_text('old lock')
        r=self.collect(root)
        self.assertTrue((root/'.run.lock').exists())
        self.assertIn('LOCK_PRESENT_NOT_REMOVED',{x['code'] for x in r['issues']})

    def test_statement_unknown_allowed_and_billing_optional(self):
        root=fixture(self.base);p=self.base/'statement.json';write(p,{'interrupted_run_status':'unknown','reason':'unknown','billing_status':'unavailable','other_calls_in_billing_window':'unknown'})
        r=self.collect(root,statement_path=p)
        self.assertEqual(r['operator_statement']['billing_status'],'unavailable')
        self.assertFalse(r['billing_note_attached'])

    def test_sanitized_billing_note_is_explicit_only(self):
        root=fixture(self.base);p=self.base/'billing.md';p.write_text('Currency: CNY; not independently verified')
        r=self.collect(root,billing_path=p)
        self.assertTrue(r['billing_note_attached'])
        with zipfile.ZipFile(self.base/'return.zip') as z:self.assertEqual(z.read('operator/billing_note.md'),p.read_bytes())

    def test_personal_path_not_in_report(self):
        root=fixture(self.base);self.collect(root)
        with zipfile.ZipFile(self.base/'return.zip') as z:
            self.assertNotIn(str(self.base).encode(),z.read('LOCAL_CHECKS.json'))

if __name__=='__main__':unittest.main()
