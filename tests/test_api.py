import json
from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from doc_storage.models import Document, DocumentCategory, DocumentTag


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
            content='Содержимое тестового документа',
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

    def test_document_create_api_authenticated(self):
        """Тест создания документа через API (авторизованный пользователь)"""
        self.client.force_authenticate(user=self.user)

        url = reverse('doc_storage:document-list')
        data = {
            'title': 'Новый документ',
            'content': 'Содержимое нового документа',
            'category_id': self.category.id
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], data['title'])
        self.assertEqual(response.data['author']['username'], self.user.username)

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


class SearchAPITest(TestCase):
    """Тесты для API поиска"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='searcher',
            password='testpass123'
        )

        # Создаем документы для поиска
        Document.objects.create(
            title='Python программирование',
            content='Изучение языка программирования Python',
            author=self.user
        )
        Document.objects.create(
            title='Java разработка',
            content='Основы разработки на Java',
            author=self.user
        )

    def test_search_api_with_results(self):
        """Тест поиска с результатами"""
        url = reverse('doc_storage:search_api')
        response = self.client.get(url, {'q': 'python'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)
        self.assertIn('total_results', response.data)
        self.assertIn('search_time', response.data)
        self.assertGreater(response.data['total_results'], 0)

    def test_search_api_no_results(self):
        """Тест поиска без результатов"""
        url = reverse('doc_storage:search_api')
        response = self.client.get(url, {'q': 'несуществующийтермин'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_results'], 0)
        self.assertEqual(len(response.data['results']), 0)

    def test_search_api_empty_query(self):
        """Тест поиска с пустым запросом"""
        url = reverse('doc_storage:search_api')
        response = self.client.get(url, {'q': ''})

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)

    def test_search_api_different_types(self):
        """Тест разных типов поиска"""
        url = reverse('doc_storage:search_api')
        search_types = ['exact', 'substring', 'fuzzy', 'combined']

        for search_type in search_types:
            response = self.client.get(url, {'q': 'программирование', 'type': search_type})

            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.assertEqual(response.data['search_type'], search_type)

    def test_search_statistics_api(self):
        """Тест получения статистики поиска"""
        # Сначала выполняем несколько поисков
        search_url = reverse('doc_storage:search_api')
        self.client.get(search_url, {'q': 'python'})
        self.client.get(search_url, {'q': 'java'})

        # Затем получаем статистику
        stats_url = reverse('doc_storage:statistics_api')
        response = self.client.get(stats_url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('total_searches', response.data)
        self.assertIn('total_documents', response.data)
        self.assertIn('popular_queries', response.data)


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
            content='Содержимое',
            author=self.user,
            category=self.category
        )

        url = reverse('doc_storage:documentcategory-documents', kwargs={'pk': self.category.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)