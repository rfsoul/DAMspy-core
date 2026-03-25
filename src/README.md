# DAMspy — Diamond Antenna Measurement System (Python)

DAMspy is a configuration‑driven, test‑first antenna measurement framework.
It controls an azimuth/elevation positioner, reads RF power from an analyzer,
and writes tidy results for plotting and post‑processing. The design keeps
**drivers, test methods, and analysis** cleanly separated so you can iterate
quickly in **simulate** mode, then flip to **live** without changing core code.

---

## 1) Folder layout

```
damspy/
├─ run.py                         # entry point (PyCharm/GUI friendly)
├─ damspy_main.py                 # orchestration API used by GUI and scripts
├─ config/
│  ├─ local_config.yaml           # machine-specific; includes runtime.simulate
│  ├─ run_config.yaml             # global defaults (rbw/averages/dwell/outputs)
│  ├─ location_config.yaml        # chamber limits + coordinate conventions
│  ├─ test_group_config.yaml      # optional grouping of scans
│  └─ test_settings_config/
│     └─ Antenna_Scans/
│        ├─ example_spherical.yml
│        └─ example_principal_cuts.yml
├─ equipment/
│  ├─ positioner/
│  │  ├─ diamond_d6050.py
│  │  └─ stand_alone_operation/   # home/jog/goto tools
│  ├─ spectrum_analyser/
│  │  ├─ CMW500.py
│  │  └─ stand_alone_operation/   # *IDN?, quick power read
│  ├─ signal_generator/
│  │  ├─ VSG60A.py                 # optional (Signal Hound or similar)
│  │  └─ stand_alone_operation/   # set CW freq/level, RF on/off
│  └─ utils/
│     ├─ driver_base.py
│     ├─ equipment_loader.py
│     └─ manifest.py
├─ test_methods/
│  └─ Antenna_Scans/
│     ├─ spherical_scan.py
│     └─ principal_cuts.py
├─ test_postprocessing/
│  └─ antenna/
│     ├─ efficiency.py
│     ├─ grids.py
│     └─ reporting.py
├─ DAMSPY_logging/
│  └─ README.md
├─ DAMspy_logs/                   # per-run folders (CSV/manifest/logs/plots)
├─ results/                       # optional final plots/reports
└─ data/
   ├─ raw/
   └─ processed/
```

---

## 2) Configuration model

### 2.1 `config/local_config.yaml`
- **Source of truth for hardware** and developer‑machine defaults.
- Contains `runtime.simulate: true|false` (master simulate switch).
- Includes connection info (COM ports, VISA strings), default speeds/limits, and logging destinations.
> Recommendation: treat this file as developer‑local (gitignore or environment‑specific overlay).

### 2.2 `config/run_config.yaml`
- Global defaults for acquisition and outputs: `rbw_hz`, `averages`, `dwell_ms`, `settle_ms` and output knobs (`save_csv`, `make_report`, `log_dir`).

### 2.3 `config/location_config.yaml`
- Coordinate conventions + motion constraints.
  - **Azimuth:** counter‑clockwise viewed from above, 0° at chamber front.
  - **Elevation:** 0° boresight, +90° zenith, −90° nadir.
- Hard limits (az/el min/max) for safety enforcement.

### 2.4 Per‑run test YAMLs (`config/test_settings_config/Antenna_Scans/*.yml`)
- Define **what** to do (plan + parameters):
  - `principal_cuts`: H‑plane (el=0 sweep az) + E‑plane (az=0 sweep el).
  - `spherical`: grid over az×el.
- Do **not** include `simulate`; it inherits from `local_config.yaml`.
- Optional `equipment_override` block may temporarily adjust ports/VISA per run.

Example:
```yaml
run:
  name: "whip2g4_principal"
  operator: "Al Morgan"
  frequency_hz: 2_440_000_000
  scan_plan: { type: principal_cuts, cut_step_deg: 5, settle_ms: 250 }
  averages: 5
  dwell_ms: 100
```

---

## 3) Orchestration API

### 3.1 `run.py`
- Loads a per‑run YAML and merges `runtime.simulate` from `local_config.yaml`.
- Prints a concise summary, then calls `damspy_main.main_from_config_dict(cfg)`.

### 3.2 `damspy_main.py`
- Exposes **`main_from_config_dict(cfg)`** and an optional **`RunController`**:
  - `RunController(cfg, on_progress, on_log).start()` → returns the **primary output path** (e.g., CSV).
  - `on_progress` receives dicts like: `{"phase":"scan","az":120,"el":10,"i":42,"n":720}`.
  - `on_log` receives printable strings.
- Both GUI and headless execution should use this same API.

---

## 4) Drivers (`equipment/`)

**Plugin pattern:**
- `utils/driver_base.py` defines abstract shapes (PositionerBase/MeterBase).
- `utils/equipment_loader.py` reads configs and instantiates concrete drivers.

**Simulation support is mandatory:**
- In simulate mode: no hardware I/O; track synthetic position/time and return deterministic pseudo‑measurements.
- In live mode: perform SCPI/serial I/O with tight timeouts and clear exceptions.

**Standalone smoke tools** (`stand_alone_operation/`):
- Positioner: home/jog/goto helpers.
- Analyzer: *IDN?* and quick power reads.
- Signal generator: CW frequency/level and RF on/off.

---

## 5) Test methods

### 5.1 `principal_cuts.py`
- H‑plane: sweep az at el=0°.
- E‑plane: sweep el at az=0°.
- Average N power readings, honor dwell/settle per config.
- Write tidy CSV rows:  
  `timestamp_iso, cut, freq_Hz, az_deg, el_deg, power_dBm, samples, dwell_ms`.

### 5.2 `spherical_scan.py`
- Iterate az×el grid (configurable start/stop/step).
- Same averaging and CSV schema (minus `cut`).

**Run folder naming:**  
`YYYY_MM_DD_HHMMh_DAMspy_<Plan>_<FreqMHz>/` under `DAMspy_logs/`.

---

## 6) Post‑processing (`test_postprocessing/antenna`)

- `grids.py`: resample/interpolate to uniform az/el grids (with masking).
- `efficiency.py`: spherical integration → TRP and radiation efficiency.
- `reporting.py`: principal‑cut polar plots, az×el heatmaps, optional 3D surface; export PNG/HTML to the run folder or `results/`.

---

## 7) Data & metadata

Each run directory should include:
- **Primary CSV** (tidy rows as above).
- **`manifest.json`** (via `utils/manifest.py`):
  - run name, frequency, plan, creation time
  - checksums/paths for calibration files (if used)
  - environment (Python version / platform)
- **`run_config_snapshot.yml`** (the per‑run YAML copy).
- Optional plots/report.

> Tip: also write Parquet in `data/raw/` for fast analysis at scale.

---

## 8) Simulate vs live

- `runtime.simulate` lives in `local_config.yaml`. The loader passes it into drivers and test methods.
- Simulate drivers should produce **repeatable** outputs to support unit tests and CI.

---

## 9) Development workflow (test‑driven)

1. Start in **simulate**: ensure `run.py` → orchestration → test method flow works.
2. Implement **principal cuts** first (fast iteration), then **spherical**.
3. Add **manifest** and **atomic CSV writing** (temp → rename).
4. Switch to live drivers; keep simulate path intact.
5. Add post‑processing (plots, efficiency) once data schema is stable.
6. (Optional) Add GUI as a thin layer over `RunController`.

**Unit tests to prioritize:**
- Coordinate conversions + limit enforcement (including az wrap‑around at 360°).
- Grid building and efficiency integration.
- Driver timeouts & exceptions (simulate + live).

---

## 10) Coding standards

- No SCPI/serial in test methods—**drivers only**.
- Typed functions and docstrings; use dedicated exceptions.
- Centralized logging; include run_id and step metadata in each log line.
- Resumability: consider a small progress file; a future `resume` option can pick up mid‑grid.
- Style: Black/ruff recommended; favor small, composable functions.

---

## 11) Quick start (PyCharm)

1. Create `config/local_config.yaml` and set `runtime.simulate: true`.
2. Open `run.py`; set Script parameters to:
   ```
   -c config/test_settings_config/Antenna_Scans/example_principal_cuts.yml
   ```
3. Run. You’ll see a summary; underlying methods may fail until stubs are filled.
4. Implement simulate drivers → principal cuts → verify a CSV appears in `DAMspy_logs/`.

---

## 12) Roadmap / TODO

- [ ] Simulate drivers for positioner, analyzer, and generator
- [ ] Principal cuts sampler + CSV writer
- [ ] Manifest + YAML snapshot per run
- [ ] Plots: principal‑cut polar + 2D heatmap
- [ ] Spherical scan + efficiency integration
- [ ] GUI thin layer over `RunController`
- [ ] Live drivers with timeouts, e‑stop, and safety checks

---

## 13) Coordinate conventions (pin this)

- **Azimuth (az):** CCW from chamber front (viewed from above).
- **Elevation (el):** 0° boresight; +90° up (zenith), −90° down (nadir).
- Persist these conventions in code comments, `location_config.yaml`, and run outputs.