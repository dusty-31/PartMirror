from enum import Enum


class ExcelColumns(Enum):
    BRAND = "Марка"
    MODEL = "Модель"
    ARTICLE = "Артикул"
    NEW_ARTICLE = "Новый_артикул"
    COMPATIBILITY = "Совместимость"
    BAS_CATEGORY = "Категория_BAS"


class CustomExcelColumns(Enum):
    RECORD_TYPE = "Тип_записи"

