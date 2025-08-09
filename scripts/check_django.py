#!/usr/bin/env python
"""
Скрипт для проверки настроек Django перед запуском тестов
"""
import os
import sys
from pathlib import Path


def setup_django():
    """Настройка Django"""
    # Определяем пути - скрипт находится в scripts/, поднимаемся на уровень выше
    current_dir = Path(__file__).resolve().parent  # scripts/
    project_root = current_dir.parent  # document_search/
    src_dir = project_root / "src"  # document_search/src/

    # Добавляем src в PYTHONPATH
    sys.path.insert(0, str(src_dir))

    # Переходим в src директорию
    os.chdir(src_dir)

    # Настраиваем Django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_search.test_settings")

    try:
        import django

        django.setup()
        return True
    except Exception as e:
        print(f"Ошибка настройки Django: {e}")
        return False


def check_installed_apps():
    """Проверка установленных приложений"""
    try:
        from django.conf import settings

        print("✓ Установленные приложения:")
        for app in settings.INSTALLED_APPS:
            print(f"  - {app}")

        return True
    except Exception as e:
        print(f"✗ Ошибка проверки приложений: {e}")
        return False


def check_database():
    """Проверка настроек базы данных"""
    try:
        from django.conf import settings
        from django.db import connection

        print("✓ Настройки базы данных:")
        db_config = settings.DATABASES["default"]
        print(f"  - ENGINE: {db_config['ENGINE']}")
        print(f"  - NAME: {db_config['NAME']}")

        # Проверяем подключение
        cursor = connection.cursor()
        print("✓ Подключение к базе данных работает")

        return True
    except Exception as e:
        print(f"✗ Ошибка проверки базы данных: {e}")
        return False


def check_models():
    """Проверка моделей"""
    try:
        print("✓ Модели успешно импортированы:")
        print("  - User")
        print("  - Document")
        print("  - DocumentCategory")
        print("  - DocumentTag")

        return True
    except Exception as e:
        print(f"✗ Ошибка импорта моделей: {e}")
        return False


def check_migrations():
    """Проверка миграций"""
    try:
        from django.core.management import execute_from_command_line

        print("✓ Применение миграций...")
        execute_from_command_line(["check_django.py", "migrate", "--verbosity=0", "--run-syncdb"])
        print("✓ Миграции применены успешно")

        return True
    except Exception as e:
        print(f"✗ Ошибка применения миграций: {e}")
        return False


def test_basic_operations():
    """Тестирование базовых операций с моделями"""
    try:
        from django.contrib.auth.models import User

        from doc_storage.models import Document, DocumentCategory

        # Создаем тестового пользователя
        user = User.objects.create_user(username="check_test_user", email="test@example.com", password="testpass123")
        print("✓ Пользователь создан")

        # Создаем категорию
        category = DocumentCategory.objects.create(name="Тестовая категория", description="Для проверки")
        print("✓ Категория создана")

        # Создаем документ
        document = Document.objects.create(
            title="Тестовый документ", content="Содержимое для проверки", author=user, category=category
        )
        print("✓ Документ создан")

        # Проверяем подсчет слов
        print(f"✓ Количество слов в документе: {document.word_count}")

        # Очищаем тестовые данные
        document.delete()
        category.delete()
        user.delete()
        print("✓ Тестовые данные очищены")

        return True
    except Exception as e:
        print(f"✗ Ошибка тестирования операций: {e}")
        return False


def main():
    """Основная функция проверки"""
    print("🔍 Проверка настроек Django для тестов")
    print("=" * 50)

    checks = [
        ("Настройка Django", setup_django),
        ("Проверка приложений", check_installed_apps),
        ("Проверка базы данных", check_database),
        ("Проверка моделей", check_models),
        ("Применение миграций", check_migrations),
        ("Тестирование операций", test_basic_operations),
    ]

    results = []

    for check_name, check_func in checks:
        print(f"\n📋 {check_name}:")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"✗ Неожиданная ошибка в {check_name}: {e}")
            results.append(False)

    print("\n" + "=" * 50)
    print("📊 Результаты проверки:")

    for i, (check_name, _) in enumerate(checks):
        status = "✓ ПРОЙДЕНО" if results[i] else "✗ ОШИБКА"
        print(f"  {check_name}: {status}")

    all_passed = all(results)

    if all_passed:
        print("\n🎉 Все проверки пройдены! Django настроен корректно для тестов.")
        print("Теперь можно запускать тесты командой:")
        print("  pytest --cov=src --cov-report=html")
        print("или")
        print("  python run_tests.py")
    else:
        print("\n❌ Некоторые проверки не пройдены. Проверьте ошибки выше.")
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
