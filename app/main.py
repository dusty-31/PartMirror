import logging
import time
from collections import Counter
from typing import Type, Optional
from types import TracebackType

from app.settings import AppConfig, setup_logging
from app.core.services.row_transformer import RowTransformer
from app.core.services.mirror_builder import MirrorBuilder
from app.core.services.model_brand_resolver import ModelBrandResolver
from app.pipelines.data_frame_processor import DataFrameProcessor

from app.gateways.trip_data_prodiver import TripDataProvider
from app.gateways.excel import ExcelGateway
from app.adapters.trip_data.resource_trip_data_provider import ResourceTripDataProvider
from app.adapters.excel.pandas_excel_gateway import PandasExcelGateway

from app.core.enums import ExcelColumns, CustomExcelColumns

logger = logging.getLogger(__name__)


class Timer:
    def __init__(self, label: str) -> None:
        self.label = label
        self.start_time: float = 0.0

    def __enter__(self) -> "Timer":
        self.start_time = time.perf_counter()
        logger.info("[START] %s", self.label)
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc_value: Optional[BaseException],
            traceback: Optional[TracebackType],
    ) -> None:
        elapsed = time.perf_counter() - self.start_time
        if exc_type:
            logger.error(f"[FAIL ] {self.label} — {elapsed:.2f}s")
        else:
            logger.info(f"[DONE ] {self.label} — {time.perf_counter() - self.start_time:.2f}s")


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
