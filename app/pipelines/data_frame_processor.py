import pandas as pd
from pandas import DataFrame

from app.core.services.mirror_builder import MirrorBuilder


class DataFrameProcessor:
    def __init__(self, builder: MirrorBuilder) -> None:
        self._builder = builder

    def process(self, df: DataFrame) -> DataFrame:
        all_rows: list[pd.Series] = []
        for _, row in df.iterrows():
            built = self._builder.build_rows_for(row)
            all_rows.extend(built)

        if not all_rows:
            return df.copy()

        result_df = pd.DataFrame(all_rows)
        ordered_cols = [c for c in df.columns if c in result_df.columns] + \
                       [c for c in result_df.columns if c not in df.columns]
        return result_df[ordered_cols]
