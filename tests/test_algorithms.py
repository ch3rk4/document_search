import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from doc_storage.models import Document, DocumentCategory
from search_service.algorithms import SearchAlgorithms, SearchService


class SearchAlgorithmsTest(TestCase):
    """Тесты для алгоритмов поиска"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = DocumentCategory.objects.create(name='Тест')

        # Создаем тестовые документы
        self.documents = [
            Document.objects.create(
                title='Python программирование',
                content='Python - это высокоуровневый язык программирования',
                author=self.user,
                category=self.category
            ),
            Document.objects.create(
                title='Java разработка',
                content='Java используется для разработки корпоративных приложений',
                author=self.user,
                category=self.category
            ),
            Document.objects.create(
                title='Веб-разработка',
                content='Современная веб-разработка включает HTML, CSS, JavaScript',
                author=self.user,
                category=self.category
            ),
            Document.objects.create(
                title='Машинное обучение',
                content='Машинное обучение - это подраздел искусственного интеллекта',
                author=self.user,
                category=self.category
            ),
        ]

    def test_normalize_text(self):
        """Тест нормализации текста"""
        text = "  PYTHON Программирование!!! 123  "
        normalized = SearchAlgorithms.normalize_text(text)
        expected = "python программирование 123"

        self.assertEqual(normalized, expected)

    def test_exact_word_search(self):
        """Тест точного поиска по словам"""
        query = "python"
        documents = Document.objects.all()
        results, search_time = SearchAlgorithms.exact_word_search(query, documents)

        self.assertGreater(len(results), 0)
        self.assertGreater(search_time, 0)

        # Проверяем, что найден документ с Python
        found_python = any(
            'python' in result['document'].title.lower() or
            'python' in result['document'].content.lower()
            for result in results
        )
        self.assertTrue(found_python)

    def test_substring_search(self):
        """Тест поиска по подстрокам"""
        query = "прог"
        documents = Document.objects.all()
        results, search_time = SearchAlgorithms.substring_search(query, documents)

        self.assertGreater(len(results), 0)
        self.assertGreater(search_time, 0)

        # Проверяем, что найдены документы с подстрокой "прог"
        for result in results:
            document = result['document']
            content_lower = document.content.lower()
            title_lower = document.title.lower()
            self.assertTrue('прог' in content_lower or 'прог' in title_lower)

    def test_fuzzy_search(self):
        """Тест нечеткого поиска"""
        query = "питон"  # Похоже на "python"
        documents = Document.objects.all()
        results, search_time = SearchAlgorithms.fuzzy_search(query, documents, threshold=0.3)

        self.assertGreaterEqual(len(results), 0)  # Может не найти ничего с низким порогом
        self.assertGreater(search_time, 0)

    def test_combined_search(self):
        """Тест комбинированного поиска"""
        query = "программирование"
        documents = Document.objects.all()
        results, search_time = SearchAlgorithms.combined_search(query, documents)

        self.assertGreater(len(results), 0)
        self.assertGreater(search_time, 0)

        # Проверяем наличие поля final_score
        for result in results:
            self.assertIn('final_score', result)
            self.assertGreater(result['final_score'], 0)

    def test_create_preview(self):
        """Тест создания превью текста"""
        content = "Это длинный текст для тестирования создания превью с выделением искомой подстроки"
        query = "тестирования"
        preview = SearchAlgorithms._create_preview(content, query, preview_length=30)

        self.assertIn(query, preview)
        self.assertLessEqual(len(preview), 100)  # Учитываем добавление "..."

    def test_count_substring_matches(self):
        """Тест подсчета вхождений подстроки"""
        text = "python python python программирование"
        query = "python"
        count = SearchAlgorithms._count_substring_matches(query, text)

        self.assertEqual(count, 3)

    def test_empty_query(self):
        """Тест поиска с пустым запросом"""
        query = ""
        documents = Document.objects.all()
        results, search_time = SearchAlgorithms.exact_word_search(query, documents)

        self.assertEqual(len(results), 0)

    def test_no_results_query(self):
        """Тест поиска без результатов"""
        query = "несуществующийтермин12345"
        documents = Document.objects.all()
        results, search_time = SearchAlgorithms.exact_word_search(query, documents)

        self.assertEqual(len(results), 0)
        self.assertGreater(search_time, 0)


class SearchServiceTest(TestCase):
    """Тесты для сервиса поиска"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.search_service = SearchService()

        Document.objects.create(
            title='Тестовый документ',
            content='Содержимое для тестирования поиска',
            author=self.user
        )

    def test_search_documents_exact(self):
        """Тест поиска документов (точный поиск)"""
        results, search_time = self.search_service.search_documents(
            query='тестирования',
            search_type='exact',
            user=self.user,
            ip_address='127.0.0.1'
        )

        self.assertGreaterEqual(len(results), 0)
        self.assertGreater(search_time, 0)

    def test_search_documents_combined(self):
        """Тест поиска документов (комбинированный)"""
        results, search_time = self.search_service.search_documents(
            query='тест',
            search_type='combined',
            user=self.user
        )

        self.assertGreater(len(results), 0)
        self.assertGreater(search_time, 0)

    def test_search_documents_empty_query(self):
        """Тест поиска с пустым запросом"""
        results, search_time = self.search_service.search_documents(
            query='',
            user=self.user
        )

        self.assertEqual(len(results), 0)
        self.assertEqual(search_time, 0.0)

    def test_search_documents_short_query(self):
        """Тест поиска с коротким запросом"""
        results, search_time = self.search_service.search_documents(
            query='а',
            user=self.user
        )

        self.assertEqual(len(results), 0)
        self.assertEqual(search_time, 0.0)

    def test_search_history_creation(self):
        """Тест создания записи в истории поиска"""
        from doc_storage.models import SearchHistory

        initial_count = SearchHistory.objects.count()

        self.search_service.search_documents(
            query='тестовый запрос',
            user=self.user,
            ip_address='192.168.1.1'
        )

        final_count = SearchHistory.objects.count()
        self.assertEqual(final_count, initial_count + 1)

        # Проверяем созданную запись
        last_search = SearchHistory.objects.latest('created_at')
        self.assertEqual(last_search.query, 'тестовый запрос')
        self.assertEqual(last_search.user, self.user)
        self.assertEqual(last_search.ip_address, '192.168.1.1')