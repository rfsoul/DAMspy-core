"""
DAMspy – run.py

Generic runner responsibilities:
- build the top-level output folder name from the first test YAML
- copy the source YAML file(s) used for the run into the top-level run folder
- optionally create and maintain generic WOYM runtime state files:
    - <run_root>/woym.json
    - <DAMspy_logs>/latest_woym.json
- pass WOYM paths and basic run context into each test method

WOYM-specific measurement meaning stays in the test method.
"""

import importlib.util
import json
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from time import sleep

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


def sanitize_windows_path(name: str, fallback: str = "unknown") -> str:
    """Remove invalid Windows filename characters and normalise whitespace."""
    safe = "".join(c for c in str(name) if c not in r'<>:"/\\|?*')
    safe = safe.replace(" ", "_")
    safe = re.sub(r"_+", "_", safe)
    safe = safe.strip("._- ")
    return safe or fallback


def ensure_list(value):
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def list_token(prefix: str, values):
    values = ensure_list(values)
    if not values:
        return None
    joined = "_".join(sanitize_windows_path(v) for v in values)
    return f"{prefix}_{joined}"


def optional_token(value):
    if value is None:
        return None
    text = sanitize_windows_path(value, fallback="")
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
    """Build the top-level run folder name from the current test group and first YAML."""
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


def iso_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def write_json_atomic(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error = None

    # Windows readers can briefly lock the destination without delete-share,
    # which breaks os.replace even though a normal overwrite would succeed.
    for attempt in range(8):
        tmp_fd, tmp_name = tempfile.mkstemp(
            prefix=f"{path.name}.",
            suffix=".tmp",
            dir=str(path.parent),
            text=True,
        )
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp_name, path)
            return
        except PermissionError as e:
            last_error = e
            try:
                os.remove(tmp_name)
            except OSError:
                pass

            if attempt == 7:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                    f.flush()
                    os.fsync(f.fileno())
                return

            sleep(0.05 * (attempt + 1))
        except Exception:
            try:
                os.remove(tmp_name)
            except OSError:
                pass
            raise

    if last_error is not None:
        raise last_error


def append_recent_event(woym: dict, event: str, limit: int = 20):
    events = woym.setdefault("recent_events", [])
    events.append({
        "timestamp": iso_now(),
        "event": event,
    })
    if len(events) > limit:
        del events[:-limit]


def write_woym(woym: dict, run_woym_path: Path, latest_woym_path: Path):
    woym["updated_at"] = iso_now()
    write_json_atomic(run_woym_path, woym)
    write_json_atomic(latest_woym_path, woym)


def build_initial_woym(
    *,
    current_group: str,
    output_root: Path,
    run_woym_path: Path,
    latest_woym_path: Path,
) -> dict:
    return {
        "status": "initialising",
        "current_test_group": current_group,
        "current_test_method": "",
        "current_state": {
            "state": "initialising",
            "message": "Preparing DAMspy run",
            "target": {},
        },
        "current_sweep": {
            "sweep_index": 0,
            "total_sweeps": 0,
            "point_index": 0,
            "total_points": 0,
            "axis": "",
        },
        "last_measurement": {
            "timestamp": "",
        },
        "artifacts": {
            "run_root": str(output_root),
            "woym_path": str(run_woym_path),
            "latest_woym_path": str(latest_woym_path),
            "latest_yaml_path": "",
        },
        "error": {
            "status": "none",
            "message": "",
            "where": "",
            "timestamp": "",
        },
        "recent_events": [],
        "updated_at": iso_now(),
    }


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
    # Optional generic WOYM shell
    # ----------------------------------------------------------
    use_woym = bool(first_params.get("use_woym", False))
    run_woym_path = None
    latest_woym_path = None
    woym = None

    if use_woym:
        run_woym_path = output_root / "woym.json"
        latest_woym_path = root / "DAMspy_logs" / "latest_woym.json"

        print(f"[WOYM] Enabled")
        print(f"[WOYM] Run WOYM path: {run_woym_path}")
        print(f"[WOYM] Latest WOYM path: {latest_woym_path}")

        woym = build_initial_woym(
            current_group=current_group,
            output_root=output_root,
            run_woym_path=run_woym_path,
            latest_woym_path=latest_woym_path,
        )
        woym["artifacts"]["latest_yaml_path"] = str(output_root / first_yaml_path.name)
        append_recent_event(woym, "DAMspy run initialised")
        write_woym(woym, run_woym_path, latest_woym_path)
    else:
        print("[WOYM] Disabled by YAML")

    # ----------------------------------------------------------
    # Begin running each test
    # ----------------------------------------------------------
    for test_name in test_list:
        print("\n" + "=" * 100)
        print(f"➡ Running test: {test_name}")
        print("=" * 100)

        if use_woym and woym is not None:
            woym["status"] = "running"
            woym["current_test_method"] = test_name
            woym["current_state"] = {
                "state": "configuring",
                "message": f"Preparing test method '{test_name}'",
                "target": {},
            }
            append_recent_event(woym, f"Starting test method: {test_name}")
            write_woym(woym, run_woym_path, latest_woym_path)

        # Load individual test YAML
        yaml_path = root / "config" / "test_settings_config" / current_group / f"{test_name}.yaml"
        if not yaml_path.exists():
            error_msg = f"YAML missing: {yaml_path}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/main",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        params = load_yaml(yaml_path)
        if params is None:
            error_msg = f"YAML unreadable: {yaml_path}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/main",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        copy_yaml_to_output(yaml_path, output_root)

        if use_woym and woym is not None:
            woym["artifacts"]["latest_yaml_path"] = str(output_root / yaml_path.name)
            append_recent_event(woym, f"Copied YAML to run root: {yaml_path.name}")
            write_woym(woym, run_woym_path, latest_woym_path)

        # Pass common runtime context to every test
        params["output_dir"] = str(output_root)
        params["current_group"] = current_group
        params["current_test_method"] = test_name
        params["use_woym"] = use_woym
        params["woym_path"] = str(run_woym_path) if use_woym and run_woym_path else ""
        params["latest_woym_path"] = str(latest_woym_path) if use_woym and latest_woym_path else ""

        # ----------------------------------------------------------
        # Load test Python file
        # ----------------------------------------------------------
        py_path = root / "test_methods" / current_group / f"{test_name}.py"
        if not py_path.exists():
            error_msg = f"Script missing: {py_path}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/main",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        try:
            test_module = import_test_module(py_path)
        except Exception as e:
            error_msg = f"Could not import {test_name}: {e}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/import_test_module",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        if not hasattr(test_module, "run"):
            error_msg = f"Test {test_name} missing run() function"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/main",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        # ----------------------------------------------------------
        # Run the test
        # ----------------------------------------------------------
        try:
            test_module.run(params, equip_mgr)
            if use_woym and woym is not None:
                woym["status"] = "running"
                woym["error"] = {
                    "status": "none",
                    "message": "",
                    "where": "",
                    "timestamp": "",
                }
                woym["current_state"] = {
                    "state": "idle",
                    "message": f"Completed test method '{test_name}'",
                    "target": {},
                }
                append_recent_event(woym, f"Completed test method: {test_name}")
                write_woym(woym, run_woym_path, latest_woym_path)
        except Exception as e:
            error_msg = f"Test {test_name} failed: {e}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": f"{test_name}.run",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)

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
            error_msg = f"Post-processing script missing: {pp_path}"
            print(f"[WARN] {error_msg}")
            if use_woym and woym is not None:
                append_recent_event(woym, error_msg)
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        try:
            pp_module = import_test_module(pp_path)
        except Exception as e:
            error_msg = f"Could not import post-processing {pp_name}: {e}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                append_recent_event(woym, error_msg)
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/postprocessing_import",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        if not hasattr(pp_module, "run"):
            error_msg = f"Post-processing {pp_name} missing run()"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                append_recent_event(woym, error_msg)
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/postprocessing",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                write_woym(woym, run_woym_path, latest_woym_path)
            continue

        try:
            print(f"➡ Post-processing: {pp_name}")
            pp_module.run(str(output_root))
            if use_woym and woym is not None:
                append_recent_event(woym, f"Completed post-processing: {pp_name}")
                write_woym(woym, run_woym_path, latest_woym_path)
        except Exception as e:
            error_msg = f"Post-processing {pp_name} failed: {e}"
            print(f"[ERROR] {error_msg}")
            if use_woym and woym is not None:
                append_recent_event(woym, error_msg)
                woym["status"] = "error"
                woym["error"] = {
                    "status": "active",
                    "message": error_msg,
                    "where": "run.py/postprocessing_run",
                    "timestamp": iso_now(),
                }
                woym["current_state"] = {
                    "state": "error",
                    "message": error_msg,
                    "target": {},
                }
                write_woym(woym, run_woym_path, latest_woym_path)

    if use_woym and woym is not None and woym["status"] != "error":
        woym["status"] = "complete"
        woym["current_state"] = {
            "state": "complete",
            "message": "All tests finished",
            "target": {},
        }
        append_recent_event(woym, "DAMspy run complete")
        write_woym(woym, run_woym_path, latest_woym_path)

    print("\n=== All tests finished. ===")


# ----------------------------------------------------------
# Entry point
# ----------------------------------------------------------
if __name__ == "__main__":
    main()
