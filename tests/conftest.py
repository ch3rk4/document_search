"""
Конфигурация и фикстуры для тестов
"""
import os
import sys
import tempfile


# Добавляем src в Python path
src_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
sys.path.insert(0, src_path)

# Настройка Django до импорта моделей
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "document_search.test_settings")

import django

django.setup()

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client


@pytest.fixture(scope="session")
def django_db_setup(django_db_blocker):
    """Настройка тестовой базы данных — применяем миграции с разблокировкой доступа"""
    from django.core.management import call_command

    with django_db_blocker.unblock():
        call_command("migrate", verbosity=0, interactive=False)


@pytest.fixture
def client():
    """Фикстура для тестового клиента Django"""
    return Client()


@pytest.fixture
def admin_user(db):
    """Создание администратора для тестов"""
    from django.contrib.auth.models import User

    return User.objects.create_superuser(
        username="admin_test", email="admin@test.com", password="testpass123", first_name="Test", last_name="Admin"
    )


@pytest.fixture
def regular_user(db):
    """Создание обычного пользователя для тестов"""
    from django.contrib.auth.models import User

    return User.objects.create_user(
        username="user_test", email="user@test.com", password="testpass123", first_name="Test", last_name="User"
    )


@pytest.fixture
def anonymous_user(db):
    """Получение анонимного пользователя"""
    from django.contrib.auth.models import User

    user, created = User.objects.get_or_create(
        username="anonymous",
        defaults={
            "email": "anonymous@example.com",
            "first_name": "Анонимный",
            "last_name": "Пользователь",
        },
    )
    user.set_unusable_password()
    user.save()
    return user


@pytest.fixture
def test_category(db):
    """Создание тестовой категории"""
    from doc_storage.models import DocumentCategory

    return DocumentCategory.objects.create(name="Тестовая категория", description="Категория для тестирования")


@pytest.fixture
def test_tag(db):
    """Создание тестового тега"""
    from doc_storage.models import DocumentTag

    return DocumentTag.objects.create(name="тест", color="#ff0000")


@pytest.fixture
def test_document(db, regular_user, test_category):
    """Создание тестового документа"""
    from doc_storage.models import Document

    return Document.objects.create(
        title="Тестовый документ",
        content="Это тестовый документ с различными словами для проверки поиска. "
        "В документе есть программирование, алгоритмы, python, javascript и другие термины.",
        author=regular_user,
        category=test_category,
        is_active=True,
    )


@pytest.fixture
def test_document_with_tags(db, test_document, test_tag):
    """Тестовый документ с тегами"""
    from doc_storage.models import DocumentTagRelation

    DocumentTagRelation.objects.create(document=test_document, tag=test_tag)
    return test_document


@pytest.fixture
def multiple_documents(db, regular_user, admin_user, test_category):
    """Создание нескольких тестовых документов"""
    from doc_storage.models import Document

    documents = []

    # Документ 1
    doc1 = Document.objects.create(
        title="Python программирование",
        content="Python это мощный язык программирования. Он используется для разработки веб-приложений, "
        "анализа данных и машинного обучения. Python имеет простой синтаксис.",
        author=regular_user,
        category=test_category,
    )
    documents.append(doc1)

    # Документ 2
    doc2 = Document.objects.create(
        title="JavaScript разработка",
        content="JavaScript это язык программирования для веб-разработки. "
        "Он работает в браузере и позволяет создавать интерактивные веб-страницы.",
        author=admin_user,
        category=test_category,
    )
    documents.append(doc2)

    # Документ 3
    doc3 = Document.objects.create(
        title="Алгоритмы и структуры данных",
        content="Алгоритмы это последовательность действий для решения задач. "
        "Структуры данных помогают эффективно хранить и обрабатывать информацию.",
        author=regular_user,
        category=test_category,
    )
    documents.append(doc3)

    return documents


@pytest.fixture
def sample_text_file():
    """Создание тестового текстового файла"""
    content = "Это тестовый текстовый файл.\nОн содержит несколько строк текста.\nДля тестирования загрузки файлов."
    return SimpleUploadedFile("test_document.txt", content.encode("utf-8"), content_type="text/plain")


@pytest.fixture
def sample_docx_file():
    """Создание тестового DOCX файла (имитация)"""
    # Создаем простой файл, который будет имитировать DOCX
    content = b"PK\x03\x04\x14\x00\x06\x00"  # Заголовок ZIP файла
    return SimpleUploadedFile(
        "test_document.docx",
        content,
        content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@pytest.fixture
def large_file():
    """Создание файла большого размера для тестирования ограничений"""
    content = b"x" * (60 * 1024 * 1024)  # 60MB файл
    return SimpleUploadedFile("large_file.txt", content, content_type="text/plain")


@pytest.fixture
def unsupported_file():
    """Создание файла неподдерживаемого формата"""
    content = b"\x89PNG\r\n\x1a\n"  # PNG заголовок
    return SimpleUploadedFile("test_image.png", content, content_type="image/png")


@pytest.fixture
def authenticated_client(client, regular_user):
    """Аутентифицированный клиент"""
    client.force_login(regular_user)
    return client


@pytest.fixture
def admin_client(client, admin_user):
    """Клиент с правами администратора"""
    client.force_login(admin_user)
    return client


@pytest.fixture
def api_client():
    """Клиент для API тестов"""
    from rest_framework.test import APIClient

    return APIClient()


@pytest.fixture
def authenticated_api_client(api_client, regular_user):
    """Аутентифицированный API клиент"""
    api_client.force_authenticate(user=regular_user)
    return api_client


@pytest.fixture
def admin_api_client(api_client, admin_user):
    """API клиент с правами администратора"""
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def temp_media_root(settings):
    """Временная директория для медиа файлов в тестах"""
    with tempfile.TemporaryDirectory() as temp_dir:
        settings.MEDIA_ROOT = temp_dir
        yield temp_dir


@pytest.fixture
def search_test_data(db, regular_user, test_category):
    """Данные для тестирования поиска"""
    # Создаем документы с различным содержимым для тестирования поиска
    from doc_storage.models import Document

    doc1 = Document.objects.create(
        title="Программирование на Python",
        content="Python это высокоуровневый язык программирования. "
        "Программирование на Python простое и эффективное. "
        "Программист может легко изучить Python.",
        author=regular_user,
        category=test_category,
    )

    doc2 = Document.objects.create(
        title="Веб-разработка",
        content="Веб-разработка включает frontend и backend разработку. "
        "Разработчик должен знать HTML, CSS и JavaScript. "
        "Современная разработка использует фреймворки.",
        author=regular_user,
        category=test_category,
    )

    return [doc1, doc2]


import pytest


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(db):
    """Автоматически включает доступ к базе данных для всех тестов."""
    pass
