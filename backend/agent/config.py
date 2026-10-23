"""Локальные настройки агента без изменения окружения вызывающего backend."""

import os
from pathlib import Path

from dotenv import dotenv_values


# Абсолютный путь позволяет вызывать модуль из любого рабочего каталога.
ENV_FILE = Path(__file__).resolve().with_name(".env")


def read_settings() -> dict[str, str]:
    """Читаем файл при вызове; переменные процесса имеют приоритет, даже пустые.

    interpolate=False сохраняет символы ключа буквально. Секреты не выводятся
    и не записываются в os.environ; backend может передать собственное окружение.
    """
    values = dotenv_values(ENV_FILE, encoding="utf-8-sig", interpolate=False)
    return {**{key: value for key, value in values.items() if value is not None}, **os.environ}
