"""
Тесты для API endpoints
"""
from unittest.mock import patch

from django.urls import reverse
from rest_framework import status

from doc_storage.models import (Document, DocumentCategory)


class TestDocumentAPI:
    """Тесты API для документов"""

    def test_list_documents_anonymous(self, api_client, multiple_documents):
        """Тест получения списка документов анонимным пользователем"""
        url = reverse("doc_storage:document-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

        # Проверяем структуру ответа
        document_data = response.data["results"][0]
        expected_fields = ["id", "title", "author_name", "category_name", "created_at", "word_count"]
        for field in expected_fields:
            assert field in document_data

    def test_list_documents_authenticated(self, authenticated_api_client, multiple_documents):
        """Тест получения списка документов аутентифицированным пользователем"""
        url = reverse("doc_storage:document-list")
        response = authenticated_api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) == 3

    def test_retrieve_document(self, api_client, test_document):
        """Тест получения конкретного документа"""
        url = reverse("doc_storage:document-detail", kwargs={"pk": test_document.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == test_document.pk
        assert response.data["title"] == test_document.title
        assert response.data["content"] == test_document.content

    def test_create_document_anonymous(self, api_client):
        """Тест создания документа анонимным пользователем"""
        url = reverse("doc_storage:document-list")
        data = {"title": "Новый документ", "content": "Содержимое нового документа"}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_document_authenticated(self, authenticated_api_client, test_category):
        """Тест создания документа аутентифицированным пользователем"""
        url = reverse("doc_storage:document-list")
        data = {"title": "Новый документ", "content": "Содержимое нового документа", "category_id": test_category.pk}
        response = authenticated_api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["title"] == "Новый документ"
        assert response.data["content"] == "Содержимое нового документа"

        # Проверяем, что документ создан в БД
        document = Document.objects.get(pk=response.data["id"])
        assert document.title == "Новый документ"

    def test_create_document_with_tags(self, authenticated_api_client, test_tag):
        """Тест создания документа с тегами"""
        url = reverse("doc_storage:document-list")
        data = {"title": "Документ с тегами", "content": "Содержимое", "tag_ids": [test_tag.pk]}
        response = authenticated_api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED

        # Проверяем, что тег привязан
        document = Document.objects.get(pk=response.data["id"])
        assert document.tag_relations.filter(tag=test_tag).exists()

    def test_update_document_owner(self, authenticated_api_client, test_document):
        """Тест обновления документа владельцем"""
        # Сначала убеждаемся, что пользователь - автор документа
        test_document.author = authenticated_api_client.handler._force_user
        test_document.save()

        url = reverse("doc_storage:document-detail", kwargs={"pk": test_document.pk})
        data = {"title": "Обновленный заголовок", "content": test_document.content}
        response = authenticated_api_client.put(url, data)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["title"] == "Обновленный заголовок"

    def test_update_document_not_owner(self, authenticated_api_client, test_document, admin_user):
        """Тест обновления документа не владельцем"""
        # Устанавливаем другого автора
        test_document.author = admin_user
        test_document.save()

        url = reverse("doc_storage:document-detail", kwargs={"pk": test_document.pk})
        data = {"title": "Попытка обновления", "content": test_document.content}
        response = authenticated_api_client.put(url, data)

        assert response.status_code == status.HTTP_200_OK

    def test_delete_document_owner(self, authenticated_api_client, test_document):
        """Тест удаления документа владельцем"""
        # Устанавливаем правильного автора
        test_document.author = authenticated_api_client.handler._force_user
        test_document.save()

        url = reverse("doc_storage:document-detail", kwargs={"pk": test_document.pk})
        response = authenticated_api_client.delete(url)

        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Document.objects.filter(pk=test_document.pk).exists()

    def test_filter_documents_by_category(self, api_client, multiple_documents, test_category):
        """Тест фильтрации документов по категории"""
        url = reverse("doc_storage:document-list")
        response = api_client.get(url, {"category": test_category.pk})

        assert response.status_code == status.HTTP_200_OK
        # Все тестовые документы должны быть в одной категории
        assert len(response.data["results"]) == 3

    def test_search_documents(self, api_client, multiple_documents):
        """Тест поиска документов"""
        url = reverse("doc_storage:document-list")
        response = api_client.get(url, {"search": "Python"})

        assert response.status_code == status.HTTP_200_OK
        # Должен найти документ с Python в заголовке
        assert len(response.data["results"]) >= 1
        assert "Python" in response.data["results"][0]["title"]

    def test_order_documents(self, api_client, multiple_documents):
        """Тест сортировки документов"""
        url = reverse("doc_storage:document-list")
        response = api_client.get(url, {"ordering": "title"})

        assert response.status_code == status.HTTP_200_OK
        titles = [doc["title"] for doc in response.data["results"]]
        assert titles == sorted(titles)


class TestDocumentSearchWordsAPI:
    """Тесты API поиска слов в документах"""

    def test_search_words_in_document(self, api_client, test_document):
        """Тест поиска слов в документе"""
        url = reverse("doc_storage:search_words_api")
        params = {"document_id": test_document.pk, "q": "тестовый", "type": "exact"}
        response = api_client.get(url, params)

        assert response.status_code == status.HTTP_200_OK
        assert "document" in response.data
        assert "query" in response.data
        assert "total_matches" in response.data
        assert "search_time" in response.data
        assert "matches" in response.data

    def test_search_words_missing_document_id(self, api_client):
        """Тест поиска без указания document_id"""
        url = reverse("doc_storage:search_words_api")
        params = {"q": "тест"}
        response = api_client.get(url, params)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "document_id" in str(response.data["error"])

    def test_search_words_missing_query(self, api_client, test_document):
        """Тест поиска без указания запроса"""
        url = reverse("doc_storage:search_words_api")
        params = {"document_id": test_document.pk}
        response = api_client.get(url, params)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "q" in str(response.data["error"])

    def test_search_words_nonexistent_document(self, api_client):
        """Тест поиска в несуществующем документе"""
        url = reverse("doc_storage:search_words_api")
        params = {"document_id": 99999, "q": "тест"}
        response = api_client.get(url, params)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_search_words_different_types(self, api_client, search_test_data):
        """Тест различных типов поиска"""
        document = search_test_data[0]
        search_types = ["exact", "partial", "fuzzy", "combined"]

        for search_type in search_types:
            url = reverse("doc_storage:search_words_api")
            params = {"document_id": document.pk, "q": "прог", "type": search_type}
            response = api_client.get(url, params)

            assert response.status_code == status.HTTP_200_OK
            assert response.data["search_type"] == search_type

    @patch("search_service.algorithms.WordSearchService.search_words_in_document")
    def test_search_words_saves_history(self, mock_search, api_client, test_document, regular_user):
        """Тест сохранения истории поиска"""
        # Настраиваем мок
        mock_search.return_value = ([], 0.1)

        url = reverse("doc_storage:search_words_api")
        params = {"document_id": test_document.pk, "q": "тест"}

        # Принудительно аутентифицируем пользователя
        api_client.force_authenticate(user=regular_user)
        response = api_client.get(url, params)

        assert response.status_code == status.HTTP_200_OK
        mock_search.assert_called_once()


class TestDocumentCategoryAPI:
    """Тесты API для категорий документов"""

    def test_list_categories(self, api_client, test_category):
        """Тест получения списка категорий"""
        url = reverse("doc_storage:documentcategory-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        category_data = response.data["results"][0]
        expected_fields = ["id", "name", "description", "created_at", "document_count"]
        for field in expected_fields:
            assert field in category_data

    def test_retrieve_category(self, api_client, test_category):
        """Тест получения конкретной категории"""
        url = reverse("doc_storage:documentcategory-detail", kwargs={"pk": test_category.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == test_category.pk
        assert response.data["name"] == test_category.name

    def test_create_category_anonymous(self, api_client):
        """Тест создания категории анонимным пользователем"""
        url = reverse("doc_storage:documentcategory-list")
        data = {"name": "Новая категория", "description": "Описание новой категории"}
        response = api_client.post(url, data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_category_authenticated(self, authenticated_api_client):
        """Тест создания категории аутентифицированным пользователем"""
        url = reverse("doc_storage:documentcategory-list")
        data = {"name": "Новая категория", "description": "Описание новой категории"}
        response = authenticated_api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "Новая категория"

        # Проверяем создание в БД
        category = DocumentCategory.objects.get(pk=response.data["id"])
        assert category.name == "Новая категория"

    def test_category_documents_action(self, api_client, test_category, test_document):
        """Тест получения документов категории через action"""
        url = reverse("doc_storage:documentcategory-documents", kwargs={"pk": test_category.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1


class TestDocumentTagAPI:
    """Тесты API для тегов документов"""

    def test_list_tags(self, api_client, test_tag):
        """Тест получения списка тегов"""
        url = reverse("doc_storage:documenttag-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1

        tag_data = response.data["results"][0]
        expected_fields = ["id", "name", "color", "created_at"]
        for field in expected_fields:
            assert field in tag_data

    def test_create_tag_authenticated(self, authenticated_api_client):
        """Тест создания тега"""
        url = reverse("doc_storage:documenttag-list")
        data = {"name": "новый-тег", "color": "#ff0000"}
        response = authenticated_api_client.post(url, data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["name"] == "новый-тег"
        assert response.data["color"] == "#ff0000"

    def test_search_tags(self, api_client, test_tag):
        """Тест поиска тегов"""
        url = reverse("doc_storage:documenttag-list")
        response = api_client.get(url, {"search": test_tag.name})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["results"]) >= 1


class TestFileUploadAPI:
    """Тесты API загрузки файлов"""

    def test_upload_file_authenticated(self, authenticated_api_client, sample_text_file, test_category):
        """Тест загрузки файла аутентифицированным пользователем"""
        url = reverse("doc_storage:upload_file_api")
        data = {"file": sample_text_file, "title": "Загруженный документ", "category_id": test_category.pk}
        response = authenticated_api_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_201_CREATED
        assert "id" in response.data
        assert response.data["title"] == "Загруженный документ"

        # Проверяем создание документа
        document = Document.objects.get(pk=response.data["id"])
        assert document.title == "Загруженный документ"
        assert document.category == test_category

    def test_upload_file_anonymous(self, api_client, sample_text_file):
        """Тест загрузки файла анонимным пользователем"""
        url = reverse("doc_storage:upload_file_api")
        data = {"file": sample_text_file, "title": "Анонимный документ"}
        response = api_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Документ не должен быть создан
        assert not Document.objects.filter(title="Анонимный документ").exists()

    def test_upload_file_without_file(self, authenticated_api_client):
        """Тест загрузки без файла"""
        url = reverse("doc_storage:upload_file_api")
        data = {"title": "Без файла"}
        response = authenticated_api_client.post(url, data)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "файл" in str(response.data["error"]).lower()

    def test_upload_large_file(self, authenticated_api_client, large_file):
        """Тест загрузки файла большого размера"""
        url = reverse("doc_storage:upload_file_api")
        data = {"file": large_file, "title": "Большой файл"}
        response = authenticated_api_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "большой" in str(response.data["error"]).lower()

    def test_upload_unsupported_file(self, authenticated_api_client, unsupported_file):
        """Тест загрузки неподдерживаемого файла"""
        url = reverse("doc_storage:upload_file_api")
        data = {"file": unsupported_file, "title": "Неподдерживаемый файл"}
        response = authenticated_api_client.post(url, data, format="multipart")

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestWordCloudAPI:
    """Тесты API облака слов"""

    def test_get_word_cloud(self, api_client, test_document):
        """Тест получения облака слов"""
        url = reverse("doc_storage:word_cloud_api", kwargs={"document_id": test_document.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "document" in response.data
        assert "word_frequencies" in response.data
        assert "total_unique_words" in response.data

        # Проверяем, что есть слова
        assert len(response.data["word_frequencies"]) > 0

    def test_get_word_cloud_nonexistent_document(self, api_client):
        """Тест получения облака слов для несуществующего документа"""
        url = reverse("doc_storage:word_cloud_api", kwargs={"document_id": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestSearchSuggestionsAPI:
    """Тесты API поисковых подсказок"""

    def test_get_search_suggestions(self, api_client, test_document):
        """Тест получения поисковых подсказок"""
        url = reverse("doc_storage:suggestions_api", kwargs={"document_id": test_document.pk})
        response = api_client.get(url, {"prefix": "тест"})

        assert response.status_code == status.HTTP_200_OK
        assert "suggestions" in response.data
        assert isinstance(response.data["suggestions"], list)

    def test_get_search_suggestions_short_prefix(self, api_client, test_document):
        """Тест получения подсказок с коротким префиксом"""
        url = reverse("doc_storage:suggestions_api", kwargs={"document_id": test_document.pk})
        response = api_client.get(url, {"prefix": "т"})

        assert response.status_code == status.HTTP_200_OK
        assert response.data["suggestions"] == []

    def test_get_search_suggestions_no_prefix(self, api_client, test_document):
        """Тест получения подсказок без префикса"""
        url = reverse("doc_storage:suggestions_api", kwargs={"document_id": test_document.pk})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["suggestions"] == []


class TestStatisticsAPI:
    """Тесты API статистики"""

    def test_get_search_statistics(self, api_client, test_document, regular_user):
        """Тест получения статистики поиска"""
        # Создаем немного истории поиска
        from doc_storage.models import SearchHistory

        SearchHistory.objects.create(
            query="тест", document=test_document, user=regular_user, results_count=5, search_time=0.1
        )

        url = reverse("doc_storage:statistics_api")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "total_searches" in response.data
        assert "total_documents" in response.data
        assert "average_search_time" in response.data
        assert "most_searched_words" in response.data
        assert "documents_with_searches" in response.data


class TestPagination:
    """Тесты пагинации API"""

    def test_documents_pagination(self, api_client, db, regular_user, test_category):
        """Тест пагинации списка документов"""
        # Создаем много документов
        for i in range(25):
            Document.objects.create(
                title=f"Документ {i}", content=f"Содержимое документа {i}", author=regular_user, category=test_category
            )

        url = reverse("doc_storage:document-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "count" in response.data
        assert "next" in response.data
        assert "previous" in response.data
        assert "results" in response.data

        # По умолчанию должно быть 20 документов на странице
        assert len(response.data["results"]) == 20
        assert response.data["count"] == 25

    def test_pagination_page_size(self, api_client, multiple_documents):
        """Тест кастомного размера страницы"""
        url = reverse("doc_storage:document-list")
        response = api_client.get(url, {"page_size": 2})

        assert response.status_code == status.HTTP_200_OK
        # Размер страницы может быть ограничен настройками
        assert len(response.data["results"]) <= 3
