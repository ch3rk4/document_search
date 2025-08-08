"""
Конфигурация для тестов pytest с Django
"""
import os
import sys
from pathlib import Path

import django


def pytest_configure():
    """Конфигурация Django для pytest"""
    # Добавляем src директорию в PYTHONPATH
    current_dir = Path(__file__).resolve().parent  # tests/
    project_root = current_dir.parent  # document_search/
    src_dir = project_root / "src"  # document_search/src/

    sys.path.insert(0, str(src_dir))
    sys.path.insert(0, str(project_root))

    # Меняем рабочую директорию на src
    os.chdir(src_dir)

    # Настраиваем Django с тестовыми настройками
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_search.test_settings")

    # Инициализируем Django
    django.setup()
