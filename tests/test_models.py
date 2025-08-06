import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from src.doc_storage.models import Document, DocumentCategory, DocumentTag, DocumentTagRelation, SearchHistory


class DocumentModelTest(TestCase):
    """Тесты для модели Document"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = DocumentCategory.objects.create(
            name='Тестовая категория',
            description='Описание тестовой категории'
        )

    def test_document_creation(self):
        """Тест создания документа"""
        document = Document.objects.create(
            title='Тестовый документ',
            content='Содержимое тестового документа для проверки функциональности',
            author=self.user,
            category=self.category
        )

        self.assertEqual(document.title, 'Тестовый документ')
        self.assertEqual(document.author, self.user)
        self.assertEqual(document.category, self.category)
        self.assertTrue(document.is_active)
        self.assertEqual(document.word_count, 7)  # Количество слов в content

    def test_document_str_method(self):
        """Тест строкового представления документа"""
        document = Document.objects.create(
            title='Тестовый документ',
            content='Содержимое',
            author=self.user
        )

        self.assertEqual(str(document), 'Тестовый документ')

    def test_word_count_calculation(self):
        """Тест подсчета количества слов"""
        document = Document.objects.create(
            title='Заголовок',
            content='Один два три четыре пять слов',
            author=self.user
        )

        self.assertEqual(document.word_count, 6)

    def test_empty_content_word_count(self):
        """Тест подсчета слов при пустом содержимом"""
        document = Document.objects.create(
            title='Заголовок',
            content='',
            author=self.user
        )

        self.assertEqual(document.word_count, 0)


class DocumentCategoryModelTest(TestCase):
    """Тесты для модели DocumentCategory"""

    def test_category_creation(self):
        """Тест создания категории"""
        category = DocumentCategory.objects.create(
            name='Программирование',
            description='Статьи о программировании'
        )

        self.assertEqual(category.name, 'Программирование')
        self.assertEqual(category.description, 'Статьи о программировании')

    def test_category_str_method(self):
        """Тест строкового представления категории"""
        category = DocumentCategory.objects.create(
            name='Наука',
            description='Научные статьи'
        )

        self.assertEqual(str(category), 'Наука')


class DocumentTagModelTest(TestCase):
    """Тесты для модели DocumentTag"""

    def test_tag_creation(self):
        """Тест создания тега"""
        tag = DocumentTag.objects.create(
            name='python',
            color='#ff0000'
        )

        self.assertEqual(tag.name, 'python')
        self.assertEqual(tag.color, '#ff0000')

    def test_tag_unique_name(self):
        """Тест уникальности имени тега"""
        DocumentTag.objects.create(name='python')

        with self.assertRaises(Exception):  # IntegrityError в реальной БД
            DocumentTag.objects.create(name='python')


class SearchHistoryModelTest(TestCase):
    """Тесты для модели SearchHistory"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='searcher',
            email='searcher@example.com',
            password='testpass123'
        )

    def test_search_history_creation(self):
        """Тест создания записи истории поиска"""
        history = SearchHistory.objects.create(
            query='python программирование',
            user=self.user,
            results_count=15,
            search_time=0.0234,
            ip_address='192.168.1.1'
        )

        self.assertEqual(history.query, 'python программирование')
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.results_count, 15)
        self.assertEqual(history.search_time, 0.0234)
        self.assertEqual(history.ip_address, '192.168.1.1')

    def test_search_history_str_method(self):
        """Тест строкового представления истории поиска"""
        history = SearchHistory.objects.create(
            query='тестовый запрос',
            results_count=5
        )

        expected_str = 'тестовый запрос (5 результатов)'
        self.assertEqual(str(history), expected_str)


class DocumentTagRelationModelTest(TestCase):
    """Тесты для модели DocumentTagRelation"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.document = Document.objects.create(
            title='Тестовый документ',
            content='Содержимое',
            author=self.user
        )
        self.tag = DocumentTag.objects.create(name='test')

    def test_document_tag_relation_creation(self):
        """Тест создания связи документ-тег"""
        relation = DocumentTagRelation.objects.create(
            document=self.document,
            tag=self.tag
        )

        self.assertEqual(relation.document, self.document)
        self.assertEqual(relation.tag, self.tag)

    def test_document_tag_relation_unique_together(self):
        """Тест уникальности связи документ-тег"""
        DocumentTagRelation.objects.create(
            document=self.document,
            tag=self.tag
        )

        with self.assertRaises(Exception):  # IntegrityError в реальной БД
            DocumentTagRelation.objects.create(
                document=self.document,
                tag=self.tag
            )