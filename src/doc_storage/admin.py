from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Document, DocumentCategory, DocumentTag, DocumentTagRelation, SearchHistory


@admin.register(DocumentCategory)
class DocumentCategoryAdmin(admin.ModelAdmin):
    """Админ-панель для категорий документов"""
    list_display = ['name', 'description', 'document_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name', 'description']
    ordering = ['name']

    def document_count(self, obj):
        """Подсчет количества документов в категории"""
        count = obj.document_set.filter(is_active=True).count()
        url = reverse('admin:doc_storage_document_changelist') + f'?category__id__exact={obj.id}'
        return format_html('<a href="{}">{}</a>', url, count)

    document_count.short_description = 'Количество документов'


@admin.register(DocumentTag)
class DocumentTagAdmin(admin.ModelAdmin):
    """Админ-панель для тегов документов"""
    list_display = ['name', 'color_preview', 'usage_count', 'created_at']
    list_filter = ['created_at']
    search_fields = ['name']
    ordering = ['name']

    def color_preview(self, obj):
        """Превью цвета тега"""
        return format_html(
            '<div style="width: 20px; height: 20px; background-color: {}; border: 1px solid #ccc;"></div>',
            obj.color
        )

    color_preview.short_description = 'Цвет'

    def usage_count(self, obj):
        """Подсчет использования тега"""
        return obj.document_relations.count()

    usage_count.short_description = 'Использований'


class DocumentTagRelationInline(admin.TabularInline):
    """Inline для связей документов и тегов"""
    model = DocumentTagRelation
    extra = 1


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Админ-панель для документов"""
    list_display = [
        'title', 'author', 'category', 'word_count',
        'is_active', 'created_at', 'updated_at'
    ]
    list_filter = ['is_active', 'category', 'author', 'created_at']
    search_fields = ['title', 'content', 'author__username']
    list_editable = ['is_active']
    ordering = ['-created_at']
    readonly_fields = ['word_count', 'created_at', 'updated_at']
    inlines = [DocumentTagRelationInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'content', 'file_path')
        }),
        ('Категоризация', {
            'fields': ('category', 'author')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Статистика', {
            'fields': ('word_count', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        """Автоматическая установка автора при создании"""
        if not change and not obj.author:
            obj.author = request.user
        super().save_model(request, obj, form, change)


@admin.register(SearchHistory)
class SearchHistoryAdmin(admin.ModelAdmin):
    """Админ-панель для истории поиска"""
    list_display = [
        'query', 'user', 'results_count', 'search_time',
        'ip_address', 'created_at'
    ]
    list_filter = ['created_at', 'user']
    search_fields = ['query', 'user__username', 'ip_address']
    ordering = ['-created_at']
    readonly_fields = ['created_at']

    def has_add_permission(self, request):
        """Запрет на ручное добавление записей истории"""
        return False


# Настройка заголовков админ-панели
admin.site.site_header = "Поисковик документов - Администрирование"
admin.site.site_title = "Поисковик документов"
admin.site.index_title = "Управление системой поиска документов"