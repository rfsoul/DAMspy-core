import importlib.util
import os
import sys
import unittest


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_ROOT = os.path.join(REPO_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

MODULE_PATH = os.path.join(SRC_ROOT, "run.py")
spec = importlib.util.spec_from_file_location("run_module", MODULE_PATH)
run_module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(run_module)


class RunOutputFolderNameTests(unittest.TestCase):
    def test_optional_foldername_comment_empty_string_is_skipped(self):
        params = {
            "DUT_product": "DUT",
            "DUT_serial_number": "123",
            "foldername_comment": "",
            "orientations": [],
            "polarisation": [],
            "step_deg": 10,
            "sig_gen_1": {"channels": [], "power_levels": []},
            "rx_path": {"antenna": "main"},
        }

        folder = run_module.build_output_folder_name(
            "Antenna_Pattern_Measurement",
            "2026-04-09_12-00-00",
            params,
        )

        self.assertNotIn("unknown", folder)
        self.assertNotIn("--", folder)

    def test_optional_foldername_comment_keeps_text_when_provided(self):
        params = {
            "DUT_product": "DUT",
            "DUT_serial_number": "123",
            "foldername_comment": "comment",
            "orientations": [],
            "polarisation": [],
            "step_deg": 10,
            "sig_gen_1": {"channels": [], "power_levels": []},
            "rx_path": {"antenna": "main"},
        }

        folder = run_module.build_output_folder_name(
            "Antenna_Pattern_Measurement",
            "2026-04-09_12-00-00",
            params,
        )

        self.assertIn("-comment-", folder)


if __name__ == "__main__":
    unittest.main()
