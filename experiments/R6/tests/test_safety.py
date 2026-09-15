import tempfile,unittest,pathlib,zipfile,json
from r6lib import storage,data,study
class SafetyTests(unittest.TestCase):
    def test_noncompleted_run_refuses_resample(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'configs').mkdir();storage.write_once(root/'configs/protocol.json',data.protocol());storage.make_manifest(root)
            study.prepare(root);storage.replace_local(study.run_dir(root)/'status.json',{'state':'paused'})
            with self.assertRaises(ValueError):study.run(root)
    def test_completed_run_no_sampling(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'configs').mkdir();storage.write_once(root/'configs/protocol.json',data.protocol());storage.make_manifest(root)
            study.prepare(root);storage.replace_local(study.run_dir(root)/'status.json',{'state':'completed'})
            self.assertTrue(study.run(root)['completed_run_no_resampling'])
    def test_source_change_after_prepare_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'configs').mkdir();storage.write_once(root/'configs/protocol.json',data.protocol());storage.make_manifest(root)
            study.prepare(root);(root/'evil.py').write_text('x=1')
            with self.assertRaises(ValueError):study.prepare(root)
    def test_bundle_rejects_path_traversal(self):
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/'a.zip'
            with zipfile.ZipFile(f,'w') as z:z.writestr('../a','x');z.writestr('BUNDLE_MANIFEST.json','{}')
            with self.assertRaises(ValueError):storage.verify_bundle(f)
    def test_bundle_preserves_license_and_excludes_unrelated_files(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'LICENSE').write_text('license');(root/'test.py').write_text('x=1');storage.make_manifest(root)
            (root/'.env').write_text('API_KEY=private')
            out=root/'uploads/a.zip';self.assertTrue(storage.bundle(root,out)['pass'])
            with zipfile.ZipFile(out) as z:
                self.assertIn('kit_source/LICENSE',z.namelist());self.assertFalse(any('.env' in x for x in z.namelist()))
    def test_bundle_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'x.py').write_text('a=1');storage.make_manifest(root);dest=root/'a.zip';storage.bundle(root,dest)
            with self.assertRaises(FileExistsError):storage.bundle(root,dest)
    def test_lock_has_no_implicit_unlock(self):
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/'.write.lock';f.write_text('existing')
            with self.assertRaises(FileExistsError):
                with storage.lock(td):pass
            self.assertEqual(f.read_text(),'existing')
    def test_secret_in_export_is_blocked(self):
        with tempfile.TemporaryDirectory() as td:
            root=pathlib.Path(td);(root/'unsafe.txt').write_text('Bearer '+'q'*32);storage.make_manifest(root)
            with self.assertRaises(ValueError):storage.bundle(root,root/'a.zip')
    def test_archive_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            f=pathlib.Path(td)/'a.zip'
            with zipfile.ZipFile(f,'w') as z:
                z.writestr('x','a');z.writestr('BUNDLE_MANIFEST.json',json.dumps({'files':{'x':{'bytes':1,'sha256':'wrong'}}}))
            self.assertFalse(storage.verify_bundle(f)['pass'])
    def test_bad_windows_path_rejected(self):
        for name in ['C:/secrets','a\\b','../a','/tmp/a']:self.assertFalse(storage.safe_path(name))
if __name__=='__main__':unittest.main()
