#!/usr/bin/env python
"""
Скрипт для запуска тестов с правильной конфигурацией
"""
import os
import sys
import subprocess
from pathlib import Path


def setup_environment():
    """Настройка окружения для тестов"""
    # Определяем пути - скрипт находится в scripts/, поднимаемся на уровень выше
    current_dir = Path(__file__).resolve().parent  # scripts/
    project_root = current_dir.parent  # document_search/
    src_dir = project_root / "src"  # document_search/src/

    # Добавляем src в PYTHONPATH
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    # Устанавливаем переменные окружения
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_search.test_settings")
    os.environ.setdefault("PYTHONPATH", str(src_dir))

    # Переходим в корневую директорию проекта
    os.chdir(project_root)


def run_tests(args=None):
    """Запуск тестов с pytest"""
    setup_environment()

    # Базовые аргументы для pytest
    pytest_args = [
        "pytest",
        "--cov=src",
        "--cov-report=html",
        "--cov-report=term-missing",
        "--cov-report=xml",
        "tests/",
    ]

    # Добавляем дополнительные аргументы если они переданы
    if args:
        pytest_args.extend(args)

    print("Запуск тестов с аргументами:", " ".join(pytest_args))

    try:
        result = subprocess.run(pytest_args, check=False)
        return result.returncode
    except FileNotFoundError:
        print("Ошибка: pytest не найден. Убедитесь, что pytest установлен.")
        return 1
    except Exception as e:
        print(f"Ошибка при запуске тестов: {e}")
        return 1


def run_specific_tests():
    """Примеры запуска специфических тестов"""
    print("\nПримеры команд для запуска тестов:")
    print("1. Все тесты с покрытием:")
    print("   python run_tests.py")
    print("\n2. Только тесты моделей:")
    print("   python run_tests.py tests/test_models.py")
    print("\n3. Только тесты алгоритмов:")
    print("   python run_tests.py tests/test_search_algorithms.py")
    print("\n4. Только тесты API:")
    print("   python run_tests.py tests/test_api.py")
    print("\n5. Тесты с маркером 'unit':")
    print("   python run_tests.py -m unit")
    print("\n6. Быстрые тесты (исключая медленные):")
    print("   python run_tests.py -m 'not slow'")
    print("\n7. Verbose режим:")
    print("   python run_tests.py -v")
    print("\n8. Остановка на первой ошибке:")
    print("   python run_tests.py -x")


def main():
    """Основная функция"""
    if len(sys.argv) > 1:
        if sys.argv[1] in ['--help', '-h', 'help']:
            run_specific_tests()
            return 0
        else:
            # Передаем все аргументы pytest
            return run_tests(sys.argv[1:])
    else:
        # Запуск всех тестов с покрытием
        return run_tests()


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)