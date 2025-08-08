#!/usr/bin/env python
"""
Скрипт для запуска тестов Django проекта
"""
import os
import sys
from pathlib import Path

import django

# Добавляем src директорию в sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
src_dir = project_root / "src"
tests_dir = project_root / "tests"

sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(project_root))

# Переходим в src директорию
os.chdir(src_dir)

# Устанавливаем настройки Django для тестов
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_search.test_settings")

# Инициализируем Django
django.setup()

# Запускаем тесты
if __name__ == "__main__":
    from django.core.management import execute_from_command_line

    # Аргументы для запуска тестов - указываем путь к тестам
    test_args = ["manage.py", "test", str(tests_dir)]

    # Добавляем дополнительные аргументы из командной строки
    if len(sys.argv) > 1:
        test_args.extend(sys.argv[1:])

    try:
        execute_from_command_line(test_args)
    except Exception as e:
        print(f"Ошибка при запуске тестов: {e}")
        print("Попробуйте запустить тесты напрямую:")
        print("cd src")
        print("python manage.py test ../tests")
        sys.exit(1)
