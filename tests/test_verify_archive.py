import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from verify_archive import verify, safe_relative

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'record.txt').write_bytes(b'original evidence\n')
        self.entry={'path':'record.txt','bytes':18,'sha256':hashlib.sha256(b'original evidence\n').hexdigest()}
        self.manifest([self.entry])
    def manifest(self, entries):
        (self.root/'ARCHIVE_MANIFEST.json').write_text(json.dumps({'files':entries}))
    def test_exact(self):
        self.assertEqual(verify(self.root)['verified_files'],1)
    def test_changed_bytes(self):
        (self.root/'record.txt').write_bytes(b'fabricated output\n')
        with self.assertRaises(ValueError): verify(self.root)
    def test_missing(self):
        (self.root/'record.txt').unlink()
        with self.assertRaises(ValueError): verify(self.root)
    def test_duplicate(self):
        self.manifest([self.entry,self.entry])
        with self.assertRaises(ValueError): verify(self.root)
    def test_extra(self):
        (self.root/'unregistered.txt').write_text('extra')
        with self.assertRaises(ValueError): verify(self.root)
    def test_git_metadata_ignored(self):
        (self.root/'.git').mkdir();(self.root/'.git'/'HEAD').write_text('ref: refs/heads/main')
        self.assertEqual(verify(self.root)['verified_files'],1)
    def test_fonts_refused(self):
        e=dict(self.entry,path='a.ttf');(self.root/'record.txt').rename(self.root/'a.ttf');self.manifest([e])
        with self.assertRaises(ValueError): verify(self.root)
    def test_symlink_refused(self):
        (self.root/'record.txt').rename(self.root/'real.txt');(self.root/'record.txt').symlink_to('real.txt')
        with self.assertRaises(ValueError): verify(self.root)
    def test_paths(self):
        for p in ('../escape','/absolute','a/../b','C:/x','a\\b','./a','a//b',''):
            with self.subTest(p=p):
                with self.assertRaises(ValueError): safe_relative(p)
        self.assertEqual(str(safe_relative('feedback/数据.json')),'feedback/数据.json')
    def test_bad_size_type(self):
        self.manifest([dict(self.entry,bytes=True)])
        with self.assertRaises(ValueError): verify(self.root)
    def test_bad_hash(self):
        self.manifest([dict(self.entry,sha256='not-a-digest')])
        with self.assertRaises(ValueError): verify(self.root)
    def test_secret_filename(self):
        e=dict(self.entry,path='.env');(self.root/'record.txt').rename(self.root/'.env');self.manifest([e])
        with self.assertRaises(ValueError): verify(self.root)

if __name__=='__main__': unittest.main()
