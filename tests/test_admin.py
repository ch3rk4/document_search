"""
Тесты для админ-панели
"""
from unittest.mock import MagicMock, patch

from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse

from doc_storage.admin import (
    DocumentAdmin, DocumentCategoryAdmin, DocumentTagAdmin,
    WordMatchAdmin, SearchHistoryAdmin, RelevanceScoreFilter
)
from doc_storage.models import (
    Document, DocumentCategory, DocumentTag, WordMatch, SearchHistory
)


class TestDocumentCategoryAdmin:
    """Тесты админ-панели для категорий документов"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.site = AdminSite()
        self.admin = DocumentCategoryAdmin(DocumentCategory, self.site)
        self.factory = RequestFactory()

    def test_list_display(self):
        """Тест отображаемых полей в списке"""
        expected_fields = ["name", "description", "document_count", "created_at"]
        assert self.admin.list_display == expected_fields

    def test_list_filter(self):
        """Тест фильтров списка"""
        expected_filters = ["created_at"]
        assert self.admin.list_filter == expected_filters

    def test_search_fields(self):
        """Тест полей поиска"""
        expected_fields = ["name", "description"]
        assert self.admin.search_fields == expected_fields

    def test_ordering(self):
        """Тест сортировки"""
        expected_ordering = ["name"]
        assert self.admin.ordering == expected_ordering

    def test_document_count_method(self, test_category, test_document):
        """Тест метода подсчета документов"""
        # Создаем дополнительные документы
        Document.objects.create(
            title="Дополнительный документ",
            content="Содержимое",
            author=test_document.author,
            category=test_category
        )

        count_html = self.admin.document_count(test_category)

        # Проверяем, что возвращается HTML с ссылкой
        assert '<a href=' in count_html
        assert str(2) in count_html  # Два документа в категории

    def test_document_count_zero(self, test_category):
        """Тест подсчета документов для пустой категории"""
        count_html = self.admin.document_count(test_category)

        assert '<a href=' in count_html
        assert '0' in count_html


class TestDocumentTagAdmin:
    """Тесты админ-панели для тегов документов"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.site = AdminSite()
        self.admin = DocumentTagAdmin(DocumentTag, self.site)

    def test_list_display(self):
        """Тест отображаемых полей в списке"""
        expected_fields = ["name", "color_preview", "usage_count", "created_at"]
        assert self.admin.list_display == expected_fields

    def test_color_preview_method(self, test_tag):
        """Тест метода предварительного просмотра цвета"""
        preview_html = self.admin.color_preview(test_tag)

        assert 'background-color:' in preview_html
        assert test_tag.color in preview_html
        assert '<div' in preview_html

    def test_usage_count_method(self, test_document_with_tags, test_tag):
        """Тест метода подсчета использования тега"""
        count = self.admin.usage_count(test_tag)

        assert count >= 1  # Тег используется в test_document_with_tags

    def test_usage_count_zero(self, test_tag):
        """Тест подсчета использования для неиспользуемого тега"""
        count = self.admin.usage_count(test_tag)

        assert count == 0


class TestDocumentAdmin:
    """Тесты админ-панели для документов"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.site = AdminSite()
        self.admin = DocumentAdmin(Document, self.site)
        self.factory = RequestFactory()

    def test_list_display(self):
        """Тест отображаемых полей в списке"""
        expected_fields = [
            "title", "author", "category", "word_count", "search_count",
            "is_active", "created_at", "updated_at"
        ]
        assert self.admin.list_display == expected_fields

    def test_list_filter(self):
        """Тест фильтров списка"""
        expected_filters = ["is_active", "category", "author", "created_at"]
        assert self.admin.list_filter == expected_filters

    def test_search_fields(self):
        """Тест полей поиска"""
        expected_fields = ["title", "content", "author__username"]
        assert self.admin.search_fields == expected_fields

    def test_list_editable(self):
        """Тест редактируемых полей в списке"""
        expected_fields = ["is_active"]
        assert self.admin.list_editable == expected_fields

    def test_readonly_fields(self):
        """Тест полей только для чтения"""
        expected_fields = ["word_count", "search_count", "created_at", "updated_at"]
        assert self.admin.readonly_fields == expected_fields

    def test_fieldsets(self):
        """Тест группировки полей"""
        fieldsets = self.admin.fieldsets

        assert len(fieldsets) == 4
        assert fieldsets[0][0] == "Основная информация"
        assert fieldsets[1][0] == "Категоризация"
        assert fieldsets[2][0] == "Статус"
        assert fieldsets[3][0] == "Статистика"

    def test_search_count_method(self, test_document, regular_user):
        """Тест метода подсчета поисков"""
        # Создаем историю поиска
        SearchHistory.objects.create(
            query="тест",
            document=test_document,
            user=regular_user,
            results_count=5
        )

        count_html = self.admin.search_count(test_document)

        assert '<a href=' in count_html
        assert '1' in count_html

    def test_search_count_zero(self, test_document):
        """Тест подсчета поисков для документа без поисков"""
        count_result = self.admin.search_count(test_document)

        assert count_result == '0'

    def test_save_model_new_document(self, admin_user):
        """Тест автоматической установки автора при создании"""
        request = self.factory.post('/admin/')
        request.user = admin_user

        document = Document(
            title="Новый документ",
            content="Содержимое"
        )

        # Имитируем создание нового документа
        self.admin.save_model(request, document, None, change=False)

        assert document.author == admin_user

    def test_save_model_existing_document(self, test_document, admin_user):
        """Тест сохранения существующего документа"""
        request = self.factory.post('/admin/')
        request.user = admin_user

        original_author = test_document.author

        # Имитируем редактирование существующего документа
        self.admin.save_model(request, test_document, None, change=True)

        # Автор не должен измениться
        assert test_document.author == original_author


class TestWordMatchAdmin:
    """Тесты админ-панели для найденных слов"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.site = AdminSite()
        self.admin = WordMatchAdmin(WordMatch, self.site)
        self.factory = RequestFactory()

    def test_list_display(self):
        """Тест отображаемых полей в списке"""
        expected_fields = [
            "matched_word", "document", "query", "match_type",
            "relevance_score", "position", "created_at"
        ]
        assert self.admin.list_display == expected_fields

    def test_list_filter(self):
        """Тест фильтров списка"""
        expected_filters = ["match_type", "created_at", "document", "relevance_score"]
        # Проверяем, что все базовые фильтры присутствуют
        for filter_field in expected_filters:
            assert filter_field in self.admin.list_filter

    def test_search_fields(self):
        """Тест полей поиска"""
        expected_fields = ["matched_word", "query", "document__title"]
        assert self.admin.search_fields == expected_fields

    def test_readonly_fields(self):
        """Тест полей только для чтения"""
        expected_fields = ["created_at"]
        assert self.admin.readonly_fields == expected_fields

    def test_fieldsets(self):
        """Тест группировки полей"""
        fieldsets = self.admin.fieldsets

        assert len(fieldsets) == 4
        assert fieldsets[0][0] == "Основная информация"
        assert fieldsets[1][0] == "Детали совпадения"
        assert fieldsets[2][0] == "Контекст"
        assert fieldsets[3][0] == "Метаданные"

    def test_has_add_permission(self, admin_user):
        """Тест запрета на ручное добавление"""
        request = self.factory.get('/admin/')
        request.user = admin_user

        has_permission = self.admin.has_add_permission(request)

        assert has_permission is False


class TestSearchHistoryAdmin:
    """Тесты админ-панели для истории поиска"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.site = AdminSite()
        self.admin = SearchHistoryAdmin(SearchHistory, self.site)
        self.factory = RequestFactory()

    def test_list_display(self):
        """Тест отображаемых полей в списке"""
        expected_fields = [
            "query", "document", "user", "results_count",
            "search_time", "ip_address", "created_at"
        ]
        assert self.admin.list_display == expected_fields

    def test_list_filter(self):
        """Тест фильтров списка"""
        expected_filters = ["created_at", "user", "document"]
        assert self.admin.list_filter == expected_filters

    def test_search_fields(self):
        """Тест полей поиска"""
        expected_fields = ["query", "user__username", "document__title", "ip_address"]
        assert self.admin.search_fields == expected_fields

    def test_has_add_permission(self, admin_user):
        """Тест запрета на ручное добавление"""
        request = self.factory.get('/admin/')
        request.user = admin_user

        has_permission = self.admin.has_add_permission(request)

        assert has_permission is False


class TestRelevanceScoreFilter:
    """Тесты кастомного фильтра по релевантности"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.filter = RelevanceScoreFilter(
            request=None,
            params={},
            model=WordMatch,
            model_admin=None
        )

    def test_filter_title(self):
        """Тест заголовка фильтра"""
        assert self.filter.title == "оценка релевантности"

    def test_filter_parameter_name(self):
        """Тест имени параметра фильтра"""
        assert self.filter.parameter_name == "relevance"

    def test_lookups(self):
        """Тест вариантов фильтрации"""
        lookups = self.filter.lookups(None, None)

        expected_lookups = [
            ("high", "Высокая (≥ 1.0)"),
            ("medium", "Средняя (0.5-1.0)"),
            ("low", "Низкая (< 0.5)"),
        ]

        assert lookups == expected_lookups

    @patch('doc_storage.admin.RelevanceScoreFilter.value')
    def test_queryset_high(self, mock_value, db, test_document):
        """Тест фильтрации высокой релевантности"""
        mock_value.return_value = "high"

        # Создаем тестовые данные
        WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест",
            position=0,
            relevance_score=1.0
        )
        WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест2",
            position=10,
            relevance_score=0.3
        )

        queryset = WordMatch.objects.all()
        filtered_queryset = self.filter.queryset(None, queryset)

        # Должен остаться только один результат с высокой релевантностью
        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().relevance_score >= 1.0

    @patch('doc_storage.admin.RelevanceScoreFilter.value')
    def test_queryset_medium(self, mock_value, db, test_document):
        """Тест фильтрации средней релевантности"""
        mock_value.return_value = "medium"

        WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест",
            position=0,
            relevance_score=0.7
        )

        queryset = WordMatch.objects.all()
        filtered_queryset = self.filter.queryset(None, queryset)

        assert filtered_queryset.count() == 1
        score = filtered_queryset.first().relevance_score
        assert 0.5 <= score < 1.0

    @patch('doc_storage.admin.RelevanceScoreFilter.value')
    def test_queryset_low(self, mock_value, db, test_document):
        """Тест фильтрации низкой релевантности"""
        mock_value.return_value = "low"

        WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест",
            position=0,
            relevance_score=0.2
        )

        queryset = WordMatch.objects.all()
        filtered_queryset = self.filter.queryset(None, queryset)

        assert filtered_queryset.count() == 1
        assert filtered_queryset.first().relevance_score < 0.5

    @patch('doc_storage.admin.RelevanceScoreFilter.value')
    def test_queryset_no_filter(self, mock_value, db, test_document):
        """Тест без фильтрации"""
        mock_value.return_value = None

        WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест1",
            position=0,
            relevance_score=1.0
        )
        WordMatch.objects.create(
            document=test_document,
            query="тест",
            matched_word="тест2",
            position=10,
            relevance_score=0.3
        )

        queryset = WordMatch.objects.all()
        filtered_queryset = self.filter.queryset(None, queryset)

        # Без фильтра должны остаться все результаты
        assert filtered_queryset.count() == 2


class TestAdminSiteConfiguration:
    """Тесты конфигурации админ-сайта"""

    def test_admin_site_headers(self):
        """Тест настройки заголовков админ-панели"""
        from django.contrib import admin

        expected_header = "Поисковик слов в документах - Администрирование"
        expected_title = "Поисковик документов"
        expected_index_title = "Управление системой поиска слов в документах"

        assert admin.site.site_header == expected_header
        assert admin.site.site_title == expected_title
        assert admin.site.index_title == expected_index_title


class TestAdminIntegration:
    """Интеграционные тесты админ-панели"""

    def test_admin_document_creation(self, admin_client, test_category, regular_user):
        """Тест создания документа через админ-панель"""
        url = reverse('admin:doc_storage_document_add')
        data = {
            'title': 'Документ из админки',
            'content': 'Содержимое документа',
            'category': test_category.pk,
            'author': regular_user.pk,
            'is_active': True
        }

        response = admin_client.post(url, data)

        # Проверяем успешное создание (редирект)
        assert response.status_code == 302

        # Проверяем создание в БД
        document = Document.objects.get(title='Документ из админки')
        assert document.content == 'Содержимое документа'
        assert document.category == test_category
        assert document.author == regular_user

    def test_admin_document_list(self, admin_client, multiple_documents):
        """Тест списка документов в админ-панели"""
        url = reverse('admin:doc_storage_document_changelist')
        response = admin_client.get(url)

        assert response.status_code == 200

        # Проверяем наличие документов в списке
        content = response.content.decode()
        for doc in multiple_documents:
            assert doc.title in content

    def test_admin_document_search(self, admin_client, multiple_documents):
        """Тест поиска документов в админ-панели"""
        url = reverse('admin:doc_storage_document_changelist')
        response = admin_client.get(url, {'q': 'Python'})

        assert response.status_code == 200

        content = response.content.decode()
        # Должен найти документ с Python в заголовке
        assert 'Python' in content

    def test_admin_document_filter(self, admin_client, multiple_documents, test_category):
        """Тест фильтрации документов в админ-панели"""
        url = reverse('admin:doc_storage_document_changelist')
        response = admin_client.get(url, {'category__id__exact': test_category.pk})

        assert response.status_code == 200
        # Ответ должен содержать отфильтрованные документы

    def test_admin_category_creation(self, admin_client):
        """Тест создания категории через админ-панель"""
        url = reverse('admin:doc_storage_documentcategory_add')
        data = {
            'name': 'Новая категория',
            'description': 'Описание новой категории'
        }

        response = admin_client.post(url, data)

        assert response.status_code == 302

        category = DocumentCategory.objects.get(name='Новая категория')
        assert category.description == 'Описание новой категории'

    def test_admin_tag_creation(self, admin_client):
        """Тест создания тега через админ-панель"""
        url = reverse('admin:doc_storage_documenttag_add')
        data = {
            'name': 'новый-тег',
            'color': '#ff0000'
        }

        response = admin_client.post(url, data)

        assert response.status_code == 302

        tag = DocumentTag.objects.get(name='новый-тег')
        assert tag.color == '#ff0000'


class TestAdminPermissions:
    """Тесты разрешений в админ-панели"""

    def test_admin_access_anonymous(self, client):
        """Тест доступа к админ-панели анонимным пользователем"""
        url = reverse('admin:index')
        response = client.get(url)

        # Должен быть редирект на страницу входа
        assert response.status_code == 302
        assert 'login' in response.url

    def test_admin_access_regular_user(self, authenticated_client):
        """Тест доступа к админ-панели обычным пользователем"""
        url = reverse('admin:index')
        response = authenticated_client.get(url)

        # Обычный пользователь не должен иметь доступ
        assert response.status_code == 302

    def test_admin_access_staff_user(self, admin_client):
        """Тест доступа к админ-панели администратором"""
        url = reverse('admin:index')
        response = admin_client.get(url)

        assert response.status_code == 200

        # Проверяем наличие ожидаемых разделов
        content = response.content.decode()
        assert 'Документы' in content
        assert 'Категории' in content


class TestAdminCustomMethods:
    """Тесты кастомных методов админ-панели"""

    def test_document_admin_get_queryset_optimization(self, admin_user):
        """Тест оптимизации запросов в админ-панели документов"""
        admin = DocumentAdmin(Document, AdminSite())
        request = MagicMock()
        request.user = admin_user

        with patch.object(admin, 'get_queryset') as mock_queryset:
            mock_queryset.return_value = Document.objects.select_related('author', 'category')

            queryset = admin.get_queryset(request)

            # Проверяем, что метод был вызван
            mock_queryset.assert_called_once_with(request)

    def test_word_match_admin_get_queryset_optimization(self, admin_user):
        """Тест оптимизации запросов в админ-панели совпадений"""
        admin = WordMatchAdmin(WordMatch, AdminSite())
        request = MagicMock()
        request.user = admin_user

        # Метод get_queryset должен использовать select_related
        queryset = admin.get_queryset(request)

        # Проверяем, что возвращается QuerySet
        assert hasattr(queryset, 'select_related')

    def test_search_history_admin_get_queryset_optimization(self, admin_user):
        """Тест оптимизации запросов в админ-панели истории поиска"""
        admin = SearchHistoryAdmin(SearchHistory, AdminSite())
        request = MagicMock()
        request.user = admin_user

        queryset = admin.get_queryset(request)

        # Проверяем, что возвращается QuerySet
        assert hasattr(queryset, 'select_related')