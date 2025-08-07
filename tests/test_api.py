import json

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from doc_storage.models import Document, DocumentCategory, DocumentTag, WordMatch, SearchHistory


class DocumentAPITest(TestCase):
    """Тесты для API документов"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = DocumentCategory.objects.create(
            name='Тестовая категория'
        )
        self.document = Document.objects.create(
            title='Тестовый документ',
            content='Это содержимое тестового документа для проверки поиска слов python программирование',
            author=self.user,
            category=self.category
        )

    def test_document_list_api(self):
        """Тест получения списка документов через API"""
        url = reverse('doc_storage:document-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertGreater(len(response.data['results']), 0)

    def test_document_detail_api(self):
        """Тест получения детальной информации о документе"""
        url = reverse('doc_storage:document-detail', kwargs={'pk': self.document.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], self.document.title)
        self.assertEqual(response.data['content'], self.document.content)

    def test_document_search_words_api(self):
        """Тест поиска слов в документе через API"""
        self.client.force_authenticate(user=self.user)

        url = reverse('doc_storage:document-search-words', kwargs={'pk': self.document.pk})
        response = self.client.get(url, {'q': 'python'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('document', response.data)
        self.assertIn('query', response.data)
        self.assertIn('total_matches', response.data)
        self.assertIn('matches', response.data)
        self.assertEqual(response.data['query'], 'python')

    def test_document_search_words_empty_query(self):
        """Тест поиска слов с пустым запросом"""
        url = reverse('doc_storage:document-search-words', kwargs={'pk': self.document.pk})
        response = self.client.get(url, {'q': ''})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_document_word_cloud_api(self):
        """Тест получения облака слов документа"""
        url = reverse('doc_storage:document-word-cloud', kwargs={'pk': self.document.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('document', response.data)
        self.assertIn('word_frequencies', response.data)
        self.assertIn('total_unique_words', response.data)

    def test_document_search_suggestions_api(self):
        """Тест получения поисковых подсказок"""
        url = reverse('doc_storage:document-search-suggestions', kwargs={'pk': self.document.pk})
        response = self.client.get(url, {'prefix': 'пр'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('suggestions', response.data)

    def test_document_create_api_with_file_upload(self):
        """Тест создания документа через API с загрузкой файла"""
        self.client.force_authenticate(user=self.user)

        # Создаем тестовый файл
        test_content = "Содержимое тестового файла с python программированием"
        test_file = SimpleUploadedFile(
            "test_document.txt",
            test_content.encode('utf-8'),
            content_type="text/plain"
        )

        url = reverse('doc_storage:upload_file_api')
        data = {
            'file': test_file,
            'title': 'Документ из файла',
            'category_id': self.category.id
        }
        response = self.client.post(url, data, format='multipart')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Документ из файла')
        self.assertEqual(response.data['author']['username'], self.user.username)
        self.assertIn('python программированием', response.data['content'])

    def test_document_create_api_unauthenticated(self):
        """Тест создания документа без авторизации"""
        url = reverse('doc_storage:document-list')
        data = {
            'title': 'Новый документ',
            'content': 'Содержимое нового документа'
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_document_update_api(self):
        """Тест обновления документа через API"""
        self.client.force_authenticate(user=self.user)

        url = reverse('doc_storage:document-detail', kwargs={'pk': self.document.pk})
        data = {
            'title': 'Обновленный заголовок',
            'content': self.document.content
        }
        response = self.client.patch(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], data['title'])

    def test_document_delete_api(self):
        """Тест удаления документа через API"""
        self.client.force_authenticate(user=self.user)

        url = reverse('doc_storage:document-detail', kwargs={'pk': self.document.pk})
        response = self.client.delete(url)

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        # Проверяем, что документ действительно удален
        self.assertFalse(Document.objects.filter(pk=self.document.pk).exists())


class WordSearchAPITest(TestCase):
    """Тесты для API поиска слов в документах"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='searcher',
            password='testpass123'
        )

        # Создаем документ для поиска
        self.document = Document.objects.create(
            title='Python программирование',
            content='''Python - это высокоуровневый язык программирования.
            Изучение Python включает в себя основы синтаксиса, структуры данных.
            Программирование на Python используется в веб-разработке, data science.
            Многие разработчики выбирают Python за его простоту и мощность.''',
            author=self.user
        )

    def test_search_words_api_with_results(self):
        """Тест поиска слов с результатами"""
        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {
            'document_id': self.document.id,
            'q': 'python'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('document', response.data)
        self.assertIn('query', response.data)
        self.assertIn('total_matches', response.data)
        self.assertIn('search_time', response.data)
        self.assertIn('matches', response.data)
        self.assertGreater(response.data['total_matches'], 0)

    def test_search_words_api_no_results(self):
        """Тест поиска слов без результатов"""
        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {
            'document_id': self.document.id,
            'q': 'несуществующееслово12345'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_matches'], 0)
        self.assertEqual(len(response.data['matches']), 0)

    def test_search_words_api_empty_query(self):
        """Тест поиска слов с пустым запросом"""
        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {
            'document_id': self.document.id,
            'q': ''
        })

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_search_words_api_missing_document_id(self):
        """Тест поиска слов без указания ID документа"""
        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {'q': 'python'})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_search_words_api_nonexistent_document(self):
        """Тест поиска слов в несуществующем документе"""
        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {
            'document_id': 99999,
            'q': 'python'
        })

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn('error', response.data)

    def test_search_words_api_different_types(self):
        """Тест разных типов поиска слов"""
        url = reverse('doc_storage:search_words_api')
        search_types = ['exact', 'partial', 'fuzzy', 'combined']

        for search_type in search_types:
            response = self.client.get(url, {
                'document_id': self.document.id,
                'q': 'программирование',
                'type': search_type
            })

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['search_type'], search_type)

    def test_search_words_creates_word_matches(self):
        """Тест создания записей WordMatch при поиске"""
        initial_count = WordMatch.objects.count()

        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {
            'document_id': self.document.id,
            'q': 'python'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        final_count = WordMatch.objects.count()
        self.assertGreater(final_count, initial_count)

    def test_search_words_creates_history(self):
        """Тест создания записи в истории поиска"""
        self.client.force_authenticate(user=self.user)
        initial_count = SearchHistory.objects.count()

        url = reverse('doc_storage:search_words_api')
        response = self.client.get(url, {
            'document_id': self.document.id,
            'q': 'python'
        })

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        final_count = SearchHistory.objects.count()
        self.assertEqual(final_count, initial_count + 1)

        # Проверяем созданную запись
        last_history = SearchHistory.objects.latest('created_at')
        self.assertEqual(last_history.query, 'python')
        self.assertEqual(last_history.document, self.document)


class WordCloudAPITest(TestCase):
    """Тесты для API облака слов"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        self.document = Document.objects.create(
            title='Тестовый документ',
            content='python программирование разработка python веб python анализ данных',
            author=self.user
        )

    def test_word_cloud_api(self):
        """Тест получения облака слов через API"""
        url = reverse('doc_storage:word_cloud_api', kwargs={'document_id': self.document.id})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('document', response.data)
        self.assertIn('word_frequencies', response.data)
        self.assertIn('total_unique_words', response.data)

        # Проверяем, что 'python' имеет высокую частоту
        word_frequencies = response.data['word_frequencies']
        self.assertIn('python', word_frequencies)
        self.assertEqual(word_frequencies['python'], 3)

    def test_word_cloud_nonexistent_document(self):
        """Тест получения облака слов для несуществующего документа"""
        url = reverse('doc_storage:word_cloud_api', kwargs={'document_id': 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SearchSuggestionsAPITest(TestCase):
    """Тесты для API поисковых подсказок"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        self.document = Document.objects.create(
            title='Тестовый документ',
            content='программирование python разработка программист программный код',
            author=self.user
        )

    def test_search_suggestions_api(self):
        """Тест получения поисковых подсказок"""
        url = reverse('doc_storage:suggestions_api', kwargs={'document_id': self.document.id})
        response = self.client.get(url, {'prefix': 'прог'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('suggestions', response.data)

        suggestions = response.data['suggestions']
        self.assertGreater(len(suggestions), 0)

        # Проверяем структуру предложений
        first_suggestion = suggestions[0]
        self.assertIn('word', first_suggestion)
        self.assertIn('frequency', first_suggestion)
        self.assertIn('context_preview', first_suggestion)

        # Проверяем, что все предложения начинаются с префикса
        for suggestion in suggestions:
            self.assertTrue(suggestion['word'].startswith('прог'))

    def test_search_suggestions_short_prefix(self):
        """Тест поисковых подсказок с коротким префиксом"""
        url = reverse('doc_storage:suggestions_api', kwargs={'document_id': self.document.id})
        response = self.client.get(url, {'prefix': 'п'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Для очень коротких префиксов возвращается пустой список
        self.assertEqual(response.data['suggestions'], [])

    def test_search_suggestions_nonexistent_document(self):
        """Тест поисковых подсказок для несуществующего документа"""
        url = reverse('doc_storage:suggestions_api', kwargs={'document_id': 99999})
        response = self.client.get(url, {'prefix': 'прог'})

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class SearchStatisticsAPITest(TestCase):
    """Тесты для API статистики поиска"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')

        self.document = Document.objects.create(
            title='Тестовый документ',
            content='python программирование разработка',
            author=self.user
        )

    def test_search_statistics_api(self):
        """Тест получения статистики поиска"""
        # Сначала выполняем несколько поисков для создания статистики
        SearchHistory.objects.create(
            query='python',
            document=self.document,
            user=self.user,
            results_count=5,
            search_time=0.1
        )
        SearchHistory.objects.create(
            query='программирование',
            document=self.document,
            user=self.user,
            results_count=3,
            search_time=0.15
        )

        url = reverse('doc_storage:statistics_api')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_searches', response.data)
        self.assertIn('total_documents', response.data)
        self.assertIn('average_search_time', response.data)
        self.assertIn('most_searched_words', response.data)
        self.assertIn('documents_with_searches', response.data)

        self.assertEqual(response.data['total_searches'], 2)
        self.assertEqual(response.data['total_documents'], 1)


class CategoryAPITest(TestCase):
    """Тесты для API категорий"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = DocumentCategory.objects.create(
            name='Программирование',
            description='Статьи о программировании'
        )

    def test_category_list_api(self):
        """Тест получения списка категорий"""
        url = reverse('doc_storage:documentcategory-list')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)

    def test_category_detail_api(self):
        """Тест получения детальной информации о категории"""
        url = reverse('doc_storage:documentcategory-detail', kwargs={'pk': self.category.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], self.category.name)

    def test_category_documents_api(self):
        """Тест получения документов категории"""
        # Создаем документ в категории
        Document.objects.create(
            title='Тестовый документ',
            content='Содержимое документа с python кодом',
            author=self.user,
            category=self.category
        )

        url = reverse('doc_storage:documentcategory-documents', kwargs={'pk': self.category.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)