# Configuration Folder Overview

This folder contains all the YAML configuration files and subfolders that drive SETI test orchestration. Each file and subfolder has a distinct purpose:

---

## 1. `location_config.yaml`

**Purpose:**
Defines hardware and environment settings specific to the computer that will run the test.
If the computer is in the lab and using the ETS setup then use the ETS_RX_Equipments location
If the computer is at your desk then feel free to setup a location specific for your tests.

**Key Contents:**

* **Instrument Addresses:** IP addresses, VISA strings or COM port identifiers (e.g., `USB0::0xAAA4::0x0001::INSTR`, `COM4`).
* **Serial Numbers & Offsets:** Device serial numbers and any calibration offsets.
* **Default Timeouts:** Per-instrument timeouts (in seconds).

**Usage:**
When `run.py` launches, it picks a `location` (from `run_config.yaml`) and looks up the corresponding entry here to configure all equipment drivers.

---

## 2. `run_config.yaml`

**Purpose:**
Defines named test runs or scenarios. Each run groups together:

* The **radio** (e.g., `CP50`, `XRS335`) under test
* The **location** (key from `local_config.yaml`) to use
* The **test\_group** (key from `test_group_config.yaml`) to execute

**Example Structure:**

```yaml
MyCP50_RX:
  radio: CP50
  location: ETS_RX_Equipments
  test_group: ETSI_EN300086_CP50_RX
```

**Usage:**
Pass the run name (`-c MyCP50_RX`) to `run.py`; it then loads the radio, loads hardware configs, and executes the specified test group.

---

## 3. `test_group_config.yaml`

**Purpose:**
Defines sequences of tests, grouped under a logical name.

**Key Contents:**
For each group:

* **test\_name:** A descriptive identifier (must match a YAML filename in `test_settings_config/<profile>/`).
* **test\_config:** The name of the subfolder in `test_settings_config/` that contains the parameters for this test.

**Example:**

```yaml
ETSI_EN300086_CP50_RX:
  - test_name: frequency_error_test
    test_config: ETSI_EN300086_CP50_RX
  - test_name: adjacent_channel_selectivity
    test_config: ETSI_EN300086_CP50_RX
```

**Usage:**
`run.py` iterates through this list, loading each test’s settings from `test_settings_config/<test_config>/<test_name>.yaml`.

---

## 4. `test_settings_config/` Subfolder

**Purpose:**
Holds device- and standard-specific parameter files for each individual test.

**Layout:**

```
test_settings_config/
├── CUSTOM_GME_STANDARD/
│   ├── frequency_error_test.yaml
│   ├── measure_power_sig_gen.yaml
│   └── tx_cal_radio_to_spec_an.yaml
├── ETSI_EN300086_CP50_RX/
│   └── ...
├── ETSI_EN300086_CP50_TX/
│   └── ...
└── …
```

**Subfolder Names:**
Should match the `test_config` values used in `test_group_config.yaml`. They typically reference a regulatory standard or device-specific profile.

**YAML Files:**
Each file defines parameters for a single test, e.g.: frequency ranges, power levels, bandwidths, measurement tolerances. They are loaded by the test harness and passed into the test method implementations.

---

**Note on Adding New Tests:**

1. Add a new entry in `test_group_config.yaml` under the desired group.
2. Create (or use an existing) subfolder in `test_settings_config/` matching your `test_config`.
3. Add a `<test_name>.yaml` file defining that test’s parameters.

---

With this structure, you can add new hardware, define new test scenarios, and customize parameters without touching the core code.
