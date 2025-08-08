import pytest
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from django.test import TestCase

from doc_storage.models import (Document, DocumentCategory, DocumentTag,
                                DocumentTagRelation, SearchHistory, WordMatch)


class DocumentModelTest(TestCase):
    """Тесты для модели Document"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="testpass123")
        self.category = DocumentCategory.objects.create(
            name="Тестовая категория", description="Описание тестовой категории"
        )

    def test_document_creation(self):
        """Тест создания документа"""
        document = Document.objects.create(
            title="Тестовый документ",
            content="Содержимое тестового документа для проверки функциональности python программирование",
            author=self.user,
            category=self.category,
        )

        self.assertEqual(document.title, "Тестовый документ")
        self.assertEqual(document.author, self.user)
        self.assertEqual(document.category, self.category)
        self.assertTrue(document.is_active)
        self.assertEqual(document.word_count, 8)  # Количество слов в content

    def test_document_str_method(self):
        """Тест строкового представления документа"""
        document = Document.objects.create(title="Тестовый документ", content="Содержимое", author=self.user)

        self.assertEqual(str(document), "Тестовый документ")

    def test_word_count_calculation(self):
        """Тест подсчета количества слов"""
        document = Document.objects.create(title="Заголовок", content="Один два три четыре пять слов", author=self.user)

        self.assertEqual(document.word_count, 6)

    def test_empty_content_word_count(self):
        """Тест подсчета слов при пустом содержимом"""
        document = Document.objects.create(title="Заголовок", content="", author=self.user)

        self.assertEqual(document.word_count, 0)

    def test_document_update_word_count(self):
        """Тест обновления количества слов при изменении содержимого"""
        document = Document.objects.create(
            title="Тестовый документ", content="Первоначальное содержимое", author=self.user
        )

        initial_word_count = document.word_count
        self.assertEqual(initial_word_count, 2)

        # Обновляем содержимое
        document.content = "Новое расширенное содержимое документа с большим количеством слов"
        document.save()

        self.assertGreater(document.word_count, initial_word_count)
        self.assertEqual(document.word_count, 9)

    def test_document_with_file_path(self):
        """Тест документа с файлом"""
        document = Document.objects.create(
            title="Документ с файлом", content="Содержимое из файла", file_path="documents/test.txt", author=self.user
        )

        self.assertTrue(document.file_path)
        self.assertEqual(str(document.file_path), "documents/test.txt")


class DocumentCategoryModelTest(TestCase):
    """Тесты для модели DocumentCategory"""

    def test_category_creation(self):
        """Тест создания категории"""
        category = DocumentCategory.objects.create(name="Программирование", description="Статьи о программировании")

        self.assertEqual(category.name, "Программирование")
        self.assertEqual(category.description, "Статьи о программировании")

    def test_category_str_method(self):
        """Тест строкового представления категории"""
        category = DocumentCategory.objects.create(name="Наука", description="Научные статьи")

        self.assertEqual(str(category), "Наука")

    def test_category_ordering(self):
        """Тест сортировки категорий по имени"""
        cat1 = DocumentCategory.objects.create(name="Я_Последняя")
        cat2 = DocumentCategory.objects.create(name="А_Первая")
        cat3 = DocumentCategory.objects.create(name="В_Средняя")

        categories = list(DocumentCategory.objects.all())
        self.assertEqual(categories[0].name, "А_Первая")
        self.assertEqual(categories[1].name, "В_Средняя")
        self.assertEqual(categories[2].name, "Я_Последняя")

    def test_category_without_description(self):
        """Тест создания категории без описания"""
        category = DocumentCategory.objects.create(name="Без описания")
        self.assertEqual(category.description, "")


class DocumentTagModelTest(TestCase):
    """Тесты для модели DocumentTag"""

    def test_tag_creation(self):
        """Тест создания тега"""
        tag = DocumentTag.objects.create(name="python", color="#ff0000")

        self.assertEqual(tag.name, "python")
        self.assertEqual(tag.color, "#ff0000")

    def test_tag_str_method(self):
        """Тест строкового представления тега"""
        tag = DocumentTag.objects.create(name="javascript")
        self.assertEqual(str(tag), "javascript")

    def test_tag_default_color(self):
        """Тест цвета тега по умолчанию"""
        tag = DocumentTag.objects.create(name="defaultcolor")
        self.assertEqual(tag.color, "#007bff")

    def test_tag_unique_name(self):
        """Тест уникальности имени тега"""
        DocumentTag.objects.create(name="python")

        with self.assertRaises(IntegrityError):
            DocumentTag.objects.create(name="python")


class WordMatchModelTest(TestCase):
    """Тесты для модели WordMatch"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.document = Document.objects.create(
            title="Тестовый документ",
            content="Python это язык программирования для разработки приложений",
            author=self.user,
        )

    def test_word_match_creation(self):
        """Тест создания найденного слова"""
        word_match = WordMatch.objects.create(
            document=self.document,
            query="python",
            matched_word="Python",
            position=0,
            context_before="",
            context_after="это язык программирования",
            match_type="exact",
            relevance_score=1.0,
        )

        self.assertEqual(word_match.document, self.document)
        self.assertEqual(word_match.query, "python")
        self.assertEqual(word_match.matched_word, "Python")
        self.assertEqual(word_match.position, 0)
        self.assertEqual(word_match.match_type, "exact")
        self.assertEqual(word_match.relevance_score, 1.0)

    def test_word_match_str_method(self):
        """Тест строкового представления найденного слова"""
        word_match = WordMatch.objects.create(
            document=self.document,
            query="программирование",
            matched_word="программирования",
            position=20,
            match_type="partial",
        )

        expected_str = f"программирования в {self.document.title}"
        self.assertEqual(str(word_match), expected_str)

    def test_word_match_ordering(self):
        """Тест сортировки найденных слов"""
        # Создаем несколько совпадений с разными оценками релевантности
        match1 = WordMatch.objects.create(
            document=self.document, query="test", matched_word="test1", position=10, relevance_score=0.5
        )
        match2 = WordMatch.objects.create(
            document=self.document, query="test", matched_word="test2", position=5, relevance_score=1.0
        )
        match3 = WordMatch.objects.create(
            document=self.document, query="test", matched_word="test3", position=15, relevance_score=1.0
        )

        matches = list(WordMatch.objects.all())

        # Первый должен быть с наивысшей релевантностью и наименьшей позицией
        self.assertEqual(matches[0], match2)
        self.assertEqual(matches[1], match3)  # Та же релевантность, но позиция больше
        self.assertEqual(matches[2], match1)  # Наименьшая релевантность

    def test_word_match_types(self):
        """Тест разных типов совпадений"""
        exact_match = WordMatch.objects.create(
            document=self.document, query="python", matched_word="python", position=0, match_type="exact"
        )

        partial_match = WordMatch.objects.create(
            document=self.document, query="прог", matched_word="программирования", position=20, match_type="partial"
        )

        fuzzy_match = WordMatch.objects.create(
            document=self.document,
            query="питон",
            matched_word="python",
            position=0,
            match_type="fuzzy",
            relevance_score=0.8,
        )

        self.assertEqual(exact_match.match_type, "exact")
        self.assertEqual(partial_match.match_type, "partial")
        self.assertEqual(fuzzy_match.match_type, "fuzzy")

    def test_word_match_context_truncation(self):
        """Тест усечения контекста до 200 символов"""
        long_context = "a" * 300
        word_match = WordMatch.objects.create(
            document=self.document,
            query="test",
            matched_word="test",
            position=0,
            context_before=long_context,
            context_after=long_context,
        )

        self.assertEqual(len(word_match.context_before), 200)
        self.assertEqual(len(word_match.context_after), 200)


class SearchHistoryModelTest(TestCase):
    """Тесты для модели SearchHistory"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username="searcher", email="searcher@example.com", password="testpass123")
        self.document = Document.objects.create(
            title="Тестовый документ", content="Содержимое документа для поиска", author=self.user
        )

    def test_search_history_creation(self):
        """Тест создания записи истории поиска"""
        history = SearchHistory.objects.create(
            query="python программирование",
            document=self.document,
            user=self.user,
            results_count=15,
            search_time=0.0234,
            ip_address="192.168.1.1",
        )

        self.assertEqual(history.query, "python программирование")
        self.assertEqual(history.document, self.document)
        self.assertEqual(history.user, self.user)
        self.assertEqual(history.results_count, 15)
        self.assertEqual(history.search_time, 0.0234)
        self.assertEqual(history.ip_address, "192.168.1.1")

    def test_search_history_str_method(self):
        """Тест строкового представления истории поиска"""
        history = SearchHistory.objects.create(query="тестовый запрос", document=self.document, results_count=5)

        expected_str = f"тестовый запрос в {self.document.title} (5 результатов)"
        self.assertEqual(str(history), expected_str)

    def test_search_history_without_user(self):
        """Тест создания истории поиска без пользователя"""
        history = SearchHistory.objects.create(
            query="анонимный поиск", document=self.document, results_count=3, ip_address="10.0.0.1"
        )

        self.assertIsNone(history.user)
        self.assertEqual(history.ip_address, "10.0.0.1")

    def test_search_history_ordering(self):
        """Тест сортировки истории поиска по дате"""
        import time

        history1 = SearchHistory.objects.create(query="первый поиск", document=self.document, user=self.user)

        time.sleep(0.01)  # Небольшая задержка для разных временных меток

        history2 = SearchHistory.objects.create(query="второй поиск", document=self.document, user=self.user)

        histories = list(SearchHistory.objects.all())
        # Более поздние записи должны быть первыми
        self.assertEqual(histories[0], history2)
        self.assertEqual(histories[1], history1)

    def test_search_history_ipv6_address(self):
        """Тест с IPv6 адресом"""
        history = SearchHistory.objects.create(query="IPv6 тест", document=self.document, ip_address="2001:db8::1")

        self.assertEqual(history.ip_address, "2001:db8::1")


class DocumentTagRelationModelTest(TestCase):
    """Тесты для модели DocumentTagRelation"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username="testuser", password="testpass123")
        self.document = Document.objects.create(
            title="Тестовый документ", content="Содержимое для тестирования тегов", author=self.user
        )
        self.tag = DocumentTag.objects.create(name="test")

    def test_document_tag_relation_creation(self):
        """Тест создания связи документ-тег"""
        relation = DocumentTagRelation.objects.create(document=self.document, tag=self.tag)

        self.assertEqual(relation.document, self.document)
        self.assertEqual(relation.tag, self.tag)
        self.assertIsNotNone(relation.created_at)

    def test_document_tag_relation_str_method(self):
        """Тест строкового представления связи"""
        relation = DocumentTagRelation.objects.create(document=self.document, tag=self.tag)

        expected_str = f"{self.document.title} - {self.tag.name}"
        self.assertEqual(str(relation), expected_str)

    def test_document_tag_relation_unique_together(self):
        """Тест уникальности связи документ-тег"""
        DocumentTagRelation.objects.create(document=self.document, tag=self.tag)

        with self.assertRaises(IntegrityError):
            DocumentTagRelation.objects.create(document=self.document, tag=self.tag)

    def test_multiple_tags_per_document(self):
        """Тест добавления нескольких тегов к одному документу"""
        tag1 = DocumentTag.objects.create(name="python")
        tag2 = DocumentTag.objects.create(name="programming")
        tag3 = DocumentTag.objects.create(name="web")

        DocumentTagRelation.objects.create(document=self.document, tag=tag1)
        DocumentTagRelation.objects.create(document=self.document, tag=tag2)
        DocumentTagRelation.objects.create(document=self.document, tag=tag3)

        # Проверяем, что у документа есть все три тега
        document_tags = self.document.tag_relations.all()
        self.assertEqual(document_tags.count(), 3)

        tag_names = [relation.tag.name for relation in document_tags]
        self.assertIn("python", tag_names)
        self.assertIn("programming", tag_names)
        self.assertIn("web", tag_names)

    def test_multiple_documents_per_tag(self):
        """Тест добавления одного тега к нескольким документам"""
        doc1 = Document.objects.create(title="Документ 1", content="Содержимое первого документа", author=self.user)
        doc2 = Document.objects.create(title="Документ 2", content="Содержимое второго документа", author=self.user)

        python_tag = DocumentTag.objects.create(name="python")

        DocumentTagRelation.objects.create(document=doc1, tag=python_tag)
        DocumentTagRelation.objects.create(document=doc2, tag=python_tag)

        # Проверяем, что тег связан с двумя документами
        tag_relations = python_tag.document_relations.all()
        self.assertEqual(tag_relations.count(), 2)

        document_titles = [relation.document.title for relation in tag_relations]
        self.assertIn("Документ 1", document_titles)
        self.assertIn("Документ 2", document_titles)

    def test_cascade_deletion(self):
        """Тест каскадного удаления"""
        relation = DocumentTagRelation.objects.create(document=self.document, tag=self.tag)

        # Удаляем документ
        self.document.delete()

        # Связь должна быть удалена
        self.assertFalse(DocumentTagRelation.objects.filter(id=relation.id).exists())

        # Создаем новые объекты для тестирования удаления тега
        new_document = Document.objects.create(title="Новый документ", content="Новое содержимое", author=self.user)
        new_relation = DocumentTagRelation.objects.create(document=new_document, tag=self.tag)

        # Удаляем тег
        self.tag.delete()

        # Связь должна быть удалена
        self.assertFalse(DocumentTagRelation.objects.filter(id=new_relation.id).exists())


class ModelIntegrationTest(TestCase):
    """Интеграционные тесты моделей"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username="integrationuser", password="testpass123")
        self.category = DocumentCategory.objects.create(name="Интеграционная категория")

    def test_full_document_workflow(self):
        """Тест полного рабочего процесса с документом"""
        # Создаем документ
        document = Document.objects.create(
            title="Интеграционный тест",
            content="Python программирование с алгоритмами поиска",
            author=self.user,
            category=self.category,
        )

        # Добавляем теги
        tag1 = DocumentTag.objects.create(name="python")
        tag2 = DocumentTag.objects.create(name="алгоритмы")

        DocumentTagRelation.objects.create(document=document, tag=tag1)
        DocumentTagRelation.objects.create(document=document, tag=tag2)

        # Создаем поиск
        history = SearchHistory.objects.create(query="python", document=document, user=self.user, results_count=2)

        # Создаем совпадения
        WordMatch.objects.create(
            document=document,
            query="python",
            matched_word="Python",
            position=0,
            match_type="exact",
            relevance_score=1.0,
        )

        # Проверяем, что все связано правильно
        self.assertEqual(document.tag_relations.count(), 2)
        self.assertEqual(SearchHistory.objects.filter(document=document).count(), 1)
        self.assertEqual(WordMatch.objects.filter(document=document).count(), 1)

        # Проверяем обратные связи
        self.assertEqual(tag1.document_relations.count(), 1)
        self.assertEqual(self.category.document_set.count(), 1)
        self.assertEqual(self.user.document_set.count(), 1)
