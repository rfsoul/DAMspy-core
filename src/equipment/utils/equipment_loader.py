import importlib
import yaml

class EquipmentLoader:
    """
    Loads only the equipment listed in required_equipment.
    Supported patterns in required_equipment:
        - "positioner"
        - "spectrum_analyser"
        - "signal_generator.sig_gen_1"

    Matching rules:
        - If "category" is required → load ALL devices under that category
        - If "category.device" is required → load ONLY that device
    """

    def __init__(self, config_path, required_equipment):
        self._drivers = {}
        self.required = required_equipment

        # --------------------
        # Load top-level YAML
        # --------------------
        with open(config_path, "r") as f:
            full_cfg = yaml.safe_load(f)

        # Find active location
        loc_name = full_cfg.get("current_location")
        if not loc_name:
            raise RuntimeError("location_config.yaml missing 'current_location'.")

        loc_block = full_cfg.get(loc_name)
        if not loc_block:
            raise RuntimeError(f"Location '{loc_name}' not found in location_config.yaml.")

        equip_cfg = loc_block.get("equipment", {})
        if not isinstance(equip_cfg, dict):
            raise RuntimeError("equipment block must be a dictionary.")

        # --------------------
        # Load categories
        # --------------------
        for category, cat_cfg in equip_cfg.items():

            # Skip category if not required
            if not self._category_required(category):
                continue

            # SINGLE-DEVICE CATEGORY
            if isinstance(cat_cfg, dict) and "driver" in cat_cfg:
                inst = self._build_device(cat_cfg)
                setattr(self, category, inst)
                self._drivers[category] = inst
                print(f"  ✔ Loaded device '{category}'")
                continue

            # MULTI-DEVICE CATEGORY
            if isinstance(cat_cfg, dict):
                devices = {}

                for dev_name, dev_cfg in cat_cfg.items():

                    # Skip device if not required
                    if not self._device_required(category, dev_name):
                        continue

                    if not isinstance(dev_cfg, dict):
                        print(f"[EquipmentLoader] Skipping '{category}.{dev_name}' (invalid structure)")
                        continue

                    inst = self._build_device(dev_cfg)
                    devices[dev_name] = inst
                    self._drivers[f"{category}.{dev_name}"] = inst
                    print(f"  ✔ Loaded device '{category}.{dev_name}'")

                # Flatten if only one device
                if len(devices) == 1:
                    setattr(self, category, next(iter(devices.values())))
                else:
                    setattr(self, category, devices)

                continue

            print(f"[EquipmentLoader] Skipping '{category}' (invalid structure)")

    # =========================================================================
    # REQUIRED-EQUIPMENT MATCHING LOGIC
    # =========================================================================
    def _category_required(self, category):
        """
        True if:
            - category is directly required ("positioner")
            - any entry in required_equipment references this category ("positioner.a", "positioner.b")
        """
        for item in self.required:
            if item == category:
                return True
            if item.startswith(category + "."):
                return True
        return False

    def _device_required(self, category, device):
        """
        True if:
            - whole category is required ("positioner")
            - exact device match required ("signal_generator.sig_gen_1")
        """
        if category in self.required:
            return True

        full = f"{category}.{device}"
        return full in self.required

    # =========================================================================
    # DEVICE BUILDER
    # =========================================================================
    def _build_device(self, cfg):
        module_path = cfg["driver"].replace("/", ".").replace("\\", ".").replace(".py", "")
        module = importlib.import_module(module_path)
        cls = getattr(module, cfg["class_name"])
        return cls(cfg)
