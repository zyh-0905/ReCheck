import hashlib
import io
import pathlib
import tempfile
import unittest
import zipfile

from collect_materials import (validate_url, wheel_rank, select_release_file,
    verify_bytes, repository_tree, verify_source_zip, pick_filename, build_bundle,
    safe_error, DownloadFailure)

def archive(content):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as z:
        for name, data in content.items():
            zi = zipfile.ZipInfo('ToolSandbox-test/' + name)
            zi.external_attr = 0o100644 << 16
            z.writestr(zi, data)
    return stream.getvalue()

class CollectorTests(unittest.TestCase):
    def test_https_allowlist(self):
        self.assertEqual(validate_url('https://pypi.org/pypi/dill/0.3.8/json'), 'pypi.org')
    def test_credentials_rejected(self):
        with self.assertRaises(ValueError): validate_url('https://user:secret@pypi.org/file')
    def test_http_rejected(self):
        with self.assertRaises(ValueError): validate_url('http://pypi.org/file')
    def test_suffix_domain_rejected(self):
        with self.assertRaises(ValueError): validate_url('https://pypi.org.example.com/file')
    def test_loopback_rejected(self):
        with self.assertRaises(ValueError): validate_url('https://127.0.0.1/file')
    def test_query_only_permitted_for_release_redirect(self):
        with self.assertRaises(ValueError): validate_url('https://pypi.org/file?token=secret')
        self.assertEqual(validate_url('https://release-assets.githubusercontent.com/a?sig=x'),
                         'release-assets.githubusercontent.com')
    def test_pure_wheel_compatible(self):
        self.assertGreater(wheel_rank('dill-0.3.8-py3-none-any.whl'), 0)
    def test_cp38_abi3_linux_compatible(self):
        self.assertGreater(wheel_rank('polars-0.20.31-cp38-abi3-manylinux_2_17_x86_64.whl'),0)
    def test_cp311_linux_compatible(self):
        self.assertGreater(wheel_rank('numpy-1.26.4-cp311-cp311-manylinux_2_17_x86_64.whl'),0)
    def test_wrong_python_rejected(self):
        self.assertEqual(wheel_rank('x-1-cp313-cp313-manylinux_2_17_x86_64.whl'),0)
    def test_wrong_platform_rejected(self):
        for name in ('x-1-cp311-cp311-macosx_11_0_arm64.whl','x-1-cp311-cp311-win_amd64.whl',
                     'x-1-cp311-cp311-manylinux_2_17_aarch64.whl','x-1-cp311-cp311-musllinux_1_1_x86_64.whl'):
            self.assertEqual(wheel_rank(name),0)
    def test_release_name_version_binding(self):
        with self.assertRaises(ValueError): select_release_file({'info':{'name':'wrong','version':'1'},'urls':[]}, 'x','1')
    def test_yanked_release_file_excluded(self):
        row={'filename':'x-1-py3-none-any.whl','packagetype':'bdist_wheel','yanked':True}
        with self.assertRaises(ValueError): select_release_file({'info':{'name':'x','version':'1'},'urls':[row]},'x','1')
    def test_source_fallback_explicit(self):
        row={'filename':'x-1.tar.gz','packagetype':'sdist','yanked':False,'requires_python':None}
        meta={'info':{'name':'x','version':'1'},'urls':[row]}
        with self.assertRaises(ValueError): select_release_file(meta,'x','1')
        self.assertEqual(select_release_file(meta,'x','1',allow_sdist=True),row)
    def test_sha256_rejected(self):
        with self.assertRaises(ValueError): verify_bytes(b'x','0'*64)
    def test_sha256_pass(self):
        verify_bytes(b'abc',hashlib.sha256(b'abc').hexdigest())
    def test_source_tree_hash(self):
        data=archive({'file.txt':b'hello','dir/a.py':b'print(1)\n'})
        tree=repository_tree({'file.txt':('100644',b'hello'),'dir/a.py':('100644',b'print(1)\n')})
        self.assertEqual(verify_source_zip(data,tree)['tree_sha1'],tree)
    def test_modified_source_tree_rejected(self):
        data=archive({'file.txt':b'changed'})
        tree=repository_tree({'file.txt':('100644',b'original')})
        with self.assertRaises(ValueError): verify_source_zip(data,tree)
    def test_archive_traversal_rejected(self):
        with self.assertRaises(ValueError): verify_source_zip(archive({'../bad':b'x'}),'0'*40)
    def test_archive_duplicate_rejected(self):
        with self.assertRaises(ValueError): repository_tree({'a':('100644',b'x'),'a/b':('100644',b'y')})
    def test_bad_file_name_rejected(self):
        for name in ('../x.whl','a/b.whl','a\\b.whl','C:x.whl',''):
            with self.assertRaises(ValueError): pick_filename(name)
    def test_bundle_only_whitelist(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); (p/'public.txt').write_text('safe'); (p/'.env').write_text('SECRET')
            out=p/'result.zip'
            build_bundle(p,['public.txt'],out,{'status':'fixture'})
            with zipfile.ZipFile(out) as z:
                self.assertEqual(set(z.namelist()),{'public.txt','DOWNLOAD_REPORT.json','BUNDLE_MANIFEST.json'})
                self.assertNotIn(b'SECRET',b''.join(z.read(n) for n in z.namelist()))
    def test_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            p=pathlib.Path(d); o=p/'a.zip'; o.write_bytes(b'old')
            with self.assertRaises(FileExistsError): build_bundle(p,[],o,{})
            self.assertEqual(o.read_bytes(),b'old')
    def test_error_redacts_query_and_paths(self):
        msg=safe_error(Exception('https://release-assets.githubusercontent.com/x?secret=abc /home/person'))
        self.assertNotIn('abc',msg)
        self.assertNotIn('/home/person',msg)

if __name__ == '__main__': unittest.main()

class EndToEndOfflineFixtures(unittest.TestCase):
    """All bytes below are test fixtures, NOT downloaded public artifacts."""
    def test_success_exports_fixture_artifacts_without_installation(self):
        import collect_materials as c
        from unittest.mock import patch
        import contextlib
        source=archive({'LICENSE':b'fixture license','file.py':b'# fixture\n'})
        tree=repository_tree({'LICENSE':('100644',b'fixture license'),'file.py':('100644',b'# fixture\n')})
        runtime=b'FAKE_RUNTIME_NOT_EXECUTABLE'
        wheel=b'FAKE_WHEEL_NOT_EXECUTABLE'
        meta={'info':{'name':'fixture','version':'1'},'urls':[{
            'filename':'fixture-1-py3-none-any.whl','packagetype':'bdist_wheel','yanked':False,
            'url':'https://files.pythonhosted.org/fixture.whl','size':len(wheel),
            'digests':{'sha256':hashlib.sha256(wheel).hexdigest()}}]}
        bodies={c.SOURCE_URL:source,c.PYTHON_URL:runtime,
                'https://pypi.org/pypi/fixture/1/json':c.json_bytes(meta),
                'https://files.pythonhosted.org/fixture.whl':wheel}
        class D:
            total=0
            def get(self,url,target,limit=c.MAX_FILE_BYTES,sha256=None,expected_size=None):
                data=bodies[url]
                if sha256 is not None: verify_bytes(data,sha256)
                if expected_size is not None: assert expected_size==len(data)
                assert len(data)<=limit
                self.total+=len(data)
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(data)
                return {'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
        with tempfile.TemporaryDirectory() as td, patch.object(c,'TREE',tree), \
             patch.object(c,'PYTHON_SHA256',hashlib.sha256(runtime).hexdigest()), \
             patch.object(c,'PACKAGES',[('fixture','1')]), contextlib.redirect_stdout(io.StringIO()):
            root=pathlib.Path(td)
            self.assertEqual(c.collect(root,D()),0)
            path=next(root.glob('*.zip'))
            with zipfile.ZipFile(path) as z:
                import json
                report=json.loads(z.read('DOWNLOAD_REPORT.json'))
                self.assertFalse(report['downloaded_code_executed'])
                self.assertFalse(report['packages_installed'])
                self.assertEqual(report['new_llm_calls'],0)
                for name,item in json.loads(z.read('BUNDLE_MANIFEST.json'))['files'].items():
                    self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),item['sha256'])
            with self.assertRaises(FileExistsError): c.collect(root,D())

    def test_network_failure_exports_diagnostic_not_fake_completion(self):
        import collect_materials as c
        import contextlib
        import json
        class D:
            total=0
            def get(self,*a,**k): raise OSError('network blocked')
        with tempfile.TemporaryDirectory() as td, contextlib.redirect_stdout(io.StringIO()):
            p=pathlib.Path(td)
            self.assertEqual(c.collect(p,D()),2)
            with zipfile.ZipFile(next(p.glob('*.zip'))) as z:
                r=json.loads(z.read('DOWNLOAD_REPORT.json'))
                self.assertEqual(r['status'],'INCOMPLETE_DOWNLOAD')
                self.assertEqual(r['artifacts'],[])
                self.assertEqual(r['failure']['stage'],'source')
