from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    excel_file: str = "data.xlsx"
    sheet_name: str = "Sheet1"
    cars_triplets_path: str = "cars.json"
    compatibility_map_path: str = "cars_eng.json"


BRAND_MODEL_COLUMNS: tuple[tuple[str, str], ...] = (
    ("Наименование_WestLine", "ru"),
    ("Наименование_WestLine_ua", "ua"),
    ("Наименование_Automotive", "ru"),
    ("Наименование_Automotive_ua", "ua"),
    ("Описание_WestLine", "ru"),
    ("Описание_WestLine_ua", "ua"),
    ("Описание_Automotive", "ru"),
    ("Описание_Automotive_ua", "ua"),
)

MIRROR_CLEAR_COLUMNS: tuple[str, ...] = (
    "Код_BAS",
    "Цена_продажи",
    "Поставщик",
    "Производитель",
    "Страна_производитель",
    "Идентификатор_подраздела",
    "Состояние",
    "Срок_гарантии",
    "Тип_запчасти",
    "Код_запчасти",
    "Код_запчасти_поставщика",
    "Код_закупки",
    "Размещение_на_складе",
    "Мин_уровень_запаса",
    "Макс_уровень_запаса",
    "Вес",
    "Марка_кириллицей",
    "Модель_кириллицей",
    "Марка_кириллицей_укр",
    "Модель_кириллицей_укр",
    "Совместимость",
    "Уточнение",
    "Сторона_установки",
    "Количество_контактов",
    "Тип_кузова",
    "Комплектация",
    "Тип_установки",
    "Материал",
    "Размер",
    "Цвет",
)
