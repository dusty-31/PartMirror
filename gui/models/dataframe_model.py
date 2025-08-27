from typing import Any, Optional

import pandas as pd
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex


class DataFrameModel(QAbstractTableModel):
    """Qt table model backed by a pandas DataFrame (read-only)."""

    def __init__(self, df: Optional[pd.DataFrame] = None) -> None:
        super().__init__()
        self._df = df if df is not None else pd.DataFrame()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self.beginResetModel()
        self._df = df
        self.endResetModel()

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else int(len(self._df))

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # type: ignore[override]
        return 0 if parent.isValid() else int(len(self._df.columns))

    def data(self, index: QModelIndex, role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:  # type: ignore[override]
        if not index.isValid() or role not in (
                int(Qt.ItemDataRole.DisplayRole),
                int(Qt.ItemDataRole.EditRole),
        ):
            return None
        value = self._df.iat[index.row(), index.column()]
        return "" if pd.isna(value) else str(value)

    def headerData(self, section: int, orientation: Qt.Orientation,
                   role: int = int(Qt.ItemDataRole.DisplayRole)) -> Any:  # type: ignore[override]
        if role != int(Qt.ItemDataRole.DisplayRole):
            return None
        if orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self._df.columns):
                return str(self._df.columns[section])
            return ""
        return str(section + 1)
