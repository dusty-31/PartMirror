from typing import Protocol
from pandas import DataFrame


class ExcelGateway(Protocol):
    def read(self, path: str, sheet: str) -> DataFrame:
        """Reads an Excel file and returns its content as a DataFrame."""
        ...

    def write(self, df: DataFrame, path: str, sheet: str) -> None:
        """Writes a DataFrame to an Excel file."""
        ...
