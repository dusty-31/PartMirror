from enum import Enum


class ExcelColumns(Enum):
    BRAND = "Марка"
    MODEL = "Модель"
    ARTICLE = "Артикул"
    NEW_ARTICLE = "Новый_артикул"
    COMPATIBILITY = "Совместимость"
    BAS_CATEGORY = "Категория_BAS"
    KEYWORDS_RU = "Поисковые_запросы"  # English and russian search queries, comma-separated
    KEYWORDS_UA = "Ключевые_слова_ua"  # English and ukrainian keywords, comma-separated
    BRAND_CYRILLIC = "Марка_кириллицей"
    MODEL_CYRILLIC = "Модель_кириллицей"
    BRAND_CYRILLIC_UA = "Марка_кириллицей_укр"
    MODEL_CYRILLIC_UA = "Модель_кириллицей_укр"
    GROUP_NAME = "Название_группы"
    GROUP_CODE = "Код_группы_BAS"


class CustomExcelColumns(Enum):
    RECORD_TYPE = "Тип_записи"
