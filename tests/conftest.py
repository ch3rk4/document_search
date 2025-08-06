"""
Конфигурация для тестов pytest с Django
"""
import os
import sys
import django
from pathlib import Path

def pytest_configure():
    """Конфигурация Django для pytest"""
    # Добавляем src директорию в PYTHONPATH
    current_dir = Path(__file__).resolve().parent  # tests/
    src_dir = current_dir.parent / 'src'  # document_search/src/
    sys.path.insert(0, str(src_dir))

    # Меняем рабочую директорию на src
    os.chdir(src_dir)

    # Настраиваем Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_search.settings')

    # Инициализируем Django
    django.setup()