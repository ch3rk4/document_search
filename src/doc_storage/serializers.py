# mypy: ignore-errors

from typing import Any, Dict, List

from django.contrib.auth.models import User
from rest_framework import serializers

from .models import (Document, DocumentCategory, DocumentTag,
                     DocumentTagRelation, SearchHistory, WordMatch)


class UserSerializer(serializers.ModelSerializer):  # type: ignore
    """Сериализатор для модели пользователя"""

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email"]
        read_only_fields = ["id"]


class DocumentCategorySerializer(serializers.ModelSerializer):  # type: ignore
    """Сериализатор для категорий документов"""

    document_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentCategory
        fields = ["id", "name", "description", "created_at", "document_count"]
        read_only_fields = ["id", "created_at"]

    def get_document_count(self, obj: DocumentCategory) -> int:
        """Подсчет количества документов в категории"""
        return Document.objects.filter(category=obj, is_active=True).count()


class DocumentTagSerializer(serializers.ModelSerializer):  # type: ignore
    """Сериализатор для тегов документов"""

    class Meta:
        model = DocumentTag
        fields = ["id", "name", "color", "created_at"]
        read_only_fields = ["id", "created_at"]


class DocumentSerializer(serializers.ModelSerializer):  # type: ignore
    """Основной сериализатор для документов"""

    author = UserSerializer(read_only=True)
    category = DocumentCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    tags = DocumentTagSerializer(many=True, read_only=True, source="get_tags")
    tag_ids = serializers.ListField(child=serializers.IntegerField(), write_only=True, required=False, allow_empty=True)
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "content",
            "file_path",
            "file_url",
            "category",
            "category_id",
            "author",
            "created_at",
            "updated_at",
            "is_active",
            "word_count",
            "tags",
            "tag_ids",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "word_count", "author"]

    def get_file_url(self, obj: Document) -> str:
        """Получение URL файла документа"""
        if obj.file_path:
            request = self.context.get("request")
            if request:
                return request.build_absolute_uri(obj.file_path.url)
        return ""

    def get_tags(self, obj: Document) -> List[DocumentTag]:
        """Получение тегов документа"""
        return [relation.tag for relation in obj.tag_relations.select_related("tag")]

    def create(self, validated_data: Dict[str, Any]) -> Document:
        """Создание документа с тегами"""
        tag_ids = validated_data.pop("tag_ids", [])
        category_id = validated_data.pop("category_id", None)

        if category_id:
            validated_data["category_id"] = category_id

        # Устанавливаем автора из контекста запроса
        request = self.context.get("request")
        if request and request.user:
            validated_data["author"] = request.user

        document = Document.objects.create(**validated_data)

        # Добавляем теги
        self._update_document_tags(document, tag_ids)

        return document

    def update(self, instance: Document, validated_data: Dict[str, Any]) -> Document:
        """Обновление документа с тегами"""
        tag_ids = validated_data.pop("tag_ids", None)
        category_id = validated_data.pop("category_id", None)

        if category_id is not None:
            validated_data["category_id"] = category_id

        # Обновляем поля документа
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Обновляем теги, если они переданы
        if tag_ids is not None:
            self._update_document_tags(instance, tag_ids)

        return instance

    def _update_document_tags(self, document: Document, tag_ids: List[int]) -> None:
        """Обновление тегов документа"""
        # Удаляем существующие связи
        DocumentTagRelation.objects.filter(document=document).delete()

        # Создаем новые связи
        for tag_id in tag_ids:
            try:
                tag = DocumentTag.objects.get(id=tag_id)
                DocumentTagRelation.objects.create(document=document, tag=tag)
            except DocumentTag.DoesNotExist:
                continue


class DocumentListSerializer(serializers.ModelSerializer):  # type: ignore
    """Упрощенный сериализатор для списка документов"""

    author_name = serializers.CharField(source="author.username", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)
    tags_count = serializers.SerializerMethodField()
    content_preview = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            "id",
            "title",
            "author_name",
            "category_name",
            "created_at",
            "updated_at",
            "word_count",
            "tags_count",
            "content_preview",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "word_count"]

    def get_tags_count(self, obj: Document) -> int:
        """Подсчет количества тегов у документа"""
        return obj.tag_relations.count()

    def get_content_preview(self, obj: Document) -> str:
        """Превью содержимого документа"""
        return obj.content[:200] + "..." if len(obj.content) > 200 else obj.content


class WordMatchSerializer(serializers.ModelSerializer):  # type: ignore
    """Сериализатор для найденных слов"""

    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = WordMatch
        fields = [
            "id",
            "document",
            "document_title",
            "query",
            "matched_word",
            "position",
            "context_before",
            "context_after",
            "match_type",
            "relevance_score",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class WordSearchResultSerializer(serializers.Serializer):  # type: ignore
    """Сериализатор для результатов поиска слов в документе"""

    document = DocumentListSerializer(read_only=True)
    query = serializers.CharField(read_only=True)
    total_matches = serializers.IntegerField(read_only=True)
    search_time = serializers.FloatField(read_only=True)
    matches = WordMatchSerializer(many=True, read_only=True)
    search_type = serializers.CharField(read_only=True)
    algorithms_used = serializers.ListField(child=serializers.CharField(), read_only=True)


class SearchSuggestionSerializer(serializers.Serializer):  # type: ignore
    """Сериализатор для поисковых подсказок"""

    word = serializers.CharField()
    frequency = serializers.IntegerField()
    context_preview = serializers.CharField()


class DocumentWordCloudSerializer(serializers.Serializer):  # type: ignore
    """Сериализатор для облака слов документа"""

    document = DocumentListSerializer(read_only=True)
    word_frequencies = serializers.DictField(child=serializers.IntegerField(), read_only=True)
    total_unique_words = serializers.IntegerField(read_only=True)


class SearchHistorySerializer(serializers.ModelSerializer):  # type: ignore
    """Сериализатор для истории поиска"""

    user_name = serializers.CharField(source="user.username", read_only=True)
    document_title = serializers.CharField(source="document.title", read_only=True)

    class Meta:
        model = SearchHistory
        fields = [
            "id",
            "query",
            "document",
            "document_title",
            "user_name",
            "results_count",
            "search_time",
            "created_at",
            "ip_address",
        ]
        read_only_fields = ["id", "created_at"]


class SearchStatisticsSerializer(serializers.Serializer):  # type: ignore
    """Сериализатор для статистики поиска"""

    total_searches = serializers.IntegerField(read_only=True)
    total_documents = serializers.IntegerField(read_only=True)
    average_search_time = serializers.FloatField(read_only=True)
    most_searched_words = serializers.ListField(child=serializers.DictField(), read_only=True)
    documents_with_searches = serializers.ListField(child=serializers.DictField(), read_only=True)


class DocumentAnalysisSerializer(serializers.Serializer):  # type: ignore
    """Сериализатор для анализа документа"""

    document = DocumentListSerializer(read_only=True)
    readability_score = serializers.FloatField(read_only=True)
    complexity_score = serializers.FloatField(read_only=True)
    most_common_words = serializers.ListField(child=serializers.DictField(), read_only=True)
    sentence_count = serializers.IntegerField(read_only=True)
    paragraph_count = serializers.IntegerField(read_only=True)
    average_word_length = serializers.FloatField(read_only=True)
