"""
DAMspy – run.py

Updates in this version:
- Top-level output folder name is derived from the first test YAML using:
  current_group, timestamp, DUT_product, DUT_serial_number,
  foldername_comment, orientations, channels, power levels,
  polarisations, step size, and RX antenna.
- Copies the source YAML file(s) used for the run into the top-level run folder
  using their original filenames.
- Leaves per-test measurement logic unchanged.
"""

import importlib.util
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml

from equipment.utils.equipment_loader import EquipmentLoader


# ----------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------

def load_yaml(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def import_test_module(py_path: Path):
    """Import test file by absolute path so filenames can start with digits."""
    mod_name = py_path.stem
    spec = importlib.util.spec_from_file_location(mod_name, str(py_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot import test module from {py_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sanitize_windows_path(name: str) -> str:
    """
    Remove invalid Windows filename characters and normalise whitespace.
    """
    safe = "".join(c for c in str(name) if c not in r'<>:"/\|?*')
    safe = safe.replace(" ", "_")
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("._- ")
    return safe or "unknown"


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def list_token(prefix: str, values) -> str | None:
    values = ensure_list(values)
    if not values:
        return None
    joined = "_".join(sanitize_windows_path(v) for v in values)
    return f"{prefix}_{joined}"


def optional_token(value) -> str | None:
    if value is None:
        return None
    text = sanitize_windows_path(value)
    return text if text else None


def copy_yaml_to_output(yaml_path: Path, outdir: Path):
    if not yaml_path.exists():
        print(f"[WARN] YAML not found for copy: {yaml_path}")
        return

    dest = outdir / yaml_path.name
    try:
        shutil.copy2(yaml_path, dest)
        print(f"[INFO] Copied YAML to run root: {dest}")
    except Exception as e:
        print(f"[WARN] Failed to copy YAML {yaml_path} -> {dest}: {e}")


def resolve_runtime_mode(repo_root: Path) -> str:
    localenv_path = repo_root / "operating_env" / ".localenv"

    if not localenv_path.exists():
        return "virtual"

    try:
        with open(localenv_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()

                if not line or line.startswith("#"):
                    continue

                if "=" not in line:
                    continue

                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()

                if key == "DAMSPY_RUNTIME_MODE":
                    return "real" if value == "real" else "virtual"

    except Exception as e:
        print(f"[WARN] Could not read {localenv_path}: {e}")
        return "virtual"

    return "virtual"


def build_output_folder_name(current_group: str, timestamp: str, first_params: dict) -> str:
    """
    Build the top-level run folder name from the current test group and first YAML.
    """
    dut_product = first_params.get("DUT_product", "UnknownDUT")
    dut_serial_number = first_params.get("DUT_serial_number", "UnknownSerial")
    foldername_comment = first_params.get("foldername_comment")

    orientations = first_params.get("orientations", [])
    polarisations = first_params.get("polarisation", [])
    step_deg = first_params.get("step_deg", "unknown")

    sg_cfg = first_params.get("sig_gen_1", {})
    channels = sg_cfg.get("channels", [])
    power_levels = sg_cfg.get("power_levels", [])

    rx_cfg = first_params.get("rx_path", {})
    rx_antenna = rx_cfg.get("antenna", "Unknown")

    parts = [
        sanitize_windows_path(current_group),
        timestamp,
        sanitize_windows_path(f"{dut_product}_{dut_serial_number}"),
        optional_token(foldername_comment),
        list_token("Ori", orientations),
        list_token("Ch", channels),
        list_token("Pwr", power_levels),
        list_token("Pol", polarisations),
        f"Step_{sanitize_windows_path(step_deg)}deg",
        f"RxAnt_{sanitize_windows_path(rx_antenna)}",
    ]

    return "-".join(part for part in parts if part)


# ----------------------------------------------------------
# Main Execution
# ----------------------------------------------------------

def main():
    print("\n=== DAMspy Test Runner ===")

    root = Path(__file__).resolve().parent
    repo_root = root.parent

    runtime_mode = resolve_runtime_mode(repo_root)
    print(f"[INFO] Runtime mode resolved: {runtime_mode}")

    if runtime_mode != "real":
        print("[INFO] Virtual runtime is not implemented yet.")
        print("[INFO] Exiting before equipment initialization.")
        sys.exit(0)

    # ---------------- Load Group Config ----------------
    group_cfg = load_yaml(root / "config" / "test_group_run_config.yaml")

    current_group = group_cfg.get("current_test_group")
    if not current_group:
        raise RuntimeError("Missing 'current_test_group' in test_group_run_config.yaml")

    group_block = group_cfg[current_group]
    test_list = group_block.get("tests", [])
    required_equipment = group_block.get("required_equipment", [])
    postprocs = group_block.get("test_postprocessing", [])

    print(f"Current Test Group: {current_group}")
    print(f"Tests to run: {test_list}")
    print(f"Post-processing scripts: {postprocs}")

    if not test_list:
        raise RuntimeError(f"No tests configured for group '{current_group}'")

    # ---------------- Load Equipment ----------------
    equip_cfg_path = root / "config" / "location_config.yaml"
    equip_mgr = EquipmentLoader(equip_cfg_path, required_equipment)
    print("Equipment loaded.")

    # ----------------------------------------------------------
    # Determine top-level output folder from the first test YAML
    # ----------------------------------------------------------
    first_test_name = test_list[0]
    first_yaml_path = root / "config" / "test_settings_config" / current_group / f"{first_test_name}.yaml"
    first_params = load_yaml(first_yaml_path)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = build_output_folder_name(current_group, timestamp, first_params)

    output_root = root / "DAMspy_logs" / folder_name
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"[LOG] Output directory: {output_root}")

    # Copy the first YAML immediately so the run root is self-describing
    copy_yaml_to_output(first_yaml_path, output_root)

    # ----------------------------------------------------------
    # Begin running each test
    # ----------------------------------------------------------
    for test_name in test_list:
        print("\n" + "=" * 100)
        print(f"➡ Running test: {test_name}")
        print("=" * 100)

        # Load individual test YAML
        yaml_path = root / "config" / "test_settings_config" / current_group / f"{test_name}.yaml"
        if not yaml_path.exists():
            print(f"[ERROR] YAML missing: {yaml_path}")
            continue

        params = load_yaml(yaml_path)
        if params is None:
            print(f"[ERROR] YAML unreadable: {yaml_path}")
            continue

        # Copy each test YAML to the run root using its original filename.
        # This future-proofs multi-test groups.
        copy_yaml_to_output(yaml_path, output_root)

        # Pass the SAME top-level output directory to every test
        params["output_dir"] = str(output_root)

        # ----------------------------------------------------------
        # Load test Python file
        # ----------------------------------------------------------
        py_path = root / "test_methods" / current_group / f"{test_name}.py"
        if not py_path.exists():
            print(f"[ERROR] Script missing: {py_path}")
            continue

        try:
            test_module = import_test_module(py_path)
        except Exception as e:
            print(f"[ERROR] Could not import {test_name}: {e}")
            continue

        if not hasattr(test_module, "run"):
            print(f"[ERROR] Test {test_name} missing run() function")
            continue

        # ----------------------------------------------------------
        # Run the test
        # ----------------------------------------------------------
        try:
            test_module.run(params, equip_mgr)
        except Exception as e:
            print(f"[ERROR] Test {test_name} failed: {e}")

    # ----------------------------------------------------------
    # Run post-processing (group-level)
    # ----------------------------------------------------------
    if postprocs:
        print("\n=== Running post-processing ===")

    for pp_name in postprocs:
        pp_path = (
            root
            / "test_postprocessing"
            / current_group
            / f"{pp_name}.py"
        )

        if not pp_path.exists():
            print(f"[WARN] Post-processing script missing: {pp_path}")
            continue

        try:
            pp_module = import_test_module(pp_path)
        except Exception as e:
            print(f"[ERROR] Could not import post-processing {pp_name}: {e}")
            continue

        if not hasattr(pp_module, "run"):
            print(f"[ERROR] Post-processing {pp_name} missing run()")
            continue

        try:
            print(f"➡ Post-processing: {pp_name}")
            pp_module.run(str(output_root))
        except Exception as e:
            print(f"[ERROR] Post-processing {pp_name} failed: {e}")

    print("\n=== All tests finished. ===")


# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    main()