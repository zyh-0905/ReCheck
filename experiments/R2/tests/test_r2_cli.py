
import copy,tempfile,unittest,importlib.util,json
from pathlib import Path
from pilot.common import read_json,write_json
import r2
from r2lib import protocol,storage,session

class CLITests(unittest.TestCase):
    def fn(self,name):
        self.assertTrue(callable(getattr(r2,name,None)),name+" missing");return getattr(r2,name)
    def test_cap_consent_required(self):
        with self.assertRaises(ValueError):self.fn("require_call_consent")(0,484)
    def test_exact_cap_consent(self):
        self.fn("require_call_consent")(484,484)
        with self.assertRaises(ValueError):r2.require_call_consent(485,484)
    def test_fixed_output_limit(self):
        c=read_json(Path(__file__).resolve().parents[1]/"config.example.json")
        c["max_output_tokens"]=4096
        with self.assertRaises(ValueError):session.validate_r2_config(c)
    def test_thinking_toggle_explicit_supported(self):
        c=read_json(Path(__file__).resolve().parents[1]/"config.example.json")
        q=session.validate_r2_config(c)
        self.assertEqual(q["extra_body"],{"thinking":{"type":"enabled"},"reasoning_effort":"high"})
    def test_no_smoke_no_run(self):
        with tempfile.TemporaryDirectory() as d:
            c=read_json(Path(__file__).resolve().parents[1]/"config.example.json")
            with self.assertRaises(ValueError):self.fn("require_smoke")(Path(d),c)
    def test_smoke_profile_mismatch_no_run(self):
        with tempfile.TemporaryDirectory() as d:
            c=read_json(Path(__file__).resolve().parents[1]/"config.example.json")
            write_json(Path(d)/"runs/R2_smoke/smoke_result.json",{"json_ok":True,"profile_sha256":"wrong"})
            write_json(Path(d)/"runs/R2_smoke/status.json",{"state":"completed"})
            with self.assertRaises(ValueError):self.fn("require_smoke")(Path(d),c)
    def test_freeze_config_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as d:
            c=read_json(Path(__file__).resolve().parents[1]/"config.example.json")
            m=storage.freeze(Path(d),c,"r2_recheck",protocol.load_protocol(),{"enabled":False})
            c["model"]="other"
            with self.assertRaises(ValueError):storage.freeze(Path(d),c,"r2_recheck",protocol.load_protocol(),{"enabled":False})

    def test_fixture_label_not_allowed_on_remote_endpoint(self):
        c=read_json(Path(__file__).resolve().parents[1]/"config.example.json")
        c["backend_kind"]="test_fixture"
        with self.assertRaises(ValueError):session.validate_r2_config(c)
