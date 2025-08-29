from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    excel_file: str = "../test.xlsx"
    sheet_name: str = "TDSheet"

    # True, if you want to use resources json files
    use_resource_triplets: bool = True
