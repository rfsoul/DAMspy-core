"""
DAMspy v17 – run.py (corrected FULL version)
- DUT suffix applied to TOP-LEVEL output directory
- NO per-test subfolder
- AF/Loss files copied into root output directory
- Compatible with DAMspy v17 architecture
"""

import importlib.util
import yaml
import os
import sys
from pathlib import Path
from datetime import datetime
from equipment.utils.equipment_loader import EquipmentLoader
import shutil


# ----------------------------------------------------------
# Utility Functions
# ----------------------------------------------------------

def load_yaml(path: Path):
    with open(path, "r") as f:
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
    """Remove invalid Windows filename characters."""
    safe = "".join(c for c in name if c not in r'<>:"/\|?*')
    return safe.replace(" ", "_").strip()


def safe_copy(src: str, outdir: Path):
    """Copy AF and Loss CSVs into the output root directory."""
    if not src:
        return
    src_path = Path(src)
    if src_path.exists():
        try:
            dest = outdir / src_path.name
            shutil.copy2(src_path, dest)
            print(f"[INFO] Copied: {dest}")
        except Exception as e:
            print(f"[WARN] Failed to copy {src}: {e}")
    else:
        print(f"[WARN] File not found: {src}")

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

# ----------------------------------------------------------
# Main Execution
# ----------------------------------------------------------

def main():
    print("\n=== DAMspy v17 Test Runner ===")

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
    print(f' postprocessing script: {postprocs}')

    # ---------------- Load Equipment ----------------
    equip_cfg_path = root / "config" / "location_config.yaml"
    equip_mgr = EquipmentLoader(equip_cfg_path, required_equipment)
    print("Equipment loaded.")

    # ----------------------------------------------------------
    # Determine DUT BEFORE creating output folder (use first test's YAML)
    # ----------------------------------------------------------
    first_test_name = test_list[0]
    first_yaml_path = root / "config" / "test_settings_config" / current_group / f"{first_test_name}.yaml"
    first_params = load_yaml(first_yaml_path)

    dut_raw = first_params.get("DUT", "Unknown")
    dut_clean = sanitize_windows_path(dut_raw)

    # ----------------------------------------------------------
    # Create TOP-LEVEL output directory with DUT suffix
    # ----------------------------------------------------------
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_root = root / "DAMspy_logs" / f"{current_group}_{timestamp}_{dut_clean}"
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"[LOG] Output directory: {output_root}")

    # Copy AF + Loss files ONCE per test run
    safe_copy(first_params.get("antenna_factor_file"), output_root)
    safe_copy(first_params.get("path_loss_file"), output_root)

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

        # Pass the SAME output directory to every test
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
