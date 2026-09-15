import unittest,tempfile,json,hashlib,importlib.util
from pathlib import Path
s=importlib.util.spec_from_file_location('r12_verify',Path(__file__).resolve().parents[1]/'verify_archive.py')
m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class ArchiveTests(unittest.TestCase):
    def make_root(self,p):
        (p/'a.txt').write_bytes(b'abc')
        (p/'MANIFEST.json').write_text(json.dumps({'files':{'a.txt':{'bytes':3,'sha256':hashlib.sha256(b'abc').hexdigest()}}}))
    def test_valid(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.make_root(p);self.assertTrue(m.verify(p)['ok'])
    def test_changed(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);self.make_root(p);(p/'a.txt').write_bytes(b'changed');self.assertFalse(m.verify(p)['ok'])
