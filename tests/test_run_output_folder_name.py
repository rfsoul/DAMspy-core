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
    def test_resolve_selected_dut_definitions_defaults_to_legacy_fields(self):
        params = {
            "DUT_product": "hendrix-tx",
            "DUT_hardware_config": "S1B_sd_baseline",
            "DUT_serial_number": "TxRF_4",
            "foldername_comment": "bodyworn",
        }

        selected = run_module.resolve_selected_dut_definitions(params)

        self.assertEqual(
            selected,
            [
                {
                    "name": "",
                    "product": "hendrix-tx",
                    "hardware_config": "S1B_sd_baseline",
                    "serial_number": "TxRF_4",
                    "foldername_comment": "bodyworn",
                }
            ],
        )

    def test_resolve_selected_dut_definitions_uses_named_batch_selection(self):
        params = {
            "dut_definitions": {
                "DUT1": {
                    "product": "hendrix-tx",
                    "hardware_config": "S1B_sd_baseline",
                    "serial_number": "TxRF_4",
                    "foldername_comment": "bodyworn",
                },
                "DUT2": {
                    "product": "hendrix-tx",
                    "hardware_config": "s2b",
                    "serial_number": "TxRF_2",
                    "foldername_comment": "bodyworn",
                },
            },
            "DUTS": ["DUT1", "DUT2"],
        }

        selected = run_module.resolve_selected_dut_definitions(params)

        self.assertEqual([item["name"] for item in selected], ["DUT1", "DUT2"])
        self.assertEqual(selected[0]["hardware_config"], "S1B_sd_baseline")
        self.assertEqual(selected[1]["serial_number"], "TxRF_2")

    def test_apply_dut_definition_maps_named_dut_into_legacy_fields(self):
        params = {"yaml_comment": "kept"}
        dut_definition = {
            "name": "DUT2",
            "product": "hendrix-tx",
            "hardware_config": "s2b",
            "serial_number": "TxRF_2",
            "foldername_comment": "bodyworn",
        }

        resolved = run_module.apply_dut_definition(
            params,
            dut_definition,
            dut_index=2,
            total_duts=4,
        )

        self.assertEqual(resolved["DUT_product"], "hendrix-tx")
        self.assertEqual(resolved["DUT_hardware_config"], "s2b")
        self.assertEqual(resolved["DUT_serial_number"], "TxRF_2")
        self.assertEqual(resolved["foldername_comment"], "bodyworn")
        self.assertEqual(resolved["active_dut_name"], "DUT2")
        self.assertEqual(resolved["active_dut_index"], 2)
        self.assertEqual(resolved["active_dut_total"], 4)
        self.assertEqual(resolved["yaml_comment"], "kept")

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

    def test_dut_hardware_config_flows_into_foldername_when_provided(self):
        params = {
            "DUT_product": "DUT",
            "DUT_hardware_config": "V3-04F",
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

        self.assertIn("DUT_V3-04F_123", folder)

    def test_blank_dut_hardware_config_is_skipped_in_foldername(self):
        params = {
            "DUT_product": "DUT",
            "DUT_hardware_config": "",
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

        self.assertIn("DUT_123", folder)
        self.assertNotIn("DUT__123", folder)

    def test_max_angle_is_included_in_foldername(self):
        params = {
            "DUT_product": "DUT",
            "DUT_serial_number": "123",
            "foldername_comment": "",
            "orientations": [],
            "polarisation": [],
            "max_angle_deg": 170,
            "step_deg": 10,
            "sig_gen_1": {"channels": [], "power_levels": []},
            "rx_path": {"antenna": "main"},
        }

        folder = run_module.build_output_folder_name(
            "Antenna_Pattern_Measurement",
            "2026-04-09_12-00-00",
            params,
        )

        self.assertIn("MaxA_170", folder)

    def test_max_angle_list_is_included_in_foldername(self):
        params = {
            "DUT_product": "DUT",
            "DUT_serial_number": "123",
            "foldername_comment": "",
            "orientations": [],
            "polarisation": [],
            "max_angle_deg": [10, 30, 50],
            "step_deg": 10,
            "sig_gen_1": {"channels": [], "power_levels": []},
            "rx_path": {"antenna": "main"},
        }

        folder = run_module.build_output_folder_name(
            "Antenna_Pattern_Measurement",
            "2026-04-09_12-00-00",
            params,
        )

        self.assertIn("MaxA_10_30_50", folder)


if __name__ == "__main__":
    unittest.main()
