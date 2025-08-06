#!/usr/bin/env python
"""
Скрипт для запуска тестов Django проекта
"""
import os
import sys
import django
from pathlib import Path

# Добавляем src директорию в sys.path
current_dir = Path(__file__).resolve().parent
src_dir = current_dir / 'src'
sys.path.insert(0, str(src_dir))

# Устанавливаем настройки Django для тестов
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_search.test_settings')

# Инициализируем Django
django.setup()

# Запускаем тесты
if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    # Аргументы для запуска тестов
    argv = ['manage.py', 'test'] + sys.argv[1:]
    execute_from_command_line(argv)