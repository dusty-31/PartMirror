from app.config import AppConfig
from app.core.services.row_transformer import RowTransformer
from app.core.services.mirror_builder import MirrorBuilder
from app.pipelines.data_frame_processor import DataFrameProcessor

from app.gateways.trip_data_prodiver import TripDataProvider
from app.gateways.compatibility_provider import CompatibilityProvider
from app.gateways.excel import ExcelGateway

from app.adapters.trip_data.resource_trip_data_provider import ResourceTripDataProvider
from app.adapters.trip_data.finder_trip_data_provider import FinderTripDataProvider
from app.adapters.compatibility.json_compatibility_provider import JsonCompatibilityProvider
from app.adapters.excel.pandas_excel_gateway import PandasExcelGateway


def main() -> None:
    cfg = AppConfig()

    trip_provider: TripDataProvider
    if cfg.use_resource_triplets:
        trip_provider = ResourceTripDataProvider()
        triplets = trip_provider.load_triplets()

        trip_index = trip_provider.build_index(triplets)
    else:
        trip_provider = FinderTripDataProvider(cfg.cars_triplets_path)
        triplets = trip_provider.load_triplets()
        trip_index = trip_provider.build_index(triplets)

    compat_provider: CompatibilityProvider = JsonCompatibilityProvider(cfg.compatibility_map_path)
    excel_gateway: ExcelGateway = PandasExcelGateway()

    transformer = RowTransformer(trip_index=trip_index, triplets=triplets)
    builder = MirrorBuilder(transformer=transformer, trip_index=trip_index)
    processor = DataFrameProcessor(builder=builder)

    df = excel_gateway.read(cfg.excel_file, cfg.sheet_name)
    compatibility_map = compat_provider.load()

    result_df = processor.process(df, compatibility_map)

    print("Результат (оригінал + копії для кожного товару):")
    cols_to_show = [c for c in ["Название_позиции_BAS", "Марка", "Модель", "Тип_записи"] if c in result_df.columns]
    if cols_to_show:
        print(result_df[cols_to_show])
    else:
        print(result_df.head(10))

    excel_gateway.write(result_df, "result.xlsx")
    print("\nРезультат збережено у файл 'result.xlsx'")


if __name__ == "__main__":
    main()
