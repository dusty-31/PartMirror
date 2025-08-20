import pandas as pd
from pandas import DataFrame
from app.gateways.excel import ExcelGateway


class PandasExcelGateway(ExcelGateway):
    def read(self, path: str, sheet: str) -> DataFrame:
        """Reads an Excel file and returns its content as a DataFrame."""
        return pd.read_excel(path, sheet_name=sheet)

    def write(self, df: DataFrame, path: str, sheet: str) -> None:
        """Writes a DataFrame to an Excel file."""
        df.to_excel(path, index=False)
