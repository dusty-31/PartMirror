## PartMirror

Minimal, cross-platform Excel processing app with PySide6 GUI. The GUI runs your existing pipeline to build product
mirrors and save the result as an `.xlsx`.

Mirrors - a feature that creates duplicates of products with changed categories and other attributes for the BAS system.

### Requirements

- Python 3.12+
- pip (and optionally a virtualenv)

Install deps:

```bash
  pip install -r requirements.txt
```

Key runtime deps: PySide6, pandas, openpyxl (via requirements.txt).

### Run the GUI

```bash
  python -m gui
```

Shortcuts (macOS/Windows/Linux):

- Open: ⌘O / Ctrl+O
- Process: ⌘R / Ctrl+R
- Cancel: ⌘. / Ctrl+.
- Quit: ⌘Q / Ctrl+Q
- Toggle logs sidebar: F2

### How the GUI integrates your pipeline

The GUI calls `app.pipelines.ExcelFilePipeline.process_file(input_path, logger)` in a background thread. The pipeline:

1) Loads triplets and builds an index;
2) Reads the selected Excel sheet;
3) Builds originals + mirrors;
4) Writes a temporary output `.xlsx` and returns its path.

On success, the GUI prompts for “Save As…”. On error, it logs the exception and returns to idle.

### Configuration

Basic GUI identifiers are in `gui/config.py`:

```python
APP_ORG = "Name of Your Company"
APP_NAME = "Name of Your App"
```

QSettings uses these values to persist UI state (e.g., sidebar width, last directory).

### Build a desktop app (PyInstaller)

Example command:

```bash
    # Use the same name as APP_NAME in gui/config.py for consistency
    pyinstaller --windowed --name "PartMirror" \
    --icon=gui/icon.icns \
    --add-data "app/adapters/trip_data/resources:app/adapters/trip_data/resources" \
    gui/main.py
```

We need `--add-data` to load all json files with data for creating mirrors.

Resulting bundle(s) will appear under `dist/`.

