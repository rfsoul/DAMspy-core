import importlib
import os
import yaml
from DAMspy_logging.pretty_printing import header, line, success, error

def RunTestGroup(test_list, equip_mgr, logger, test_group_name):
    header(f"Running DAMSpy Test Group: {test_group_name}")

    for test_name in test_list:
        line(f"➡ Running test: {test_name}")

        yaml_path = os.path.join("config", "test_settings_config", test_group_name, f"{test_name}.yaml")
        py_module_path = f"test_methods.{test_group_name}.{test_name}"

        if not os.path.isfile(yaml_path):
            error(f"[{test_name}] Missing test config file: {yaml_path}")
            continue

        try:
            with open(yaml_path, "r") as f:
                test_cfg = yaml.safe_load(f)
        except Exception as e:
            error(f"[{test_name}] Failed to load YAML config: {e}")
            continue

        try:
            test_module = importlib.import_module(py_module_path)
        except Exception as e:
            error(f"[{test_name}] Failed to import test module: {e}")
            continue

        try:
            if hasattr(test_module, "run"):
                result = test_module.run(equip_mgr, None, logger, test_cfg)
                if result:
                    success(f"{test_name} completed successfully.")
                else:
                    error(f"{test_name} reported failure.")
            else:
                error(f"{test_name} has no run() function.")
        except Exception as e:
            error(f"{test_name} failed during execution: {e}")

    footer = success if all(getattr(logger, "passed", False) for _ in test_list) else error
    footer(f"[{test_group_name}] {'✅ All tests passed' if logger.passed else '❌ Some tests failed'}")
