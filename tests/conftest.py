"""
Конфигурация для тестов pytest с Django
"""
import os
import sys
from pathlib import Path

import django
import pytest


def pytest_configure(config):
    """Конфигурация Django для pytest"""
    # Определяем пути
    current_dir = Path(__file__).resolve().parent  # tests/
    project_root = current_dir.parent  # document_search/
    src_dir = project_root / "src"  # document_search/src/

    # Добавляем src директорию в PYTHONPATH
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))

    # Устанавливаем переменные окружения
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_search.test_settings")

    # Инициализируем Django
    if not django.conf.settings.configured:
        django.setup()


@pytest.fixture(scope="session")
def django_db_setup():
    """Настройка базы данных для тестов"""
    from django.core.management import execute_from_command_line

    # Создаем таблицы в тестовой БД
    execute_from_command_line(['manage.py', 'migrate', '--verbosity=0', '--run-syncdb'])


@pytest.fixture
def authenticated_user():
    """Фикстура для создания аутентифицированного пользователя"""
    from django.contrib.auth.models import User

    user = User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )
    return user


@pytest.fixture
def document_category():
    """Фикстура для создания категории документа"""
    from doc_storage.models import DocumentCategory

    category = DocumentCategory.objects.create(
        name="Тестовая категория",
        description="Категория для тестов"
    )
    return category


@pytest.fixture
def sample_document(authenticated_user, document_category):
    """Фикстура для создания тестового документа"""
    from doc_storage.models import Document

    document = Document.objects.create(
        title="Тестовый документ",
        content="Это тестовый документ с python программированием и алгоритмами поиска",
        author=authenticated_user,
        category=document_category
    )
    return document


@pytest.fixture
def api_client():
    """Фикстура для API клиента"""
    from rest_framework.test import APIClient
    return APIClient()


# Marks для pytest
pytest_plugins = []

# Отключаем некоторые предупреждения для чистого вывода тестов
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)