"""GUI package for the Excel processing application.

Install dependencies:
    pip install PySide6

Run the app:
    python -m gui

Optional (create a macOS app bundle with PyInstaller):
pyinstaller --windowed --name "WLP - PartMirror" \
--icon=gui/icon.icns \
--add-data "app/adapters/trip_data/resources:app/adapters/trip_data/resources" \
gui/main.py
"""

__all__ = [
    "__version__",
]

__version__ = "0.1.0"
