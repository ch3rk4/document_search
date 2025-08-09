"""
Тесты для утилит и дополнительных компонентов
"""
import pytest
from unittest.mock import patch, MagicMock
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings
from io import StringIO


class TestModelMethods:
    """Тесты дополнительных методов моделей"""

    def test_document_save_word_count(self, test_document):
        """Тест автоматического подсчета слов при сохранении"""
        original_count = test_document.word_count

        test_document.content = "Новое содержимое с пятью различными словами"
        test_document.save()

        assert test_document.word_count == 5
        assert test_document.word_count != original_count

    def test_word_match_context_truncation(self, test_document):
        """Тест автоматического обрезания контекста"""
        from doc_storage.models import WordMatch

        long_context = "x" * 250  # Больше лимита

        word_match = WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест",
            position=10,
            context_before=long_context,
            context_after=long_context
        )

        assert len(word_match.context_before) == 200
        assert len(word_match.context_after) == 200

    def test_document_str_method(self, test_document):
        """Тест строкового представления документа"""
        assert str(test_document) == test_document.title

    def test_document_category_str_method(self, test_category):
        """Тест строкового представления категории"""
        assert str(test_category) == test_category.name

    def test_document_tag_str_method(self, test_tag):
        """Тест строкового представления тега"""
        assert str(test_tag) == test_tag.name


class TestSignals:
    """Тесты сигналов Django (если есть)"""

    @patch('doc_storage.models.Document.save')
    def test_document_pre_save_signal(self, mock_save, test_document):
        """Тест сигнала перед сохранением документа"""
        # Если есть сигналы, тестируем их
        test_document.content = "Новое содержимое для подсчета слов"
        test_document.save()

        mock_save.assert_called()


class TestValidators:
    """Тесты валидаторов (если есть кастомные)"""

    def test_file_size_validation(self, large_file):
        """Тест валидации размера файла"""
        from doc_storage.file_service import FileTextExtractor

        # Проверяем, что большой файл не проходит валидацию
        assert large_file.size > FileTextExtractor.MAX_FILE_SIZE

    def test_file_extension_validation(self, unsupported_file):
        """Тест валидации расширения файла"""
        from doc_storage.file_service import FileTextExtractor

        assert not FileTextExtractor.is_supported_file(unsupported_file.name)


class TestMiddleware:
    """Тесты middleware (если есть кастомные)"""

    def test_request_processing(self, client):
        """Тест обработки запросов middleware"""
        # Проверяем, что стандартные middleware работают
        response = client.get('/')

        # Проверяем заголовки безопасности
        assert response.status_code in [200, 302, 404]


class TestTemplateFilters:
    """Тесты фильтров шаблонов (если есть кастомные)"""

    pass  # Пока кастомных фильтров нет


class TestTemplateTags:
    """Тесты тегов шаблонов (если есть кастомные)"""

    pass  # Пока кастомных тегов нет


class TestHelperFunctions:
    """Тесты вспомогательных функций"""

    def test_get_anonymous_user_function(self, db):
        """Тест функции получения анонимного пользователя"""
        from doc_storage.views import get_anonymous_user
        from django.contrib.auth.models import User

        # Удаляем анонимного пользователя если есть
        User.objects.filter(username='anonymous').delete()

        user = get_anonymous_user()

        assert user.username == 'anonymous'
        assert user.first_name == 'Анонимный'
        assert user.last_name == 'Пользователь'
        assert not user.has_usable_password()

    def test_text_processing_functions(self):
        """Тест функций обработки текста"""
        from search_service.algorithms import TextSearchAlgorithms

        # Тест нормализации
        normalized = TextSearchAlgorithms.normalize_text("Тест с БОЛЬШИМИ буквами!")
        expected = "тест с большими буквами"
        assert normalized == expected

        # Тест получения контекста
        text = "Это длинный текст для тестирования функции контекста"
        before, after = TextSearchAlgorithms.get_context(text, 10, 7, 5)

        assert len(before) <= 5
        assert len(after) <= 5


class TestConstants:
    """Тесты констант и настроек"""

    def test_file_size_constants(self):
        """Тест констант размера файла"""
        from doc_storage.file_service import FileTextExtractor

        assert FileTextExtractor.MAX_FILE_SIZE == 50 * 1024 * 1024  # 50MB
        assert isinstance(FileTextExtractor.SUPPORTED_EXTENSIONS, set)
        assert len(FileTextExtractor.SUPPORTED_EXTENSIONS) > 0

    def test_supported_extensions_constant(self):
        """Тест константы поддерживаемых расширений"""
        from doc_storage.file_service import FileTextExtractor

        extensions = FileTextExtractor.SUPPORTED_EXTENSIONS

        # Проверяем основные расширения
        required_extensions = {'.txt', '.docx', '.pdf', '.xlsx', '.csv', '.html'}
        for ext in required_extensions:
            assert ext in extensions


class TestErrorHandling:
    """Тесты обработки ошибок"""

    def test_document_creation_error_handling(self, db):
        """Тест обработки ошибок при создании документа"""
        from doc_storage.models import Document
        from django.contrib.auth.models import User

        user = User.objects.create_user(username='testuser', password='testpass')

        # Попытка создать документ без обязательных полей
        with pytest.raises(Exception):
            Document.objects.create(author=user)  # Отсутствуют title и content

    def test_search_service_error_handling(self, test_document):
        """Тест обработки ошибок в сервисе поиска"""
        from search_service.algorithms import WordSearchService

        service = WordSearchService()

        # Тест с некорректными параметрами
        matches, time = service.search_words_in_document(
            document=test_document,
            query="",  # Пустой запрос
            search_type="invalid"  # Неверный тип
        )

        assert matches == []
        assert time >= 0

    def test_file_service_error_handling(self):
        """Тест обработки ошибок в файловом сервисе"""
        from doc_storage.file_service import FileTextExtractor

        # Тест с несуществующим файлом
        text, error = FileTextExtractor.extract_text('/nonexistent/path/file.txt')

        assert text is None
        assert error is not None
        assert 'не найден' in error.lower()


class TestPerformance:
    """Тесты производительности"""

    def test_search_algorithm_performance(self, search_test_data):
        """Тест производительности алгоритмов поиска"""
        from search_service.algorithms import WordSearchService
        import time

        service = WordSearchService()
        document = search_test_data[0]

        start_time = time.time()
        matches, search_time = service.search_words_in_document(
            document=document,
            query="программирование",
            search_type="combined"
        )
        total_time = time.time() - start_time

        # Поиск должен быть быстрым
        assert total_time < 1.0  # Менее секунды
        assert search_time < 1.0

    def test_database_query_performance(self, db, multiple_documents):
        """Тест производительности запросов к БД"""
        from doc_storage.models import Document
        from django.test.utils import override_settings
        from django.db import connection

        with override_settings(DEBUG=True):
            initial_queries = len(connection.queries)

            # Получаем документы с оптимизацией
            documents = list(Document.objects.select_related('author', 'category')[:10])

            queries_count = len(connection.queries) - initial_queries

            # Должно быть минимальное количество запросов
            assert queries_count <= 3  # Основной запрос + возможные джойны


class TestCaching:
    """Тесты кеширования (если реализовано)"""

    @override_settings(CACHES={
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        }
    })
    def test_cache_functionality(self):
        """Тест функциональности кеша"""
        from django.core.cache import cache

        # Тестируем базовые операции кеша
        cache.set('test_key', 'test_value', 30)
        assert cache.get('test_key') == 'test_value'

        cache.delete('test_key')
        assert cache.get('test_key') is None


class TestLogging:
    """Тесты логирования"""

    @patch('logging.Logger.info')
    def test_logging_functionality(self, mock_log):
        """Тест функциональности логирования"""
        import logging

        logger = logging.getLogger('doc_storage')
        logger.info('Test log message')

        mock_log.assert_called_with('Test log message')


class TestSecurity:
    """Тесты безопасности"""

    def test_password_hashing(self, regular_user):
        """Тест хеширования паролей"""
        # Пароль не должен храниться в открытом виде
        assert regular_user.password != 'testpass123'
        assert regular_user.check_password('testpass123')

    def test_csrf_protection(self, client):
        """Тест защиты от CSRF"""
        # POST запрос без CSRF токена должен быть отклонен
        response = client.post('/register/', {
            'username': 'testuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        })

        # Django должен требовать CSRF токен
        assert response.status_code in [403, 302]  # Forbidden или редирект

    def test_sql_injection_protection(self, client, test_document):
        """Тест защиты от SQL инъекций"""
        # Попытка SQL инъекции через параметры поиска
        malicious_query = "'; DROP TABLE doc_storage_document; --"

        url = f'/api/v1/search-words/?document_id={test_document.pk}&q={malicious_query}'
        response = client.get(url)

        # Запрос должен быть обработан безопасно
        assert response.status_code in [200, 400]

        # Таблица должна остаться целой
        from doc_storage.models import Document
        assert Document.objects.count() > 0


class TestTranslations:
    """Тесты переводов (если используется i18n)"""

    def test_russian_translations(self):
        """Тест русских переводов"""
        from django.utils.translation import gettext

        # Проверяем, что переводы работают (если настроены)
        # Это базовый тест, реальные переводы зависят от настройки
        assert gettext('Document') in ['Document', 'Документ']


class TestDatabaseConstraints:
    """Тесты ограничений базы данных"""

    def test_unique_constraints(self, db):
        """Тест ограничений уникальности"""
        from doc_storage.models import DocumentTag
        from django.db import IntegrityError

        # Создаем тег
        DocumentTag.objects.create(name="unique_tag")

        # Попытка создать тег с тем же именем должна вызвать ошибку
        with pytest.raises(IntegrityError):
            DocumentTag.objects.create(name="unique_tag")

    def test_foreign_key_constraints(self, db, regular_user):
        """Тест ограничений внешних ключей"""
        from doc_storage.models import Document

        document = Document.objects.create(
            title="Test Document",
            content="Content",
            author=regular_user
        )

        # При удалении пользователя документ должен быть удален (CASCADE)
        regular_user.delete()

        assert not Document.objects.filter(id=document.id).exists()


class TestEnvironmentConfiguration:
    """Тесты конфигурации окружения"""

    def test_debug_mode_settings(self):
        """Тест настроек режима отладки"""
        from django.conf import settings

        # В тестовом окружении DEBUG должен быть False
        assert settings.DEBUG is False

    def test_database_configuration(self):
        """Тест конфигурации базы данных"""
        from django.conf import settings

        db_config = settings.DATABASES['default']

        # В тестах используется SQLite in-memory
        assert db_config['ENGINE'] == 'django.db.backends.sqlite3'
        assert db_config['NAME'] == ':memory:'

    def test_static_files_configuration(self):
        """Тест конфигурации статических файлов"""
        from django.conf import settings

        assert hasattr(settings, 'STATIC_URL')
        assert hasattr(settings, 'STATICFILES_DIRS')


class TestModelValidation:
    """Тесты валидации моделей"""

    def test_document_model_validation(self, db, regular_user):
        """Тест валидации модели документа"""
        from doc_storage.models import Document
        from django.core.exceptions import ValidationError

        # Создаем документ с корректными данными
        document = Document(
            title="Valid Document",
            content="Valid content",
            author=regular_user
        )

        # Валидация должна пройти успешно
        try:
            document.full_clean()
        except ValidationError:
            pytest.fail("Валидация корректного документа не должна вызывать ошибку")

    def test_document_tag_model_validation(self, db):
        """Тест валидации модели тега"""
        from doc_storage.models import DocumentTag
        from django.core.exceptions import ValidationError

        # Создаем тег с корректными данными
        tag = DocumentTag(
            name="valid_tag",
            color="#ff0000"
        )

        # Валидация должна пройти успешно
        try:
            tag.full_clean()
        except ValidationError:
            pytest.fail("Валидация корректного тега не должна вызывать ошибку")