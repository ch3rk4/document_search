from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from typing import Optional


class DocumentCategory(models.Model):
    """Модель категории документов"""

    name = models.CharField(max_length=100, verbose_name="Название категории")
    description = models.TextField(blank=True, verbose_name="Описание")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Категория документа"
        verbose_name_plural = "Категории документов"
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class Document(models.Model):
    """Основная модель документа"""

    title = models.CharField(max_length=255, verbose_name="Заголовок")
    content = models.TextField(verbose_name="Содержимое документа")
    file_path = models.FileField(upload_to='documents/', blank=True, null=True, verbose_name="Файл")
    category = models.ForeignKey(
        DocumentCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Категория"
    )
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Автор")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    is_active = models.BooleanField(default=True, verbose_name="Активен")

    # Поля для оптимизации поиска
    word_count = models.PositiveIntegerField(default=0, verbose_name="Количество слов")
    search_vector = models.TextField(blank=True, verbose_name="Вектор поиска")

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['title']),
            models.Index(fields=['created_at']),
            models.Index(fields=['category']),
            models.Index(fields=['author']),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        """Переопределение метода сохранения для подсчета слов"""
        if self.content:
            self.word_count = len(self.content.split())
        super().save(*args, **kwargs)


class DocumentTag(models.Model):
    """Модель тегов для документов"""

    name = models.CharField(max_length=50, unique=True, verbose_name="Название тега")
    color = models.CharField(max_length=7, default="#007bff", verbose_name="Цвет тега")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Тег"
        verbose_name_plural = "Теги"
        ordering = ['name']

    def __str__(self) -> str:
        return self.name


class DocumentTagRelation(models.Model):
    """Связь документов и тегов"""

    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='tag_relations')
    tag = models.ForeignKey(DocumentTag, on_delete=models.CASCADE, related_name='document_relations')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['document', 'tag']
        verbose_name = "Связь документ-тег"
        verbose_name_plural = "Связи документов и тегов"


class SearchHistory(models.Model):
    """Модель истории поисковых запросов"""

    query = models.CharField(max_length=255, verbose_name="Поисковый запрос")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="Пользователь")
    results_count = models.PositiveIntegerField(default=0, verbose_name="Количество результатов")
    search_time = models.FloatField(default=0.0, verbose_name="Время поиска (сек)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата поиска")
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="IP адрес")

    class Meta:
        verbose_name = "История поиска"
        verbose_name_plural = "История поисков"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['created_at']),
            models.Index(fields=['user']),
        ]

    def __str__(self) -> str:
        return f"{self.query} ({self.results_count} результатов)"