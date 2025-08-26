import logging
from collections import Counter

from app.settings import AppConfig, setup_logging
from app.core.services import (
    RowTransformer,
    MirrorBuilder,
    ModelBrandResolver,
)
from app.pipelines import DataFrameProcessor
from app.gateways import TripDataProvider, ExcelGateway
from app.adapters.trip_data import ResourceTripDataProvider
from app.adapters.excel import PandasExcelGateway
from app.core.enums import ExcelColumns, CustomExcelColumns
from app.utils import Timer

logger = logging.getLogger(__name__)


def main() -> None:
    cfg = AppConfig()
    setup_logging("DEBUG")

    with Timer("Triplets: load + index"):
        trip_provider: TripDataProvider = ResourceTripDataProvider()
        triplets = trip_provider.load_triplets()
        logger.debug("Triplets types: %s", Counter(type(x).__name__ for x in triplets.raw))
        trip_index = trip_provider.build_index(triplets)

    with Timer("Excel: read input"):
        excel_gateway: ExcelGateway = PandasExcelGateway()
        df = excel_gateway.read(cfg.excel_file, cfg.sheet_name)
        logger.info(f"Input rows: {len(df)}")

    transformer = RowTransformer(trip_index=trip_index, triplets=triplets)
    resolver = ModelBrandResolver(triplets.raw)
    builder = MirrorBuilder(transformer=transformer, trip_index=trip_index, resolver=resolver)
    processor = DataFrameProcessor(builder=builder)

    with Timer("Process: build originals + mirrors"):
        result_df = processor.process(df)
        logger.info(f"Output rows: {len(result_df)}")

    logger.info("\nResults (original + mirrors):")
    cols = [c for c in [
        ExcelColumns.BAS_CATEGORY.value,
        ExcelColumns.MODEL.value,
        ExcelColumns.BRAND.value,
        CustomExcelColumns.RECORD_TYPE.value
    ] if c in result_df.columns]
    preview = result_df[cols] if cols else result_df.head(10)
    logger.debug("\n%s", preview.to_string(index=True))

    with Timer("Excel: write result.xlsx"):
        excel_gateway.write(result_df, "result.xlsx", sheet=cfg.sheet_name)

    logger.info("\nSave result to a file 'result.xlsx'")


if __name__ == "__main__":
    main()
