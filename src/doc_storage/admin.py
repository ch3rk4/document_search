from typing import Any

from django.contrib import admin
from django.db.models.query import QuerySet
from django.http import HttpRequest
from django.urls import reverse
from django.utils.html import format_html

from .models import (Document, DocumentCategory, DocumentTag,
                     DocumentTagRelation, SearchHistory, WordMatch)


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin[DocumentCategory]):
    """Админ-панель для категорий документов"""

    list_display = ["name", "description", "document_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name", "description"]
    ordering = ["name"]

    def document_count(self, obj: DocumentCategory) -> str:
        """Подсчет количества документов в категории"""
        count = Document.objects.filter(category=obj, is_active=True).count()
        url = reverse("admin:doc_storage_document_changelist") + f"?category__id__exact={obj.id}"
        return format_html('<a href="{}">{}</a>', url, count)

    document_count.short_description = "Количество документов"  # type: ignore[attr-defined]


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin[DocumentTag]):
    """Админ-панель для тегов документов"""

    list_display = ["name", "color_preview", "usage_count", "created_at"]
    list_filter = ["created_at"]
    search_fields = ["name"]
    ordering = ["name"]

    def color_preview(self, obj: DocumentTag) -> str:
        """Превью цвета тега"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>', obj.color
        )

    color_preview.short_description = "Цвет"  # type: ignore[attr-defined]

    def usage_count(self, obj: DocumentTag) -> int:
        """Подсчет использования тега"""
        return obj.document_relations.count()

    usage_count.short_description = "Использований"  # type: ignore[attr-defined]


class DocumentTagRelationInline(admin.TabularInline[DocumentTagRelation, Document]):
    """Inline для связей документов и тегов"""

    model = DocumentTagRelation
    extra = 1


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin[Document]):
    """Админ-панель для документов"""

    list_display = [
        "title",
        "author",
        "category",
        "word_count",
        "search_count",
        "is_active",
        "created_at",
        "updated_at",
    ]
    list_filter = ["is_active", "category", "author", "created_at"]
    search_fields = ["title", "content", "author__username"]
    list_editable = ["is_active"]
    ordering = ["-created_at"]
    readonly_fields = ["word_count", "search_count", "created_at", "updated_at"]
    inlines = [DocumentTagRelationInline]

    fieldsets = (
        ("Основная информация", {"fields": ("title", "content", "file_path")}),
        ("Категоризация", {"fields": ("category", "author")}),
        ("Статус", {"fields": ("is_active",)}),
        (
            "Статистика",
            {"fields": ("word_count", "search_count", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def search_count(self, obj: Document) -> str:
        """Подсчет количества поисков в документе"""
        count = SearchHistory.objects.filter(document=obj).count()
        if count > 0:
            url = reverse("admin:doc_storage_searchhistory_changelist") + f"?document__id__exact={obj.id}"
            return format_html('<a href="{}">{}</a>', url, count)
        return str(0)

    search_count.short_description = "Количество поисков"  # type: ignore[attr-defined]

    def save_model(self, request: HttpRequest, obj: Document, form: Any, change: bool) -> None:
        """Автоматическая установка автора при создании"""
        if not change and not obj.author_id:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(WordMatch)
class WordMatchAdmin(admin.ModelAdmin[WordMatch]):
    """Админ-панель для найденных слов"""

    list_display = ["matched_word", "document", "query", "match_type", "relevance_score", "position", "created_at"]
    list_filter = ["match_type", "created_at", "document", "relevance_score"]
    search_fields = ["matched_word", "query", "document__title"]
    ordering = ["-created_at", "-relevance_score"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Основная информация", {"fields": ("document", "query", "matched_word")}),
        ("Детали совпадения", {"fields": ("match_type", "position", "relevance_score")}),
        ("Контекст", {"fields": ("context_before", "context_after"), "classes": ("collapse",)}),
        ("Метаданные", {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[WordMatch]:
        """Оптимизация запросов с предзагрузкой связанных объектов"""
        return super().get_queryset(request).select_related("document")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Запрет на ручное добавление записей совпадений"""
        return False


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin[SearchHistory]):
    """Админ-панель для истории поиска"""

    list_display = ["query", "document", "user", "results_count", "search_time", "ip_address", "created_at"]
    list_filter = ["created_at", "user", "document"]
    search_fields = ["query", "user__username", "document__title", "ip_address"]
    ordering = ["-created_at"]
    readonly_fields = ["created_at"]

    fieldsets = (
        ("Поисковый запрос", {"fields": ("query", "document", "user")}),
        ("Результаты", {"fields": ("results_count", "search_time")}),
        ("Метаданные", {"fields": ("ip_address", "created_at"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request: HttpRequest) -> QuerySet[SearchHistory]:
        """Оптимизация запросов с предзагрузкой связанных объектов"""
        return super().get_queryset(request).select_related("document", "user")

    def has_add_permission(self, request: HttpRequest) -> bool:
        """Запрет на ручное добавление записей истории"""
        return False


# Дополнительные административные действия
class WordMatchInline(admin.TabularInline[WordMatch, Document]):
    """Inline для просмотра найденных слов в документе"""

    model = WordMatch
    extra = 0
    readonly_fields = ["query", "matched_word", "match_type", "relevance_score", "position", "created_at"]
    fields = ["query", "matched_word", "match_type", "relevance_score", "position"]

    def has_add_permission(self, request: HttpRequest, obj: Document = None) -> bool:
        return False


class SearchHistoryInline(admin.TabularInline[SearchHistory, Document]):
    """Inline для просмотра истории поиска в документе"""

    model = SearchHistory
    extra = 0
    readonly_fields = ["query", "user", "results_count", "search_time", "created_at"]
    fields = ["query", "user", "results_count", "search_time", "created_at"]

    def has_add_permission(self, request: HttpRequest, obj: Document = None) -> bool:
        return False


# Регистрируем inline для документов
DocumentAdmin.inlines.extend([SearchHistoryInline, WordMatchInline])

# Настройка заголовков админ-панели
admin.site.site_header = "Поисковик слов в документах - Администрирование"
admin.site.site_title = "Поисковик документов"
admin.site.index_title = "Управление системой поиска слов в документах"


# Дополнительные фильтры для удобства
class RelevanceScoreFilter(admin.SimpleListFilter):
    """Фильтр по оценке релевантности"""

    title = "оценка релевантности"
    parameter_name = "relevance"

    def lookups(self, request: HttpRequest, model_admin: Any) -> list[tuple[str, str]]:
        return [
            ("high", "Высокая (≥ 1.0)"),
            ("medium", "Средняя (0.5-1.0)"),
            ("low", "Низкая (< 0.5)"),
        ]

    def queryset(self, request: HttpRequest, queryset: QuerySet[Any]) -> QuerySet[Any]:
        if self.value() == "high":
            return queryset.filter(relevance_score__gte=1.0)
        elif self.value() == "medium":
            return queryset.filter(relevance_score__gte=0.5, relevance_score__lt=1.0)
        elif self.value() == "low":
            return queryset.filter(relevance_score__lt=0.5)
        return queryset


# Добавляем дополнительные фильтры
WordMatchAdmin.list_filter = list(WordMatchAdmin.list_filter) + [RelevanceScoreFilter]
