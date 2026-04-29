# CMPE287 — Appium iOS (Python) starter framework

Config-driven Appium **XCUITest** automation for **native iOS** apps on a **real iPhone** from **macOS**. Shared framework code lives under `framework/`; each product has its own package under `apps/` with **placeholder** locators and page methods until your team wires real UI.

Test design follows your **3D AI test model** (Deliverable **2B**): **31** unique `test_id` values, each executed on **all three** apps (**FoodZilla**, **SnapCalorie**, **Lose It!**), for **93** app-level rows total. Context cases cover **Illumination** and **Background** (IDs **1–8**); input cases cover **Plating**, **Packaging**, **Category**, **State**, and **Item Test** (**9–31**). The seven dimensions are: **Background**, **Illumination**, **Packaging**, **Category**, **State**, **Item Test**, **Plating**. Model outputs are **Food Detection** and **Food Classification**, represented in data as a single combined **`expected_output`** string (same for `actual_output` at run time—format must match your 2B export).

## Prerequisites

- macOS with Xcode and developer signing set up for WebDriverAgent on device
- [Appium](https://appium.io/) 2.x server installed and running (default `http://127.0.0.1:4723`)
- Python **3.9+** recommended
- **Your** Deliverable **2B** testcase export as `data/testcases.csv` or JSON (see below). The repo **`data/testcases.csv`** contains **93** rows (**31** IDs × **3** apps) with **`expected_output`** and **`item_description`** transcribed from the **Spartan QAs Deliverable 2B** report (per-app wording preserved where the PDF differs, e.g. TC2 Lose It! spacing). **`data/images/TC01.jpg`–`TC31.jpg`** are minimal valid **placeholder** JPEGs so paths resolve—replace with your real test photos when you run on device.

## Setup

From the project root:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Copy `config/config_template.yaml` to a **local, git-ignored** file (or use `member*_local.yaml` as a starting point) and set:

| YAML path | Purpose |
|-----------|---------|
| `device.name` | `deviceName` for capabilities |
| `device.udid` | Physical device UDID |
| `device.platform_version` | iOS version on the device |
| `app.bundle_id` | App under test |
| `appium.server_url` | Appium server URL |
| `xcode.org_id` | Apple Developer Team ID (for WDA) |
| `xcode.signing_id` | e.g. `Apple Development` |

Replace placeholder bundle IDs and UDIDs in `member1_local.yaml`, `member2_local.yaml`, and `member3_local.yaml` with your team’s real values (or keep personal copies outside the repo if policy requires).

## Test data (CSV or JSON) — Deliverable 2B

**Required** columns (CSV header or JSON keys on each object):

`test_id`, `app_name`, `section`, `subsection`, `dimension_type`, `sub_dimension`, `item_description`, `image_path`, `expected_output`

Optional template columns (ignored by the runner for execution; **`actual_output`** and **`result`** are written by the framework to the **report** CSV):

`actual_output`, `result`

- Place your **existing** 2B export at `data/testcases.csv`, or pass `--data /path/to/your.csv`.
- JSON: a top-level array, or `{"testcases": [...]}`. See `data/testcases.example.json` (empty list—paste your objects).

## Run batch tests for one app

From the **project root** (the runner adds the repo root to `sys.path`):

```bash
python tests/run_all.py --config config/member1_local.yaml --app FoodZilla
```

Other examples:

```bash
python tests/run_all.py --config config/member2_local.yaml --app SnapCalorie
python tests/run_all.py --config config/member3_local.yaml --app "Lose It!"
```

Optional flags:

- `--data path/to/file.csv` or `.json` — default `data/testcases.csv`
- `--report path/to/results.csv` — default `reports/results.csv`

## Outputs

- **Results CSV** (`reports/results.csv` by default): all input dimensions plus `expected_output`, `actual_output`, `result` (`PASS` / `FAIL` / `ERROR`), `error_message`, `timestamp`.
- **Screenshots** on **FAIL** or **ERROR**: `reports/screenshots/`.
- **Summary line** on stdout and in logs: totals, pass, fail, errors, pass percentage.

## How teammates use different machines

1. Each person maintains their own YAML (copy from `config_template.yaml`) with **their** `udid`, `device.name`, `platform_version`, and signing fields.
2. Point `--config` at that file when running; no code changes required.
3. Swap `app.bundle_id` in YAML when switching which of the three apps is installed on that phone, or keep one YAML per app/device pair.
4. Share the same **2B** testcase file via git; keep secrets and personal device identifiers out of version control if required by policy.

## Project layout

- `framework/` — driver factory, waits, config/data load, **modular** output validation, CSV result logging, stats.
- `apps/<app>/` — `locators.py`, `page.py`, `tests.py` per product.
- `tests/run_all.py` — CLI batch runner filtering by `app_name` (one executable row per app per `test_id`).

## Validation

`framework/validator.py` compares **`expected_output`** to **`actual_output`** using a **chain of rules** (`OutputMatchRule`). Order today:

1. **`PlaceholderExpectedRule`** — FAIL if `expected_output` is blank or still **`__REPLACE_WITH_DELIVERABLE_2B__`** (scaffold constant `DELIVERABLE_2B_PLACEHOLDER`).
2. **`NormalizedExactOutputRule`** — PASS on normalized equality (trim, lowercase, collapse whitespace).
3. **`NormalizedSubstringOutputRule`** — PASS if one normalized string contains the other (minimum length **4** to limit false positives).
4. **`FinalMismatchRule`** — terminal FAIL.

Adjust order or add rules (synonyms, JSON field compare, per-dimension rules) in `default_output_validator()`.
