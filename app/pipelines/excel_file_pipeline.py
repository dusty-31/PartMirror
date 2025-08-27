import logging
import tempfile
from pathlib import Path
from typing import Optional

from app.settings import AppConfig
from app.core.services import (
    RowTransformer,
    MirrorBuilder,
    ModelBrandResolver,
)
from app.pipelines import DataFrameProcessor
from app.gateways import TripDataProvider, ExcelGateway
from app.adapters.trip_data import ResourceTripDataProvider
from app.adapters.excel import PandasExcelGateway


class ExcelFilePipeline:
    """High-level pipeline to read an Excel file, build mirrors, and write output.

    This class mirrors the style of other components in ``app.pipelines`` by
    encapsulating construction and the main processing method.
    """

    def __init__(
        self,
        cfg: Optional[AppConfig] = None,
        excel_gateway: Optional[ExcelGateway] = None,
        trip_provider: Optional[TripDataProvider] = None,
    ) -> None:
        self._cfg = cfg or AppConfig()
        self._excel: ExcelGateway = excel_gateway or PandasExcelGateway()
        self._trip_provider: TripDataProvider = trip_provider or ResourceTripDataProvider()

    def process_file(self, input_path: Path, logger: logging.Logger) -> Path:
        if not input_path.exists():
            raise FileNotFoundError(f"Input file does not exist: {input_path}")
        if input_path.suffix.lower() != ".xlsx":
            raise ValueError("Only .xlsx files are supported")

        # Load trip data and build index
        triplets = self._trip_provider.load_triplets()
        trip_index = self._trip_provider.build_index(triplets)

        # Read Excel input
        logger.info("Reading input Excel: %s", input_path)
        df = self._excel.read(str(input_path), self._cfg.sheet_name)
        logger.info("Input rows: %s", len(df))

        # Build processor
        transformer = RowTransformer(trip_index=trip_index, triplets=triplets)
        resolver = ModelBrandResolver(triplets.raw)
        builder = MirrorBuilder(transformer=transformer, trip_index=trip_index, resolver=resolver)
        processor = DataFrameProcessor(builder=builder)

        # Process rows
        logger.info("Building originals and mirrors…")
        result_df = processor.process(df)
        logger.info("Output rows: %s", len(result_df))

        # Write to a temporary output file
        tmp_dir = Path(tempfile.gettempdir())
        out_name = f"{input_path.stem}_processed.xlsx"
        out_path = tmp_dir / out_name
        logger.info("Writing output Excel: %s", out_path)
        self._excel.write(result_df, str(out_path), sheet=self._cfg.sheet_name)
        return out_path


