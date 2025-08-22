import time
from collections import Counter

from app.config import AppConfig
from app.core.services.row_transformer import RowTransformer
from app.core.services.mirror_builder import MirrorBuilder
from app.core.services.model_brand_resolver import ModelBrandResolver
from app.pipelines.data_frame_processor import DataFrameProcessor

from app.gateways.trip_data_prodiver import TripDataProvider
from app.gateways.excel import ExcelGateway
from app.adapters.trip_data.resource_trip_data_provider import ResourceTripDataProvider
from app.adapters.excel.pandas_excel_gateway import PandasExcelGateway


class Timer:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.t0 = time.perf_counter()
        print(f"[START] {self.label}")
        return self

    def __exit__(self, exc_type, exc, tb):
        print(f"[DONE ] {self.label} — {time.perf_counter() - self.t0:.2f}s")


def main() -> None:
    cfg = AppConfig()

    with Timer("Triplets: load + index"):
        trip_provider: TripDataProvider = ResourceTripDataProvider()  # читає app.adapters.tripdata.resources.cars
        triplets = trip_provider.load_triplets()
        print("triplets types:", Counter(type(x).__name__ for x in triplets.raw))
        trip_index = trip_provider.build_index(triplets)

    with Timer("Excel: read input"):
        excel_gateway: ExcelGateway = PandasExcelGateway()
        df = excel_gateway.read(cfg.excel_file, cfg.sheet_name)
        print(f"Input rows: {len(df)}")

    transformer = RowTransformer(trip_index=trip_index, triplets=triplets)
    resolver = ModelBrandResolver(triplets.raw)
    builder = MirrorBuilder(transformer=transformer, trip_index=trip_index, resolver=resolver)
    processor = DataFrameProcessor(builder=builder)

    with Timer("Process: build originals + mirrors"):
        result_df = processor.process(df)
        print(f"Output rows: {len(result_df)}")

    print("\nРезультат (оригінал + копії):")
    cols = [c for c in ["Название_позиции_BAS", "Марка", "Модель", "Тип_записи"] if c in result_df.columns]
    print(result_df[cols] if cols else result_df.head(10))

    with Timer("Excel: write result.xlsx"):
        excel_gateway.write(result_df, "result.xlsx", sheet=cfg.sheet_name)

    print("\nРезультат збережено у файл 'result.xlsx'")


if __name__ == "__main__":
    main()
