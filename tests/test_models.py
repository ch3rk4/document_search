"""
Тесты для моделей приложения doc_storage
"""
import pytest
from django.db import IntegrityError

from doc_storage.models import (
    Document, DocumentCategory, DocumentTag,
    DocumentTagRelation, WordMatch, SearchHistory
)


class TestDocumentCategory:
    """Тесты модели DocumentCategory"""

    def test_create_category(self, db):
        """Тест создания категории"""
        category = DocumentCategory.objects.create(
            name="Тестовая категория",
            description="Описание тестовой категории"
        )

        assert category.name == "Тестовая категория"
        assert category.description == "Описание тестовой категории"
        assert category.created_at is not None
        assert str(category) == "Тестовая категория"

    def test_category_str_representation(self, test_category):
        """Тест строкового представления категории"""
        assert str(test_category) == "Тестовая категория"

    def test_category_ordering(self, db):
        """Тест сортировки категорий по имени"""
        category_b = DocumentCategory.objects.create(name="B категория")
        category_a = DocumentCategory.objects.create(name="A категория")
        category_c = DocumentCategory.objects.create(name="C категория")

        categories = list(DocumentCategory.objects.all())
        assert categories[0].name == "A категория"
        assert categories[1].name == "B категория"
        assert categories[2].name == "C категория"

    def test_category_without_description(self, db):
        """Тест создания категории без описания"""
        category = DocumentCategory.objects.create(name="Без описания")
        assert category.description == ""


class TestDocumentTag:
    """Тесты модели DocumentTag"""

    def test_create_tag(self, db):
        """Тест создания тега"""
        tag = DocumentTag.objects.create(
            name="python",
            color="#3776ab"
        )

        assert tag.name == "python"
        assert tag.color == "#3776ab"
        assert tag.created_at is not None
        assert str(tag) == "python"

    def test_tag_unique_name(self, db):
        """Тест уникальности имени тега"""
        DocumentTag.objects.create(name="python")

        with pytest.raises(IntegrityError):
            DocumentTag.objects.create(name="python")

    def test_tag_default_color(self, db):
        """Тест цвета тега по умолчанию"""
        tag = DocumentTag.objects.create(name="test")
        assert tag.color == "#007bff"

    def test_tag_ordering(self, db):
        """Тест сортировки тегов по имени"""
        DocumentTag.objects.create(name="zebra")
        DocumentTag.objects.create(name="alpha")
        DocumentTag.objects.create(name="beta")

        tags = list(DocumentTag.objects.all())
        assert tags[0].name == "alpha"
        assert tags[1].name == "beta"
        assert tags[2].name == "zebra"


class TestDocument:
    """Тесты модели Document"""

    def test_create_document(self, db, regular_user, test_category):
        """Тест создания документа"""
        document = Document.objects.create(
            title="Тестовый документ",
            content="Содержимое тестового документа",
            author=regular_user,
            category=test_category
        )

        assert document.title == "Тестовый документ"
        assert document.content == "Содержимое тестового документа"
        assert document.author == regular_user
        assert document.category == test_category
        assert document.is_active is True
        assert document.word_count > 0
        assert document.created_at is not None
        assert document.updated_at is not None
        assert str(document) == "Тестовый документ"

    def test_document_word_count_calculation(self, db, regular_user):
        """Тест автоматического подсчета слов"""
        content = "Это тестовый документ с пятью словами"
        document = Document.objects.create(
            title="Тест",
            content=content,
            author=regular_user
        )

        expected_count = len(content.split())
        assert document.word_count == expected_count

    def test_document_word_count_empty_content(self, db, regular_user):
        """Тест подсчета слов для пустого содержимого"""
        document = Document.objects.create(
            title="Пустой документ",
            content="",
            author=regular_user
        )

        assert document.word_count == 0

    def test_document_word_count_whitespace_content(self, db, regular_user):
        """Тест подсчета слов для содержимого только с пробелами"""
        document = Document.objects.create(
            title="Пробелы",
            content="   \n\t   ",
            author=regular_user
        )

        assert document.word_count == 0

    def test_document_without_category(self, db, regular_user):
        """Тест создания документа без категории"""
        document = Document.objects.create(
            title="Без категории",
            content="Содержимое",
            author=regular_user
        )

        assert document.category is None

    def test_document_inactive(self, db, regular_user):
        """Тест создания неактивного документа"""
        document = Document.objects.create(
            title="Неактивный",
            content="Содержимое",
            author=regular_user,
            is_active=False
        )

        assert document.is_active is False

    def test_document_ordering(self, db, regular_user):
        """Тест сортировки документов по дате создания"""
        doc1 = Document.objects.create(
            title="Первый", content="Содержимое", author=regular_user
        )
        doc2 = Document.objects.create(
            title="Второй", content="Содержимое", author=regular_user
        )

        documents = list(Document.objects.all())
        assert documents[0] == doc2  # Новее должен быть первым
        assert documents[1] == doc1

    def test_document_str_representation(self, test_document):
        """Тест строкового представления документа"""
        assert str(test_document) == "Тестовый документ"


class TestDocumentTagRelation:
    """Тесты модели DocumentTagRelation"""

    def test_create_tag_relation(self, db, test_document, test_tag):
        """Тест создания связи документ-тег"""
        relation = DocumentTagRelation.objects.create(
            document=test_document,
            tag=test_tag
        )

        assert relation.document == test_document
        assert relation.tag == test_tag
        assert relation.created_at is not None
        assert str(relation) == f"{test_document.title} - {test_tag.name}"

    def test_unique_document_tag_relation(self, db, test_document, test_tag):
        """Тест уникальности связи документ-тег"""
        DocumentTagRelation.objects.create(
            document=test_document,
            tag=test_tag
        )

        with pytest.raises(IntegrityError):
            DocumentTagRelation.objects.create(
                document=test_document,
                tag=test_tag
            )

    def test_multiple_tags_for_document(self, db, test_document):
        """Тест множественных тегов для одного документа"""
        tag1 = DocumentTag.objects.create(name="tag1")
        tag2 = DocumentTag.objects.create(name="tag2")

        DocumentTagRelation.objects.create(document=test_document, tag=tag1)
        DocumentTagRelation.objects.create(document=test_document, tag=tag2)

        relations = DocumentTagRelation.objects.filter(document=test_document)
        assert relations.count() == 2


class TestWordMatch:
    """Тесты модели WordMatch"""

    def test_create_word_match(self, db, test_document):
        """Тест создания совпадения слова"""
        word_match = WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тестовый",
            position=10,
            context_before="Это ",
            context_after=" документ",
            match_type="partial",
            relevance_score=0.8
        )

        assert word_match.document == test_document
        assert word_match.query == "тест"
        assert word_match.matched_word == "тестовый"
        assert word_match.position == 10
        assert word_match.context_before == "Это "
        assert word_match.context_after == " документ"
        assert word_match.match_type == "partial"
        assert word_match.relevance_score == 0.8
        assert word_match.created_at is not None

    def test_word_match_str_representation(self, db, test_document):
        """Тест строкового представления совпадения"""
        word_match = WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тестовый",
            position=10
        )

        expected = f"тестовый в {test_document.title}"
        assert str(word_match) == expected

    def test_word_match_ordering(self, db, test_document):
        """Тест сортировки совпадений"""
        match1 = WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест1",
            position=20,
            relevance_score=0.7
        )
        match2 = WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест2",
            position=10,
            relevance_score=0.9
        )

        matches = list(WordMatch.objects.all())
        assert matches[0] == match2  # Больше релевантность
        assert matches[1] == match1

    def test_word_match_context_truncation(self, db, test_document):
        """Тест обрезания контекста при сохранении"""
        long_context = "x" * 250  # Больше лимита в 200 символов

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

    def test_word_match_choices(self, db, test_document):
        """Тест валидности выборов типа совпадения"""
        valid_types = ["exact", "partial", "fuzzy"]

        for match_type in valid_types:
            word_match = WordMatch.objects.create(
                document=test_document,
                query="тест",
                matched_word="тест",
                position=10,
                match_type=match_type
            )
            assert word_match.match_type == match_type


class TestSearchHistory:
    """Тесты модели SearchHistory"""

    def test_create_search_history(self, db, test_document, regular_user):
        """Тест создания истории поиска"""
        search_history = SearchHistory.objects.create(
            query="python",
            document=test_document,
            user=regular_user,
            results_count=5,
            search_time=0.123,
            ip_address="127.0.0.1"
        )

        assert search_history.query == "python"
        assert search_history.document == test_document
        assert search_history.user == regular_user
        assert search_history.results_count == 5
        assert search_history.search_time == 0.123
        assert search_history.ip_address == "127.0.0.1"
        assert search_history.created_at is not None

    def test_search_history_without_user(self, db, test_document):
        """Тест создания истории поиска без пользователя"""
        search_history = SearchHistory.objects.create(
            query="anonymous search",
            document=test_document,
            results_count=3,
            search_time=0.05
        )

        assert search_history.user is None

    def test_search_history_str_representation(self, db, test_document, regular_user):
        """Тест строкового представления истории поиска"""
        search_history = SearchHistory.objects.create(
            query="тест",
            document=test_document,
            user=regular_user,
            results_count=2
        )

        expected = f"тест в {test_document.title} (2 результатов)"
        assert str(search_history) == expected

    def test_search_history_ordering(self, db, test_document, regular_user):
        """Тест сортировки истории поиска"""
        history1 = SearchHistory.objects.create(
            query="первый",
            document=test_document,
            user=regular_user
        )
        history2 = SearchHistory.objects.create(
            query="второй",
            document=test_document,
            user=regular_user
        )

        histories = list(SearchHistory.objects.all())
        assert histories[0] == history2  # Новее должен быть первым
        assert histories[1] == history1

    def test_search_history_default_values(self, db, test_document):
        """Тест значений по умолчанию"""
        search_history = SearchHistory.objects.create(
            query="тест",
            document=test_document
        )

        assert search_history.results_count == 0
        assert search_history.search_time == 0.0
        assert search_history.ip_address is None


class TestModelRelationships:
    """Тесты связей между моделями"""

    def test_document_category_cascade(self, db, test_document, test_category):
        """Тест каскадного удаления при удалении категории"""
        category_id = test_category.id
        document_id = test_document.id

        # Удаляем категорию
        test_category.delete()

        # Документ должен остаться, но категория должна быть None
        document = Document.objects.get(id=document_id)
        assert document.category is None

    def test_document_author_cascade(self, db, test_document, regular_user):
        """Тест каскадного удаления при удалении автора"""
        document_id = test_document.id

        # Удаляем автора
        regular_user.delete()

        # Документ должен быть удален
        assert not Document.objects.filter(id=document_id).exists()

    def test_tag_relation_cascade(self, db, test_document_with_tags, test_tag):
        """Тест каскадного удаления связей при удалении тега"""
        # Проверяем, что связь существует
        assert DocumentTagRelation.objects.filter(
            document=test_document_with_tags,
            tag=test_tag
        ).exists()

        # Удаляем тег
        test_tag.delete()

        # Связь должна быть удалена
        assert not DocumentTagRelation.objects.filter(
            document=test_document_with_tags
        ).exists()

    def test_word_match_document_cascade(self, db, test_document):
        """Тест каскадного удаления совпадений при удалении документа"""
        word_match = WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест",
            position=10
        )

        match_id = word_match.id

        # Удаляем документ
        test_document.delete()

        # Совпадение должно быть удалено
        assert not WordMatch.objects.filter(id=match_id).exists()

    def test_search_history_document_cascade(self, db, test_document, regular_user):
        """Тест каскадного удаления истории при удалении документа"""
        search_history = SearchHistory.objects.create(
            query="тест",
            document=test_document,
            user=regular_user
        )

        history_id = search_history.id

        # Удаляем документ
        test_document.delete()

        # История должна быть удалена
        assert not SearchHistory.objects.filter(id=history_id).exists()


class TestModelIndexes:
    """Тесты индексов моделей"""

    def test_document_indexes_exist(self, db):
        """Тест существования индексов для модели Document"""
        # Проверяем, что индексы определены в Meta
        meta = Document._meta
        index_fields = []

        for index in meta.indexes:
            index_fields.extend(index.fields)

        expected_fields = ['title', 'created_at', 'category', 'author']
        for field in expected_fields:
            assert field in index_fields or f'-{field}' in index_fields

    def test_word_match_indexes_exist(self, db):
        """Тест существования индексов для модели WordMatch"""
        meta = WordMatch._meta
        index_fields = []

        for index in meta.indexes:
            for field in index.fields:
                index_fields.append(field)

        expected_fields = ['matched_word', 'position']
        for field in expected_fields:
            assert field in index_fields

    def test_search_history_indexes_exist(self, db):
        """Тест существования индексов для модели SearchHistory"""
        meta = SearchHistory._meta
        index_fields = []

        for index in meta.indexes:
            for field in index.fields:
                index_fields.append(field)

        expected_fields = ['query', 'document', 'created_at', 'user']
        for field in expected_fields:
            assert field in index_fields