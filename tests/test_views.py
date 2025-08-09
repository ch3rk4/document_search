"""
Тесты для веб-представлений (views)
"""
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.urls import reverse

from doc_storage.models import Document, SearchHistory
from doc_storage.views import get_anonymous_user


class TestDocumentListView:
    """Тесты представления списка документов"""

    def test_document_list_anonymous(self, client, multiple_documents):
        """Тест доступа к списку документов анонимным пользователем"""
        url = reverse("doc_storage:document_list")
        response = client.get(url)

        assert response.status_code == 200
        assert "documents" in response.context
        assert len(response.context["documents"]) == 3

        # Проверяем шаблон
        assert "doc_storage/document_list.html" in [t.name for t in response.templates]

    def test_document_list_authenticated(self, authenticated_client, multiple_documents):
        """Тест доступа к списку документов аутентифицированным пользователем"""
        url = reverse("doc_storage:document_list")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert "documents" in response.context

    def test_document_list_search(self, client, multiple_documents):
        """Тест поиска в списке документов"""
        url = reverse("doc_storage:document_list")
        response = client.get(url, {"search": "Python"})

        assert response.status_code == 200
        documents = response.context["documents"]

        # Должен найти документ с Python в заголовке или содержимом
        found = any("Python" in doc.title or "Python" in doc.content for doc in documents)
        assert found

    def test_document_list_category_filter(self, client, multiple_documents, test_category):
        """Тест фильтрации по категории"""
        url = reverse("doc_storage:document_list")
        response = client.get(url, {"category": test_category.pk})

        assert response.status_code == 200
        documents = response.context["documents"]

        # Все документы должны быть из выбранной категории
        for doc in documents:
            assert doc.category == test_category

    def test_document_list_pagination(self, client, db, regular_user, test_category):
        """Тест пагинации списка документов"""
        # Создаем много документов
        for i in range(25):
            Document.objects.create(
                title=f"Документ {i}", content=f"Содержимое {i}", author=regular_user, category=test_category
            )

        url = reverse("doc_storage:document_list")
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["is_paginated"] is True
        assert len(response.context["documents"]) == 20  # Размер страницы

    def test_document_list_context(self, client, multiple_documents, test_category):
        """Тест контекста представления"""
        url = reverse("doc_storage:document_list")
        response = client.get(url)

        assert response.status_code == 200

        # Проверяем наличие необходимых элементов контекста
        assert "categories" in response.context
        assert "search_query" in response.context
        assert "selected_category" in response.context

        assert test_category in response.context["categories"]


class TestDocumentDetailView:
    """Тесты представления детального просмотра документа"""

    def test_document_detail_anonymous(self, client, test_document):
        """Тест просмотра документа анонимным пользователем"""
        url = reverse("doc_storage:document_detail", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["document"] == test_document
        assert "doc_storage/document_detail.html" in [t.name for t in response.templates]

    def test_document_detail_authenticated(self, authenticated_client, test_document):
        """Тест просмотра документа аутентифицированным пользователем"""
        url = reverse("doc_storage:document_detail", kwargs={"pk": test_document.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.context["document"] == test_document

    def test_document_detail_inactive(self, client, test_document):
        """Тест просмотра неактивного документа"""
        test_document.is_active = False
        test_document.save()

        url = reverse("doc_storage:document_detail", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 404

    def test_document_detail_nonexistent(self, client):
        """Тест просмотра несуществующего документа"""
        url = reverse("doc_storage:document_detail", kwargs={"pk": 99999})
        response = client.get(url)

        assert response.status_code == 404

    def test_document_detail_context(self, client, test_document_with_tags, multiple_documents):
        """Тест контекста детального представления"""
        url = reverse("doc_storage:document_detail", kwargs={"pk": test_document_with_tags.pk})
        response = client.get(url)

        assert response.status_code == 200

        # Проверяем контекст
        assert "similar_documents" in response.context
        assert "document_tags" in response.context
        assert "recent_searches" in response.context


class TestWordSearchView:
    """Тесты представления поиска слов"""

    def test_word_search_get(self, client, test_document):
        """Тест GET запроса к поиску слов"""
        url = reverse("doc_storage:word_search", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["document"] == test_document
        assert "doc_storage/word_search.html" in [t.name for t in response.templates]

    @patch("search_service.algorithms.WordSearchService.search_words_in_document")
    def test_word_search_with_query(self, mock_search, client, test_document):
        """Тест поиска слов с запросом"""
        # Настраиваем мок
        mock_search.return_value = ([], 0.1)

        url = reverse("doc_storage:word_search", kwargs={"pk": test_document.pk})
        response = client.get(url, {"q": "тест", "type": "exact"})

        assert response.status_code == 200
        assert response.context["query"] == "тест"
        assert response.context["search_type"] == "exact"
        assert "search_time" in response.context
        assert "total_matches" in response.context

    def test_word_search_without_query(self, client, test_document):
        """Тест поиска слов без запроса"""
        url = reverse("doc_storage:word_search", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 200
        assert response.context["query"] == ""
        assert "word_matches" not in response.context

    def test_word_search_inactive_document(self, client, test_document):
        """Тест поиска в неактивном документе"""
        test_document.is_active = False
        test_document.save()

        url = reverse("doc_storage:word_search", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 404


class TestUserAuthViews:
    """Тесты представлений аутентификации"""

    def test_registration_view_get(self, client):
        """Тест GET запроса к регистрации"""
        url = reverse("doc_storage:user_register")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert "doc_storage/auth/register.html" in [t.name for t in response.templates]

    def test_registration_view_authenticated_redirect(self, authenticated_client):
        """Тест редиректа аутентифицированного пользователя с регистрации"""
        url = reverse("doc_storage:user_register")
        response = authenticated_client.get(url)

        assert response.status_code == 302
        assert response.url == reverse("doc_storage:document_list")

    def test_registration_view_post_valid(self, client, db):
        """Тест успешной регистрации"""
        url = reverse("doc_storage:user_register")
        data = {
            "username": "newuser",
            "first_name": "Test",
            "last_name": "User",
            "email": "new@test.com",
            "password1": "testpass123",
            "password2": "testpass123",
        }
        response = client.post(url, data)

        assert response.status_code == 302
        assert response.url == reverse("doc_storage:document_list")

        # Проверяем создание пользователя
        assert User.objects.filter(username="newuser").exists()

    def test_registration_view_post_invalid(self, client, db):
        """Тест регистрации с невалидными данными"""
        url = reverse("doc_storage:user_register")
        data = {"username": "newuser", "password1": "testpass123", "password2": "differentpass"}  # Не совпадают пароли
        response = client.post(url, data)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors

    def test_login_view_get(self, client):
        """Тест GET запроса к входу"""
        url = reverse("doc_storage:user_login")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert "doc_storage/auth/login.html" in [t.name for t in response.templates]

    def test_login_view_post_valid(self, client, regular_user):
        """Тест успешного входа"""
        url = reverse("doc_storage:user_login")
        data = {"username": regular_user.username, "password": "testpass123"}
        response = client.post(url, data)

        assert response.status_code == 302
        # Проверяем, что пользователь аутентифицирован
        assert "_auth_user_id" in client.session

    def test_logout_view(self, authenticated_client):
        """Тест выхода"""
        url = reverse("doc_storage:user_logout")
        response = authenticated_client.post(url)

        assert response.status_code == 302
        assert response.url == reverse("doc_storage:document_list")

    def test_profile_view_anonymous(self, client):
        """Тест доступа к профилю анонимным пользователем"""
        url = reverse("doc_storage:user_profile")
        response = client.get(url)

        assert response.status_code == 302  # Редирект на логин

    def test_profile_view_authenticated(self, authenticated_client, regular_user):
        """Тест просмотра профиля"""
        url = reverse("doc_storage:user_profile")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.context["object"] == regular_user
        assert "doc_storage/auth/profile.html" in [t.name for t in response.templates]


class TestDocumentUploadView:
    """Тесты представления загрузки документа"""

    def test_upload_view_get(self, client):
        """Тест GET запроса к загрузке"""
        url = reverse("doc_storage:document_upload")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert "supported_formats" in response.context
        assert "max_file_size_mb" in response.context

    @patch("doc_storage.file_service.DocumentFileService.create_document_from_file")
    def test_upload_view_post_authenticated(self, mock_create, authenticated_client, sample_text_file, test_category):
        """Тест загрузки файла аутентифицированным пользователем"""
        # Настраиваем мок
        mock_document = MagicMock()
        mock_document.pk = 1
        mock_document.title = "Тестовый документ"
        mock_create.return_value = (mock_document, None)

        url = reverse("doc_storage:document_upload")
        data = {"file": sample_text_file, "title": "Загруженный документ", "category": test_category.pk}
        response = authenticated_client.post(url, data)

        assert response.status_code == 302
        mock_create.assert_called_once()

    @patch("doc_storage.file_service.DocumentFileService.create_document_from_file")
    def test_upload_view_post_anonymous(self, mock_create, client, sample_text_file):
        """Тест загрузки файла анонимным пользователем"""
        mock_document = MagicMock()
        mock_document.pk = 1
        mock_document.title = "Анонимный документ"
        mock_create.return_value = (mock_document, None)

        url = reverse("doc_storage:document_upload")
        data = {"file": sample_text_file, "title": "Анонимный документ"}
        response = client.post(url, data)

        assert response.status_code == 302
        mock_create.assert_called_once()

    @patch("doc_storage.file_service.DocumentFileService.create_document_from_file")
    def test_upload_view_post_error(self, mock_create, client, sample_text_file):
        """Тест загрузки с ошибкой"""
        # Настраиваем мок для возврата ошибки
        mock_create.return_value = (None, "Ошибка загрузки файла")

        url = reverse("doc_storage:document_upload")
        data = {"file": sample_text_file, "title": "Документ с ошибкой"}
        response = client.post(url, data)

        assert response.status_code == 200

        # Проверяем сообщение об ошибке
        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "ошибка" in str(messages[0]).lower()

    def test_upload_view_invalid_form(self, client, unsupported_file):
        """Тест загрузки с невалидной формой"""
        url = reverse("doc_storage:document_upload")
        data = {"file": unsupported_file, "title": "Неподдерживаемый файл"}
        response = client.post(url, data)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors


class TestDocumentCreateView:
    """Тесты представления создания документа"""

    def test_create_view_get(self, client):
        """Тест GET запроса к созданию"""
        url = reverse("doc_storage:document_create")
        response = client.get(url)

        assert response.status_code == 200
        assert "form" in response.context
        assert "doc_storage/document_create.html" in [t.name for t in response.templates]

    def test_create_view_post_authenticated(self, authenticated_client, test_category, test_tag, regular_user):
        """Тест создания документа аутентифицированным пользователем"""
        url = reverse("doc_storage:document_create")
        data = {
            "title": "Новый документ",
            "content": "Содержимое нового документа",
            "category": test_category.pk,
            "tags": [test_tag.pk],
        }
        response = authenticated_client.post(url, data)

        assert response.status_code == 302

        # Проверяем создание документа
        document = Document.objects.get(title="Новый документ")
        assert document.author == regular_user
        assert document.category == test_category

    def test_create_view_post_anonymous(self, client, anonymous_user):
        """Тест создания документа анонимным пользователем"""
        url = reverse("doc_storage:document_create")
        data = {"title": "Анонимный документ", "content": "Содержимое анонимного документа"}
        response = client.post(url, data)

        assert response.status_code == 302

        # Проверяем создание документа
        document = Document.objects.get(title="Анонимный документ")
        assert document.author.username == "anonymous"

    def test_create_view_invalid_form(self, client):
        """Тест создания с невалидной формой"""
        url = reverse("doc_storage:document_create")
        data = {}  # Отсутствуют обязательные поля
        response = client.post(url, data)

        assert response.status_code == 200
        assert "form" in response.context
        assert response.context["form"].errors


class TestDocumentEditView:
    """Тесты представления редактирования документа"""

    def test_edit_view_get_owner(self, authenticated_client, test_document, regular_user):
        """Тест GET запроса к редактированию владельцем"""
        # Устанавливаем правильного автора
        test_document.author = regular_user
        test_document.save()

        url = reverse("doc_storage:document_edit", kwargs={"pk": test_document.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert response.context["object"] == test_document
        assert "doc_storage/document_edit.html" in [t.name for t in response.templates]

    def test_edit_view_get_not_owner(self, authenticated_client, test_document, admin_user):
        """Тест GET запроса к редактированию не владельцем"""
        # Устанавливаем другого автора
        test_document.author = admin_user
        test_document.save()

        url = reverse("doc_storage:document_edit", kwargs={"pk": test_document.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 404

    def test_edit_view_post_owner(self, authenticated_client, test_document, regular_user):
        """Тест POST запроса к редактированию владельцем"""
        test_document.author = regular_user
        test_document.save()

        url = reverse("doc_storage:document_edit", kwargs={"pk": test_document.pk})
        data = {"title": "Обновленный заголовок", "content": test_document.content, "is_active": True}
        response = authenticated_client.post(url, data)

        assert response.status_code == 302

        # Проверяем обновление
        test_document.refresh_from_db()
        assert test_document.title == "Обновленный заголовок"

    def test_edit_view_anonymous(self, client, test_document):
        """Тест редактирования анонимным пользователем"""
        url = reverse("doc_storage:document_edit", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 302  # Редирект на логин


class TestSearchHistoryView:
    """Тесты представления истории поиска"""

    def test_search_history_anonymous(self, client):
        """Тест доступа к истории поиска анонимным пользователем"""
        url = reverse("doc_storage:search_history")
        response = client.get(url)

        assert response.status_code == 302  # Редирект на логин

    def test_search_history_authenticated(self, authenticated_client, regular_user, test_document):
        """Тест просмотра истории поиска"""
        # Создаем историю поиска
        SearchHistory.objects.create(query="тест", document=test_document, user=regular_user, results_count=5)

        url = reverse("doc_storage:search_history")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        assert "search_history" in response.context
        assert len(response.context["search_history"]) >= 1

    def test_search_history_own_only(self, authenticated_client, regular_user, admin_user, test_document):
        """Тест отображения только своей истории поиска"""
        # Создаем историю для разных пользователей
        SearchHistory.objects.create(query="мой поиск", document=test_document, user=regular_user)
        SearchHistory.objects.create(query="чужой поиск", document=test_document, user=admin_user)

        url = reverse("doc_storage:search_history")
        response = authenticated_client.get(url)

        assert response.status_code == 200
        search_history = response.context["search_history"]

        # Должен видеть только свои поиски
        queries = [h.query for h in search_history]
        assert "мой поиск" in queries
        assert "чужой поиск" not in queries


class TestUtilityFunctions:
    """Тесты вспомогательных функций"""

    def test_get_anonymous_user_exists(self, db, anonymous_user):
        """Тест получения существующего анонимного пользователя"""
        user = get_anonymous_user()

        assert user.username == "anonymous"
        assert user == anonymous_user

    def test_get_anonymous_user_not_exists(self, db):
        """Тест создания анонимного пользователя"""
        # Убеждаемся, что анонимного пользователя нет
        User.objects.filter(username="anonymous").delete()

        user = get_anonymous_user()

        assert user.username == "anonymous"
        assert user.first_name == "Анонимный"
        assert user.last_name == "Пользователь"
        assert not user.has_usable_password()


class TestTemplateResponses:
    """Тесты ответов шаблонов"""

    def test_document_list_template_context(self, client, multiple_documents):
        """Тест контекста шаблона списка документов"""
        url = reverse("doc_storage:document_list")
        response = client.get(url)

        assert response.status_code == 200

        # Проверяем, что все необходимые переменные доступны в шаблоне
        content = response.content.decode()
        assert "Документы" in content
        assert "Python" in content  # Из тестовых документов

    def test_document_detail_template_context(self, client, test_document):
        """Тест контекста шаблона детального просмотра"""
        url = reverse("doc_storage:document_detail", kwargs={"pk": test_document.pk})
        response = client.get(url)

        assert response.status_code == 200

        content = response.content.decode()
        assert test_document.title in content
        assert test_document.content in content

    def test_word_search_template_context(self, client, test_document):
        """Тест контекста шаблона поиска слов"""
        url = reverse("doc_storage:word_search", kwargs={"pk": test_document.pk})
        response = client.get(url, {"q": "тест"})

        assert response.status_code == 200

        content = response.content.decode()
        assert "Поиск слов" in content
        assert test_document.title in content


class TestViewPermissions:
    """Тесты разрешений представлений"""

    def test_document_edit_permission_owner(self, authenticated_client, test_document, regular_user):
        """Тест разрешения редактирования для владельца"""
        test_document.author = regular_user
        test_document.save()

        url = reverse("doc_storage:document_edit", kwargs={"pk": test_document.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 200

    def test_document_edit_permission_not_owner(self, authenticated_client, test_document, admin_user):
        """Тест запрета редактирования для не владельца"""
        test_document.author = admin_user
        test_document.save()

        url = reverse("doc_storage:document_edit", kwargs={"pk": test_document.pk})
        response = authenticated_client.get(url)

        assert response.status_code == 404

    def test_profile_permission_authenticated_only(self, client):
        """Тест доступа к профилю только для аутентифицированных"""
        url = reverse("doc_storage:user_profile")
        response = client.get(url)

        assert response.status_code == 302
        assert "/login/" in response.url

    def test_search_history_permission_authenticated_only(self, client):
        """Тест доступа к истории поиска только для аутентифицированных"""
        url = reverse("doc_storage:search_history")
        response = client.get(url)

        assert response.status_code == 302
        assert "/login/" in response.url


class TestViewMessages:
    """Тесты сообщений в представлениях"""

    def test_registration_success_message(self, client, db):
        """Тест сообщения об успешной регистрации"""
        url = reverse("doc_storage:user_register")
        data = {
            "username": "newuser",
            "first_name": "Test",
            "last_name": "User",
            "email": "new@test.com",
            "password1": "testpass123",
            "password2": "testpass123",
        }
        response = client.post(url, data, follow=True)

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "добро пожаловать" in str(messages[0]).lower()

    def test_login_success_message(self, client, regular_user):
        """Тест сообщения об успешном входе"""
        url = reverse("doc_storage:user_login")
        data = {"username": regular_user.username, "password": "testpass123"}
        response = client.post(url, data, follow=True)

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "добро пожаловать" in str(messages[0]).lower()

    def test_logout_success_message(self, authenticated_client):
        """Тест сообщения об успешном выходе"""
        url = reverse("doc_storage:user_logout")
        response = authenticated_client.get(url, follow=True)

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "вышли" in str(messages[0]).lower()

    @patch("doc_storage.file_service.DocumentFileService.create_document_from_file")
    def test_upload_success_message(self, mock_create, authenticated_client, sample_text_file):
        """Тест сообщения об успешной загрузке"""
        mock_document = MagicMock()
        mock_document.pk = 1
        mock_document.title = "Загруженный документ"
        mock_create.return_value = (mock_document, None)

        url = reverse("doc_storage:document_upload")
        data = {"file": sample_text_file, "title": "Загруженный документ"}
        response = authenticated_client.post(url, data, follow=True)

        messages = list(get_messages(response.wsgi_request))
        assert len(messages) > 0
        assert "успешно создан" in str(messages[0]).lower()
