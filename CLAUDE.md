# CLAUDE.md – Factory Firmware Updater (FFU)

This file describes the codebase for AI assistants working on this project.

## Project Overview

Factory Firmware Updater (FFU) is a **desktop GUI application** that updates Oura rings from factory firmware to a Bentley 0.2.12 customer image via Bluetooth Low Energy (BLE). It is built with **Python + PyWebView** (Python backend, HTML/CSS/JS frontend) and requires a **BleuIO Pro USB dongle** for BLE connectivity.

## Repository Structure

```
ffu/
├── app.py                    # Main application – PyWebView window + DFuApi class
├── main.py                   # Placeholder entry point (not used in production)
├── setup_macos.py            # py2app build script for macOS .app bundle
├── pyproject.toml            # Project metadata and dependencies
├── requirements.txt          # Direct pip-installable dependencies
├── uv.lock                   # UV package manager lockfile (do not edit manually)
├── config.json               # Advanced DFU settings (overrides in-code defaults)
├── .python-version           # Pins Python to 3.12
├── bentley_0_2_12/
│   └── bentley-fw.signed.confirmed.bin   # Bundled factory firmware binary
├── ui/
│   ├── index.html            # Single-page frontend (embedded JS, dark theme)
│   └── ui.png                # Screenshot for README
├── .github/
│   └── workflows/
│       └── build-macos.yml   # Manual GitHub Actions workflow to build .app
├── README.md                 # User-facing setup and usage guide
└── DFU Procedure Document v1.0.txt  # Technical reference for DFU parameters
```

## Architecture

### Python backend (`app.py`)

| Component | Purpose |
|-----------|---------|
| `DfuApi` class | Exposed to the WebView via `js_api`; all public methods are callable from JavaScript |
| `DfuApi.get_defaults()` | Returns form defaults and advanced settings loaded from `config.json` |
| `DfuApi.get_progress()` | Thread-safe progress snapshot polled by the UI every 250 ms |
| `DfuApi.start_dfu()` | Runs the DFU procedure in a background thread; blocks until complete |
| `load_config()` | Merges `config.json` over `DEFAULT_ADVANCED`; silently falls back to defaults on error |
| `resolve_firmware_path()` | Resolves relative firmware paths against the app directory |

**Threading model:** `start_dfu()` spawns a `threading.Thread`. Progress is protected by `threading.Lock()`. The calling thread blocks via `thread.join()`, so `start_dfu()` is synchronous from JavaScript's perspective even though DFU runs off the main thread.

**Optional dependency:** `PlatformController` is imported with a `try/except`. If the package is not installed the app launches but `start_dfu()` raises a descriptive `RuntimeError`.

### Frontend (`ui/index.html`)

A self-contained SPA with no build step and no external dependencies.

- Listens for `pywebviewready`, then calls `pywebview.api.get_defaults()` to pre-fill the form.
- On "Update" click, calls `pywebview.api.start_dfu(...)` and starts a 250 ms `setInterval` that calls `pywebview.api.get_progress()`.
- Status bar uses CSS classes `success` (green) / `error` (red).
- Window size: 520 × 740 px.

### Configuration (`config.json`)

Loaded at runtime (not baked in at build time). Fields:

| Key | Default | Description |
|-----|---------|-------------|
| `app_id` | `1` | Application ID (always 1 for factory firmware) |
| `start_address` | `0` | Firmware start address |
| `block_size` | `512` | Transfer block size in bytes |
| `ring_type` | `8` | Device type identifier (8 = Bentley) |
| `force_flags` | `0` | Force-update flags |
| `reboot_wait` | `10` | Seconds to wait after reboot |

If `config.json` is missing or malformed, in-code defaults are used silently.

## Development Workflow

### Prerequisites

- Python 3.12 (enforced by `.python-version`)
- [uv](https://docs.astral.sh/uv/) package manager (recommended)
- BleuIO Pro USB dongle (required to actually run DFU)
- The `platform_controller` / `pyring` package that provides `PlatformController` and `DfuManager` (internal Oura package, not in `requirements.txt`)

### Install and run

```bash
# With uv (recommended)
uv venv
uv pip install -r requirements.txt
uv run python app.py

# Without uv
pip install -r requirements.txt
python app.py
```

### Dependency management

This project uses **uv** and the lockfile `uv.lock`.

- Add a new dependency: edit `pyproject.toml` then run `uv sync` (updates `uv.lock`).
- Install from lockfile: `uv sync`.
- Never edit `uv.lock` manually.

The `oura_message_client` dependency is sourced directly from a private GitHub repo:
```
oura_message_client @ git+https://github.com/jouzen/celebrimbor.git@main#subdirectory=oura_message_client
```
Access requires appropriate GitHub credentials. In CI, set `UV_GIT_OAUTH_TOKEN` to a PAT.

### Building for macOS

**Via GitHub Actions (preferred):**
1. Go to **Actions → Build macOS app → Run workflow**.
2. Download the `Factory-Firmware-Updater-macOS` artifact (`.app` bundle).

**Locally on a Mac:**
```bash
pip install py2app
python setup_macos.py py2app
# Output: dist/app.app (or similar)
```

`setup_macos.py` bundles:
- `ui/` → `Contents/Resources/ui/`
- `bentley_0_2_12/*.bin` → `Contents/Resources/bentley_0_2_12/`
- `config.json` → `Contents/Resources/`

## Key Conventions

### Python style
- **Python 3.12+** – use modern stdlib features (`pathlib.Path`, `match`, etc.).
- **`pathlib.Path`** for all file system operations; no raw string path concatenation.
- **Type hints** on function signatures.
- **Docstrings** for public functions and classes.
- `black` is present in the lockfile – format code with `black .` before committing.
- No linting config is currently enforced (no `.flake8`, `ruff.toml`, etc.), but keep code clean.

### Frontend style
- The HTML/JS in `ui/index.html` has **no build step** and **no npm**. Keep it that way unless there is a strong reason to add tooling.
- All JavaScript is vanilla (ES5-compatible where feasible; `var`, `function` declarations, no modules).
- CSS variables are not used; the color palette is inline. Accent colour: `#3b82f6`. Background: `#1a1a1e`.
- Do not add external CDN links – the app must work offline.

### Configuration changes
- User-facing DFU parameters go in `config.json`, not hardcoded in `app.py`.
- In-code `DEFAULT_ADVANCED` dict in `app.py` must stay in sync with the keys documented in this file.

## Testing

There are **no automated tests** in this repository. The project is tested manually with physical hardware (ring + dongle). If tests are added, use **pytest** (already present in `uv.lock`).

## CI/CD

A single workflow `.github/workflows/build-macos.yml`:
- Trigger: **manual** (`workflow_dispatch`) only.
- Runs on `macos-latest`.
- Steps: checkout → install uv → install Python 3.12 → `uv sync` → install py2app → `python setup_macos.py py2app` → upload artifact.
- No automated test or lint step currently.

## Hardware Requirements

| Hardware | Notes |
|----------|-------|
| BleuIO Pro USB dongle | Must be Pro model; standard BleuIO will not work |
| Oura ring (Bentley platform) | Ring must be in factory firmware state |

The ring's BLE name is discovered with `pyring-ORT`. The default prefix is `oura_`.

## Common Pitfalls

- **`PlatformController` not found:** The package providing it (`platform_controller` or `pyring`) is an internal Oura package not listed in `requirements.txt`. Install it separately.
- **Relative firmware paths:** `resolve_firmware_path()` resolves them relative to the directory containing `app.py`, not the current working directory. This matters when building a `.app` bundle.
- **`config.json` not found:** The app silently uses defaults. Check `APP_DIR / "config.json"` if settings are not being applied.
- **Dongle position:** Place the BleuIO Pro dongle physically close to the ring for reliable BLE connectivity.
- **`main.py` is a placeholder:** The real entry point is `app.py` → `main()`. Do not route new logic through `main.py`.
