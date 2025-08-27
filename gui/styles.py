from PySide6 import QtGui


SPACING_SMALL = 8
SPACING_MEDIUM = 12
SPACING_LARGE = 16

MARGINS = (12, 12, 12, 12)


def system_mono_font() -> QtGui.QFont:
    return QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.SystemFont.FixedFont)


BASE_STYLESHEET = """
QFrame#DropArea {
    border: 2px dashed #b5b5b5;
    border-radius: 12px;
    background: #fafafa;
}
QFrame#DropArea[hover=true] {
    border-color: #0a84ff; /* mac accent */
    background: #f0f8ff;
}
QPushButton[primary="true"] {
    font-weight: 600;
}
"""


