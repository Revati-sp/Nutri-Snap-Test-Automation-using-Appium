# Nutri Snap — AI Test Automation (Appium + Python)

**CMPE 287 — Deliverable #3**  
Team automation project: **native iOS** apps **FoodZilla**, **SnapCalorie**, and **Lose It!**, exercised with **Appium** and **Python** on **macOS** against a **physical iPhone** (XCUITest). Test design follows the **3D AI test model** from **Deliverable #2B** (same course).

---

## Overview

We built a **config-driven** automation framework that:

- Loads **93 executable rows** from `data/testcases.csv` (31 logical testcase IDs × **one row per app**).
- Filters runs by **`app_name`** so each teammate can execute **only FoodZilla**, **only SnapCalorie**, or **only Lose It!** in a batch.
- Starts an **Appium / XCUITest** session from **YAML** (device UDID, iOS version, bundle ID, signing, server URL).
- Runs **shared** plumbing (driver, waits, data load, validation, CSV results, summary stats) and **app-specific** packages under `apps/` for locators and page flows.

The framework is intended for **repeatable** batch runs, **structured logging**, and **clear extension points** for a team of **four** developers on **different machines**.

---

## Objectives

| Objective | How the repo supports it |
|-----------|---------------------------|
| **Executable test scripting** | Python batch runner `tests/run_all.py` drives rows from CSV/JSON; each row is one app-level run. |
| **Repeatable execution** | Same data file + config contract; append-only results CSV; exit code reflects pass/fail counts. |
| **3D model–based complexity** | CSV columns carry **context / input** dimensions (`section`, `subsection`, `dimension_type`, `sub_dimension`, `item_description`); **output** is modeled as a single combined `expected_output` string (Food Detection + Food Classification as written in 2B). |
| **Team-ready local setup** | Per-machine YAML (`config/member*_local.yaml` or personal copies) without editing shared Python for device-specific values. |

---

## Current status (honest)

| Area | Status |
|------|--------|
| **Driver, config, CSV/JSON load, validation chain, results CSV, HTML report, stats, screenshots per case** | Implemented under `framework/` and `tests/run_all.py`. |
| **Shared scan → image → read flow** | Implemented in `framework/ios_food_scan_page.py`; app pages delegate to it. |
| **App-specific UI** | **`apps/*/locators.py` still use TODO accessibility IDs.** Real flows require **Appium Inspector** (or Xcode) on **your** builds to replace `SCAN_ENTRY`, `RESULT_PANEL`, and optional `PHOTO_*` / `RESULT_*` locators. |
| **`data/testcases.csv`** | Contains **93** rows aligned to the 2B model; **`expected_output`** is populated from the team’s Deliverable **2B** report. If you re-import or scaffold rows, replace any **`__REPLACE_WITH_DELIVERABLE_2B__`** placeholder before trusting PASS/FAIL (see §Test data). |

---

## Architecture and folder structure

Shared logic stays in **`framework/`**; each product has **`locators.py`**, **`page.py`**, and **`tests.py`** under **`apps/<app>/`**. Configuration is YAML under **`config/`**. External test data and images live under **`data/`**. Run outputs go under **`reports/`** (gitignored artifacts: `results.csv`, `screenshots/`).

```
CMPE287 Automation Appium Python Framework/
├── README.md
├── requirements.txt
├── .gitignore
├── config/
│   ├── config_template.yaml
│   ├── member1_local.yaml
│   ├── member2_local.yaml
│   └── member3_local.yaml
├── data/
│   ├── testcases.csv              # 93 rows — primary testcase source
│   ├── testcases.example.json     # JSON shape reference (optional)
│   └── images/
│       └── TC01.jpg … TC31.jpg    # Images referenced by image_path
├── framework/
│   ├── __init__.py
│   ├── base_driver.py             # XCUITest session, waits, screenshots
│   ├── config_loader.py
│   ├── data_loader.py
│   ├── ios_food_scan_page.py      # Shared open → scan → image → read steps
│   ├── logger.py
│   ├── report_generator.py       # HTML batch summary next to CSV
│   ├── result_logger.py
│   ├── stats.py
│   ├── utils.py
│   └── validator.py
├── apps/
│   ├── foodzilla/
│   │   ├── locators.py
│   │   ├── page.py
│   │   └── tests.py
│   ├── snapcalorie/
│   │   ├── locators.py
│   │   ├── page.py
│   │   └── tests.py
│   └── loseit/
│       ├── locators.py
│       ├── page.py
│       └── tests.py
├── reports/
│   └── .gitkeep                   # generated results.csv / screenshots/ not committed
└── tests/
    └── run_all.py                 # CLI batch runner (--app filter)
```

---

## Test model (Deliverable 2B → 93 rows)

- **31** testcase IDs (`test_id` **1**–**31**). Each ID is executed for **all three** apps → **93** rows in `data/testcases.csv`.
- **Context (IDs 1–8)**  
  - **1–4:** Illumination  
  - **5–8:** Background  
- **Input (IDs 9–31)**  
  - **9–12:** Plating  
  - **13–16:** Packaging  
  - **17–20:** Category  
  - **21–23:** State  
  - **24–31:** Item Test  
- **Output (conceptual):** Food **Detection** and **Classification** are represented in the CSV as one string field: **`expected_output`** (and at runtime **`actual_output`**), formatted to match what the app displays and what was recorded in **2B**.

---

## Prerequisites

- **macOS** with **full Xcode** (not Command Line Tools only) — required to build **WebDriverAgent** for a real device.
- **Physical iPhone** (USB or supported wireless debugging), **Developer Mode** enabled where iOS requires it, device **trusted** on the Mac.
- **Apple Developer** access: **Team ID** and a signing identity that can run the three apps on that device.
- **Node.js** + **npm** (for Appium server).
- **Python 3.9+** (project tested with a local `venv` and `requirements.txt`).
- **Appium 3.x** (recommended) or **2.x**, with the **XCUITest** driver installed.
- The three **production or debug builds** installed on the phone, with **bundle IDs** known for YAML.

---

## Installation (Python)

From the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt    # installs Appium-Python-Client, PyYAML, etc.
```

The batch runner adds the repo root to `sys.path` when you execute `tests/run_all.py`.

---

## iPhone and macOS setup

1. Install **Xcode** from the App Store; open it once and accept the license.
2. Set the active developer directory (adjust path if your Xcode.app name differs):

   ```bash
   sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
   xcodebuild -version
   ```

3. Connect the iPhone; unlock it; tap **Trust** when prompted.
4. Note the device **UDID** (Xcode → **Window → Devices and Simulators**, or `xcrun devicectl list devices` on newer Xcode).
5. Note **iOS version** (**Settings → General → About**) for `platform_version` in YAML.

---

## Appium setup

Install Appium and the XCUITest driver (example for Appium 3):

```bash
npm install -g appium@3
appium driver install xcuitest
appium driver list --installed
```

Start the server (default matches `appium.server_url` in the YAML templates):

```bash
appium server --address 127.0.0.1 --port 4723
```

Leave this process running in a dedicated terminal while tests execute. For signing and provisioning issues on a physical phone, see the [Appium XCUITest driver — real device configuration](https://appium.github.io/appium-xcuitest-driver/latest/real-device-config/) documentation.

---

## Configuration (YAML)

Each teammate keeps a **local YAML** (e.g. `config/member1_local.yaml` or a **personal copy** such as `config/jane_local.yaml`). Point `--config` at that file when running.

**Important:** `app.bundle_id` must match the **app currently installed** on the phone for that run. Switching from FoodZilla to SnapCalorie usually means **editing YAML** or using **separate YAML files** per app.

### Example `config/my_local.yaml`

```yaml
device:
  name: "CMPE287 iPhone"
  udid: "00008110-001A109C12345678"   # example format only — use your real UDID
  platform_version: "18.2"          # must match the device

app:
  bundle_id: "com.yourteam.foodzilla"   # change when targeting another app

appium:
  server_url: "http://127.0.0.1:4723"

xcode:
  org_id: "ABCDE12345"              # Apple Developer Team ID
  signing_id: "Apple Development"

session:
  wda_local_port: null
  new_command_timeout: 120
```

The checked-in `config/member*_local.yaml` files use **`REPLACE_*`** placeholders for UDID, Team ID, bundle IDs, and iOS version—copy them to a **private** file (and add that filename to `.gitignore` if needed) before putting real values.

Do **not** commit real UDIDs or team secrets if your course or employer forbids it—use **git-ignored** personal files or environment-specific copies.

---

## Test data file format

**Primary file:** `data/testcases.csv` (**93** data rows + header).

**Required columns** (CSV header or JSON keys on each object):

`test_id`, `app_name`, `section`, `subsection`, `dimension_type`, `sub_dimension`, `item_description`, `image_path`, `expected_output`

**Optional** columns in the source file (ignored for control flow; the runner overwrites them in the **report**): `actual_output`, `result`

**`app_name` values** in the CSV must match one of: **`FoodZilla`**, **`SnapCalorie`**, **`Lose It!`** (spacing/capitalization is normalized internally).

**`image_path`:** Paths such as `data/images/TC01.jpg` are resolved relative to the **repository root**.

### Expected output placeholders (setup TODO)

If any row still has **`expected_output`** equal to **`__REPLACE_WITH_DELIVERABLE_2B__`** (constant `DELIVERABLE_2B_PLACEHOLDER` in `framework/validator.py`) or **blank**, validation will **FAIL** with an explicit message until you paste the correct **2B** expected string for that row. Use find-in-files on that placeholder string across the repo after merges. After editing the CSV, re-run batches; no code change is required.

**JSON:** Supported via `framework/data_loader.py` — either a top-level array of objects or `{"testcases": [...]}` with the same required keys. Use `--data path/to/file.json`.

---

## How to run tests for one app

From the **repository root**, with the venv activated and Appium server running:

**FoodZilla only (31 rows):**

```bash
python tests/run_all.py --config config/member1_local.yaml --app FoodZilla
```

**SnapCalorie only:**

```bash
python tests/run_all.py --config config/member2_local.yaml --app SnapCalorie
```

**Lose It! only** (quote the name because of spaces):

```bash
python tests/run_all.py --config config/member3_local.yaml --app "Lose It!"
```

Ensure each YAML’s **`bundle_id`** matches the app you pass to **`--app`**.

Optional flags:

- `--data path/to/alternate.csv` — default is `data/testcases.csv`
- `--report path/to/results.csv` — default is `reports/results.csv` (**append** mode)
- `--no-screenshots` — skip PNG capture after each testcase
- `--no-html-report` — skip generating `reports/test_report_*.html`

---

## How to run all 93 tests (all three apps)

The CLI accepts **one `--app` per process**. To cover **all three** apps (93 rows total), run **three** batches—**update `bundle_id`** (or use **three YAML files**) between runs so the session targets the correct binary:

```bash
# Example: three configs, one per app (recommended)
python tests/run_all.py --config config/foodzilla_local.yaml --app FoodZilla --report reports/results-foodzilla.csv
python tests/run_all.py --config config/snapcalorie_local.yaml --app SnapCalorie --report reports/results-snapcalorie.csv
python tests/run_all.py --config config/loseit_local.yaml --app "Lose It!" --report reports/results-loseit.csv
```

Exit code **0** means the batch finished with **no FAIL and no ERROR** rows; **1** means at least one failure or error; **2** means no rows matched the `--app` filter (wrong app name or empty data).

Using **separate `--report` files** avoids mixing three apps in one append-only CSV unless you intend to.

If your **`results.csv`** was created **before** the **`screenshot_path`** column existed, start a **new** `--report` path (or delete the old CSV) so the header matches the current columns.

---

## Results and reporting

- **`reports/results.csv`** (or your `--report` path): **append-only** CSV with columns  
  `test_id`, `app_name`, `section`, `subsection`, `dimension_type`, `sub_dimension`, `item_description`, `image_path`, `expected_output`, `actual_output`, `result`, `error_message`, `screenshot_path`, `timestamp`.
- **`result`:** `PASS`, `FAIL`, or `ERROR` (exceptions or runner-reported errors).
- **Screenshots:** After **each** testcase (including **`PASS`**), a PNG is saved under **`reports/screenshots/`** (named with outcome). Disable with **`--no-screenshots`** if needed.
- **HTML report:** After each batch, **`reports/test_report_<UTC>.html`** and **`reports/test_report_latest.html`** summarize the same rows with thumbnail links. Skip with **`--no-html-report`**.
- **Console / logs:** A one-line **summary** (totals, pass, fail, errors, pass percentage) is printed at the end of each batch.

---

## Validation behavior

`framework/validator.py` compares **`expected_output`** to **`actual_output`** using a **fixed-order rule chain** (extensible later for fuzzy or rubric-specific rules):

1. **`PlaceholderExpectedRule`** — fails if `expected_output` is empty or still **`__REPLACE_WITH_DELIVERABLE_2B__`**.
2. **`NormalizedExactOutputRule`** — passes if strings match after trim, lowercase, and whitespace collapse.
3. **`NormalizedSubstringOutputRule`** — passes if one normalized string contains the other (minimum length **4** on each side to reduce accidental passes).
4. **`FinalMismatchRule`** — terminal failure with both normalized strings in the message.

**Future work:** Add new `OutputMatchRule` classes (synonyms, token overlap, JSON field-wise compare, per-dimension tolerance) and register them in `default_output_validator()` without changing the batch runner contract.

---

## Team workflow

1. **Clone** the repo; create **`venv`**; `pip install -r requirements.txt`.
2. Each member maintains **their own YAML** (UDID, iOS version, signing, and **bundle_id** for the app they run most often).
3. **Share** `data/testcases.csv` and **`data/images/`** through git when appropriate; keep **secrets** out of version control if required.
4. **Split Inspector work** by app: update **`apps/<app>/locators.py`**, then adjust **`page.py`** only if you need overrides beyond the shared **`ios_food_scan_page`** behavior.
5. **Run** one app at a time during development; merge **results CSVs** or use distinct `--report` paths for grading evidence.

---

## Mapping to Deliverable #3 expectations (rubric-oriented)

| Theme | This repository |
|--------|-------------------|
| **Executable automation** | `tests/run_all.py` + `apps/*/tests.py` execute CSV rows against a live Appium session. |
| **Repeatability** | External data file, deterministic runner, append-only results, exit code from summary. |
| **3D AI model coverage** | Rows encode **context** and **input** dimensions; **output** is checked via **`expected_output`** vs **`actual_output`** after UI reads are implemented. |
| **Engineering quality** | Page Object–style layout, shared framework vs app modules, explicit waits, per-case screenshots + CSV/HTML reporting, modular validation. |

---

## Known limitations and TODOs

- **Locators** are **not** production-complete; **Appium Inspector** (or Xcode) is required on each app’s current UI.
- **Photo selection** on iOS varies by app and OS version: optional locators `PHOTO_LIBRARY_BUTTON`, `PHOTO_PICKER_CELL`, etc., must be filled for `select_image` to do more than log warnings.
- **`read_model_output`** assumes the UI eventually exposes text matching **2B** `expected_output` format (single panel or split detection/classification locators).
- **One device per run** in the current runner; parallel devices would need process-level orchestration outside this script.
- **No** cloud device farm or CI Mac worker is configured in-repo.

---

## Troubleshooting

| Symptom | Things to check |
|--------|-------------------|
| **`xcodebuild` errors** / WDA will not install | Full **Xcode** selected via `xcode-select`; valid **Team ID** and **signing_id**; iPhone **Developer Mode**; device registered for development. |
| **Session start fails** | Appium process running; `appium.server_url` correct; USB/wifi debugging; firewall blocking **4723**. |
| **App opens wrong binary** | `bundle_id` in YAML matches the app under test; `activate_app` uses that bundle. |
| **No rows executed** | `--app` spelling vs `app_name` column; CSV path with `--data`. |
| **Immediate validation failures** | `expected_output` still placeholder or format mismatch vs on-screen text; adjust locators / `read_model_output` or extend validator rules. |
| **Timeouts on result** | Increase AI wait tolerance in `framework/ios_food_scan_page.py` or stabilize network on device. |

---

## Example commands (quick reference)

```bash
# Terminal A — Appium
appium server --address 127.0.0.1 --port 4723

# Terminal B — Python (from repo root, venv on)
python tests/run_all.py --config config/member1_local.yaml --app FoodZilla
python tests/run_all.py --config config/member2_local.yaml --app SnapCalorie
python tests/run_all.py --config config/member3_local.yaml --app "Lose It!"

# Alternate data / report paths
python tests/run_all.py --config config/my_local.yaml --app FoodZilla \
  --data data/testcases.csv --report reports/run-2026-04-29.csv
```

---

## Course and repository

**Course:** CMPE 287 — Software Quality Assurance and Testing.  
**Deliverable:** #3 — AI-related test automation for native iOS nutrition / computer-vision apps.  
**Remote:** [Nutri-Snap-Test-Automation-using-Appium](https://github.com/Revati-sp/Nutri-Snap-Test-Automation-using-Appium) (team GitHub; use the branch and tags your instructor expects).

For questions about **2B** testcase semantics, refer to the team’s **Deliverable 2B** document; this README only describes how those cases are **represented and executed** in automation.
