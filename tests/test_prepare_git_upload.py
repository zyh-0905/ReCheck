import hashlib,json,subprocess,sys,tempfile,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from prepare_git_upload import prepare, validate_origin

class UploadPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'evidence.log').write_bytes(b'raw evidence\r\n')
        (self.root/'数据.json').write_bytes(b'{"verdict":false}\n')
        (self.root/'.gitignore').write_text('*.log\n*.json\n',encoding='utf8')
        self.manifest()
    def manifest(self):
        entries=[]
        for p in self.root.iterdir():
            if p.is_file() and p.name!='ARCHIVE_MANIFEST.json':
                b=p.read_bytes();entries.append({'path':p.name,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()})
        (self.root/'ARCHIVE_MANIFEST.json').write_text(json.dumps({'files':entries}),encoding='utf8')
    def git(self,*args,**kwargs):
        return subprocess.run(['git',*args],cwd=self.root,capture_output=True,check=True,**kwargs).stdout
    def init(self):
        self.git('init','-b','main');self.git('remote','add','origin','https://github.com/zyh-0905/ReCheck.git')
    def test_dry_run_does_not_create_git(self):
        self.assertEqual(prepare(self.root)['files_to_stage'],4)
        self.assertFalse((self.root/'.git').exists())
    def test_stage_requires_git_repo(self):
        with self.assertRaises(ValueError):prepare(self.root,stage=True)
    def test_accepted_origin_forms(self):
        for url in ['https://github.com/zyh-0905/ReCheck.git','git@github.com:zyh-0905/ReCheck.git','ssh://git@github.com/zyh-0905/ReCheck.git']:
            self.assertTrue(validate_origin(url))
    def test_wrong_origin_rejected(self):
        for url in ['https://github.com/Sorasky681/ReCheck.git','https://github.com/zyh-0905/RepairLens.git','https://token@github.com/zyh-0905/ReCheck.git']:
            with self.assertRaises(ValueError):validate_origin(url)
    def test_stage_ignored_data_exactly(self):
        self.init();r=prepare(self.root,stage=True)
        self.assertEqual(r['index_verified_files'],4)
        self.assertEqual(self.git('show',':evidence.log'),b'raw evidence\r\n')
        self.assertIn('数据.json'.encode(),self.git('ls-files','-z'))
    def test_no_filters_executed(self):
        (self.root/'.gitattributes').write_text('*.log filter=fail text\n',encoding='utf8');self.manifest();self.init()
        self.git('config','filter.fail.clean','false');self.git('config','filter.fail.required','true')
        self.git('config','core.autocrlf','true')
        self.assertEqual(prepare(self.root,stage=True)['index_verified_files'],5)
        self.assertEqual(self.git('show',':evidence.log'),b'raw evidence\r\n')
    def test_stage_has_no_commit(self):
        self.init();prepare(self.root,stage=True)
        r=subprocess.run(['git','rev-parse','--verify','HEAD'],cwd=self.root,capture_output=True)
        self.assertNotEqual(r.returncode,0)
    def test_index_check(self):
        self.init();prepare(self.root,stage=True)
        self.assertEqual(prepare(self.root,check_index=True)['index_verified_files'],4)
    def test_idempotent_stage(self):
        self.init();prepare(self.root,stage=True)
        before=(self.root/'.git/index').read_bytes()
        self.assertTrue(prepare(self.root,stage=True)['already_staged'])
        self.assertEqual(before,(self.root/'.git/index').read_bytes())
    def test_wrong_remote_aborts_without_index(self):
        self.init();self.git('remote','set-url','origin','https://github.com/zyh-0905/RepairLens.git')
        with self.assertRaises(ValueError):prepare(self.root,stage=True)
        self.assertFalse((self.root/'.git/index').exists())
    def test_tampered_file_rejected(self):
        self.init();(self.root/'evidence.log').write_text('changed')
        with self.assertRaises(ValueError):prepare(self.root,stage=True)
    def test_existing_partial_index_refused(self):
        self.init();self.git('add','-f','evidence.log')
        with self.assertRaises(ValueError):prepare(self.root,stage=True)
    def test_reject_nested_repo_root(self):
        self.init();sub=self.root/'sub';sub.mkdir();(sub/'a.txt').write_text('a')
        (sub/'ARCHIVE_MANIFEST.json').write_text(json.dumps({'files':[{'path':'a.txt','bytes':1,'sha256':hashlib.sha256(b'a').hexdigest()}]}))
        with self.assertRaises(ValueError):prepare(sub,stage=True)
if __name__=='__main__':unittest.main()
