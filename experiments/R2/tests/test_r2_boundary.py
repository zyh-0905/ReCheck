
import json,tempfile,unittest,zipfile
from pathlib import Path
from pilot.common import default_config,read_json,write_json
from r2lib import storage,review
class BoundaryTests(unittest.TestCase):
    def fn(self,module,name):
        self.assertTrue(callable(getattr(module,name,None)),name+" missing");return getattr(module,name)
    def test_export_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"offline_reports").mkdir()
            (root/"offline_reports/PREFLIGHT.json").write_text('{"pass":false}')
            out=root/"uploads/x.zip"
            self.fn(storage,"export_bundle")(root,out)
            with self.assertRaises(FileExistsError):storage.export_bundle(root,out)
    def test_export_excludes_local_secrets(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"offline_reports").mkdir();(root/"offline_reports/a.json").write_text("{}")
            (root/"config.local.json").write_text('{"fake":"not for export"}');(root/".env").write_text("SECRET=abc")
            out=root/"uploads/x.zip";self.fn(storage,"export_bundle")(root,out)
            names=zipfile.ZipFile(out).namelist()
            self.assertNotIn("config.local.json",names);self.assertNotIn(".env",names)
    def test_export_symlink_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"offline_reports").mkdir();(root/"normal.txt").write_text("private")
            try:(root/"offline_reports/link.txt").symlink_to(root/"normal.txt")
            except (OSError,NotImplementedError):self.skipTest("symlinks not supported")
            with self.assertRaises(ValueError):self.fn(storage,"export_bundle")(root,root/"uploads/x.zip")
    def test_export_key_pattern_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"offline_reports").mkdir()
            (root/"offline_reports/bad.json").write_text('{"value":"sk-'+("X"*32)+'"}')
            with self.assertRaises(ValueError):self.fn(storage,"export_bundle")(root,root/"uploads/x.zip")
    def test_prior_regression_reproduced(self):
        q=self.fn(review,"regression_checks")()
        self.assertTrue(q["pass"]);self.assertEqual(q["examples"],2)
    def test_repair_cost_not_call_count(self):
        q=self.fn(review,"repair_cost_diagnostic")()
        self.assertLess(q["local_patch_call_ratio"],1)
        self.assertGreater(q["local_patch_cost_ratio"],2)
        self.assertGreater(q["selection_cost_to_all_generation"],1)
        self.assertEqual(q["new_model_calls"],0)
    def test_orphan_result_not_passed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"attempts").mkdir()
            write_json(root/"attempts/000001_result.json",{"attempt":1,"status":"ok","logical_id":"x"})
            q=self.fn(review,"ledger_check")(root)
            self.assertFalse(q["pass"]);self.assertTrue(q["orphan_results"])
    def test_registered_not_claimed_sent(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/"attempts").mkdir()
            write_json(root/"attempts/000001_start.json",{"attempt":1,"logical_id":"x"})
            q=self.fn(review,"ledger_check")(root)
            self.assertEqual(q["registered_without_result"],1)
            self.assertEqual(q["unconfirmed_remote_receipt"],1)
