from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, DocumentCategory, DocumentTag, DocumentTagRelation, SearchHistory


class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя"""

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name', 'email']
        read_only_fields = ['id']


class DocumentCategorySerializer(serializers.ModelSerializer):
    """Сериализатор для категорий документов"""

    document_count = serializers.SerializerMethodField()

    class Meta:
        model = DocumentCategory
        fields = ['id', 'name', 'description', 'created_at', 'document_count']
        read_only_fields = ['id', 'created_at']

    def get_document_count(self, obj: DocumentCategory) -> int:
        """Подсчет количества документов в категории"""
        return obj.document_set.filter(is_active=True).count()


class DocumentTagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов документов"""

    class Meta:
        model = DocumentTag
        fields = ['id', 'name', 'color', 'created_at']
        read_only_fields = ['id', 'created_at']


class DocumentSerializer(serializers.ModelSerializer):
    """Основной сериализатор для документов"""

    author = UserSerializer(read_only=True)
    category = DocumentCategorySerializer(read_only=True)
    category_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    tags = DocumentTagSerializer(source='tag_relations.tag', many=True, read_only=True)
    tag_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False,
        allow_empty=True
    )
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'content', 'file_path', 'file_url',
            'category', 'category_id', 'author', 'created_at',
            'updated_at', 'is_active', 'word_count', 'tags', 'tag_ids'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'word_count', 'author']

    def get_file_url(self, obj: Document) -> str:
        """Получение URL файла документа"""
        if obj.file_path:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.file_path.url)
        return ""

    def create(self, validated_data: dict) -> Document:
        """Создание документа с тегами"""
        tag_ids = validated_data.pop('tag_ids', [])
        category_id = validated_data.pop('category_id', None)

        if category_id:
            validated_data['category_id'] = category_id

        # Устанавливаем автора из контекста запроса
        request = self.context.get('request')
        if request and request.user:
            validated_data['author'] = request.user

        document = Document.objects.create(**validated_data)

        # Добавляем теги
        self._update_document_tags(document, tag_ids)

        return document

    def update(self, instance: Document, validated_data: dict) -> Document:
        """Обновление документа с тегами"""
        tag_ids = validated_data.pop('tag_ids', None)
        category_id = validated_data.pop('category_id', None)

        if category_id is not None:
            validated_data['category_id'] = category_id

        # Обновляем поля документа
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Обновляем теги, если они переданы
        if tag_ids is not None:
            self._update_document_tags(instance, tag_ids)

        return instance

    def _update_document_tags(self, document: Document, tag_ids: list) -> None:
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


class DocumentListSerializer(serializers.ModelSerializer):
    """Упрощенный сериализатор для списка документов"""

    author_name = serializers.CharField(source='author.username', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    tags_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'author_name', 'category_name',
            'created_at', 'updated_at', 'word_count', 'tags_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'word_count']

    def get_tags_count(self, obj: Document) -> int:
        """Подсчет количества тегов у документа"""
        return obj.tag_relations.count()


class SearchResultSerializer(serializers.Serializer):
    """Сериализатор для результатов поиска"""

    document = DocumentListSerializer(read_only=True)
    relevance_score = serializers.FloatField(read_only=True)
    preview = serializers.CharField(read_only=True)
    search_type = serializers.CharField(read_only=True, required=False)
    title_matches = serializers.IntegerField(read_only=True, required=False)
    content_matches = serializers.IntegerField(read_only=True, required=False)


class SearchHistorySerializer(serializers.ModelSerializer):
    """Сериализатор для истории поиска"""

    user_name = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = SearchHistory
        fields = [
            'id', 'query', 'user_name', 'results_count',
            'search_time', 'created_at', 'ip_address'
        ]
        read_only_fields = ['id', 'created_at']