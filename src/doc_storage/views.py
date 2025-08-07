from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
import json
from typing import Any, Dict, List
from collections import Counter
from pathlib import Path
import re

from .models import Document, DocumentCategory, DocumentTag, SearchHistory, WordMatch, DocumentTagRelation
from .serializers import (
    DocumentSerializer, DocumentListSerializer, DocumentCategorySerializer,
    DocumentTagSerializer, WordMatchSerializer, SearchHistorySerializer,
    WordSearchResultSerializer, DocumentWordCloudSerializer, SearchStatisticsSerializer
)
from .forms import DocumentUploadForm, DocumentEditForm, DocumentCreateForm, FileReplaceForm
from .file_service import DocumentFileService, FileTextExtractor
from search_service.algorithms import WordSearchService


# Function-Based Views (FBV)

@api_view(['GET'])
def search_words_in_document_api(request: HttpRequest) -> Response:
    """API функция для поиска слов в конкретном документе"""
    document_id = request.GET.get('document_id')
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'combined')

    if not document_id:
        return Response({
            'error': 'Параметр "document_id" обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)

    if not query:
        return Response({
            'error': 'Параметр запроса "q" обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)

    try:
        document = Document.objects.get(id=document_id, is_active=True)
    except Document.DoesNotExist:
        return Response({
            'error': 'Документ не найден'
        }, status=status.HTTP_404_NOT_FOUND)

    # Получаем IP адрес пользователя
    ip_address = request.META.get('REMOTE_ADDR')
    user = request.user if request.user.is_authenticated else None

    # Выполняем поиск слов в документе
    search_service = WordSearchService()
    matches, search_time = search_service.search_words_in_document(
        document=document,
        query=query,
        search_type=search_type,
        user=user,
        ip_address=ip_address
    )

    # Получаем сохраненные результаты из базы данных
    word_matches = search_service.get_search_results(document, query)

    # Определяем использованные алгоритмы
    algorithms_used = list(set([match.get('algorithm', 'Unknown') for match in matches]))

    # Сериализуем результаты
    serializer = WordSearchResultSerializer({
        'document': document,
        'query': query,
        'total_matches': len(matches),
        'search_time': search_time,
        'matches': word_matches,
        'search_type': search_type,
        'algorithms_used': algorithms_used
    })

    return Response(serializer.data)


@api_view(['GET'])
def get_document_word_cloud(request: HttpRequest, document_id: int) -> Response:
    """Получение облака слов для документа"""
    try:
        document = Document.objects.get(id=document_id, is_active=True)
    except Document.DoesNotExist:
        return Response({
            'error': 'Документ не найден'
        }, status=status.HTTP_404_NOT_FOUND)

    # Анализируем текст документа
    content = document.content.lower()
    # Удаляем пунктуацию и разбиваем на слова
    words = re.findall(r'\b[а-яё\w]+\b', content)

    # Фильтруем стоп-слова (простой список)
    stop_words = {'и', 'в', 'на', 'с', 'по', 'для', 'от', 'до', 'при', 'к', 'а', 'но', 'или', 'что', 'это', 'как',
                  'так'}
    filtered_words = [word for word in words if len(word) > 2 and word not in stop_words]

    # Подсчитываем частоту
    word_frequencies = dict(Counter(filtered_words).most_common(50))

    serializer = DocumentWordCloudSerializer({
        'document': document,
        'word_frequencies': word_frequencies,
        'total_unique_words': len(set(filtered_words))
    })

    return Response(serializer.data)


@api_view(['GET'])
def get_search_suggestions(request: HttpRequest, document_id: int) -> Response:
    """Получение поисковых подсказок на основе содержимого документа"""
    query_prefix = request.GET.get('prefix', '').strip().lower()

    if not query_prefix or len(query_prefix) < 2:
        return Response({
            'suggestions': []
        })

    try:
        document = Document.objects.get(id=document_id, is_active=True)
    except Document.DoesNotExist:
        return Response({
            'error': 'Документ не найден'
        }, status=status.HTTP_404_NOT_FOUND)

    # Ищем слова, начинающиеся с префикса
    content = document.content.lower()
    words = re.findall(r'\b[а-яё\w]+\b', content)

    # Фильтруем по префиксу
    matching_words = [word for word in words if word.startswith(query_prefix)]
    word_counts = Counter(matching_words)

    # Создаем предложения с контекстом
    suggestions = []
    for word, frequency in word_counts.most_common(10):
        # Находим контекст для слова
        pattern = r'\b' + re.escape(word) + r'\b'
        match = re.search(pattern, content)
        context_preview = ""

        if match:
            start = max(0, match.start() - 30)
            end = min(len(content), match.end() + 30)
            context_preview = content[start:end].strip()

        suggestions.append({
            'word': word,
            'frequency': frequency,
            'context_preview': context_preview
        })

    return Response({
        'suggestions': suggestions
    })


@csrf_exempt
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document(request: HttpRequest) -> Response:
    """Функция для загрузки документа"""
    try:
        data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

        serializer = DocumentSerializer(data=data, context={'request': request})
        if serializer.is_valid():
            document = serializer.save()
            return Response(
                DocumentSerializer(document, context={'request': request}).data,
                status=status.HTTP_201_CREATED
            )
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    except json.JSONDecodeError:
        return Response({
            'error': 'Некорректный JSON'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def get_search_statistics(request: HttpRequest) -> Response:
    """Получение статистики поиска"""
    # Популярные запросы
    popular_queries = (SearchHistory.objects
                       .values('query')
                       .annotate(count=Count('query'))
                       .order_by('-count')[:10])

    # Документы с наибольшим количеством поисков
    popular_documents = (SearchHistory.objects
                         .values('document__title', 'document__id')
                         .annotate(search_count=Count('document'))
                         .order_by('-search_count')[:10])

    # Общая статистика
    total_searches = SearchHistory.objects.count()
    total_documents = Document.objects.filter(is_active=True).count()

    serializer = SearchStatisticsSerializer({
        'total_searches': total_searches,
        'total_documents': total_documents,
        'average_search_time': SearchHistory.objects.aggregate(
            avg_time=Avg('search_time')
        )['avg_time'] or 0,
        'most_searched_words': list(popular_queries),
        'documents_with_searches': list(popular_documents)
    })

    return Response(serializer.data)


# Class-Based Views (CBV)

class DocumentListView(ListView):
    """Класс для отображения списка документов"""
    model = Document
    template_name = 'doc_storage/document_list.html'
    context_object_name = 'documents'
    paginate_by = 20

    def get_queryset(self):
        """Переопределение queryset с фильтрацией"""
        queryset = Document.objects.filter(is_active=True).select_related('author', 'category')

        # Фильтрация по категории
        category_id = self.request.GET.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # Поиск по заголовку
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query)
            )

        return queryset.order_by('-created_at')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Добавление дополнительного контекста"""
        context = super().get_context_data(**kwargs)
        context['categories'] = DocumentCategory.objects.all()
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        return context


class DocumentDetailView(DetailView):
    """Класс для детального просмотра документа"""
    model = Document
    template_name = 'doc_storage/document_detail.html'
    context_object_name = 'document'

    def get_queryset(self):
        """Ограничение только активными документами"""
        return Document.objects.filter(is_active=True).select_related('author', 'category')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Добавление дополнительного контекста"""
        context = super().get_context_data(**kwargs)
        document = self.get_object()

        # Похожие документы
        similar_documents = Document.objects.filter(
            category=document.category,
            is_active=True
        ).exclude(id=document.id)[:5]

        # Последние поиски в этом документе
        recent_searches = SearchHistory.objects.filter(
            document=document
        ).order_by('-created_at')[:10]

        context['similar_documents'] = similar_documents
        context['document_tags'] = document.tag_relations.select_related('tag')
        context['recent_searches'] = recent_searches
        return context


class WordSearchView(DetailView):
    """Класс для поиска слов в документе"""
    model = Document
    template_name = 'doc_storage/word_search.html'
    context_object_name = 'document'

    def get_queryset(self):
        """Ограничение только активными документами"""
        return Document.objects.filter(is_active=True).select_related('author', 'category')

    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Добавление контекста для поиска слов"""
        context = super().get_context_data(**kwargs)
        document = self.get_object()

        query = self.request.GET.get('q', '')
        search_type = self.request.GET.get('type', 'combined')

        if query:
            from search_service.algorithms import WordSearchService
            search_service = WordSearchService()
            matches, search_time = search_service.search_words_in_document(
                document=document,
                query=query,
                search_type=search_type,
                user=self.request.user if self.request.user.is_authenticated else None,
                ip_address=self.request.META.get('REMOTE_ADDR')
            )

            word_matches = search_service.get_search_results(document, query)
            context['word_matches'] = word_matches
            context['search_time'] = search_time
            context['total_matches'] = len(matches)

        context['query'] = query
        context['search_type'] = search_type
        return context


@method_decorator(login_required, name='dispatch')
class SearchHistoryView(ListView):
    """Класс для просмотра истории поиска пользователя"""
    model = SearchHistory
    template_name = 'doc_storage/search_history.html'
    context_object_name = 'search_history'
    paginate_by = 50

    def get_queryset(self):
        """Ограничение истории текущим пользователем"""
        return SearchHistory.objects.filter(
            user=self.request.user
        ).select_related('document').order_by('-created_at')


# Django REST Framework ViewSets

class DocumentCategoryViewSet(viewsets.ModelViewSet):
    """ViewSet для категорий документов"""
    queryset = DocumentCategory.objects.all()
    serializer_class = DocumentCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def documents(self, request, pk=None):
        """Получение документов конкретной категории"""
        category = self.get_object()
        documents = Document.objects.filter(
            category=category,
            is_active=True
        ).order_by('-created_at')

        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = DocumentListSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DocumentListSerializer(documents, many=True)
        return Response(serializer.data)


class DocumentTagViewSet(viewsets.ModelViewSet):
    """ViewSet для тегов документов"""
    queryset = DocumentTag.objects.all()
    serializer_class = DocumentTagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class DocumentViewSet(viewsets.ModelViewSet):
    """ViewSet для документов"""
    queryset = Document.objects.filter(is_active=True)
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'content']
    filterset_fields = ['category', 'author']
    ordering_fields = ['created_at', 'updated_at', 'title', 'word_count']
    ordering = ['-created_at']

    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'list':
            return DocumentListSerializer
        return DocumentSerializer

    def get_queryset(self):
        """Оптимизированный queryset с предзагрузкой связанных объектов"""
        return Document.objects.filter(is_active=True).select_related(
            'author', 'category'
        ).prefetch_related('tag_relations__tag')

    def perform_create(self, serializer):
        """Установка автора при создании документа"""
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'])
    def search_words(self, request, pk=None):
        """Поиск слов в конкретном документе"""
        document = self.get_object()
        query = request.query_params.get('q', '').strip()
        search_type = request.query_params.get('type', 'combined')

        if not query:
            return Response({
                'error': 'Параметр запроса "q" обязателен'
            }, status=status.HTTP_400_BAD_REQUEST)

        # Выполняем поиск
        search_service = WordSearchService()
        matches, search_time = search_service.search_words_in_document(
            document=document,
            query=query,
            search_type=search_type,
            user=request.user if request.user.is_authenticated else None,
            ip_address=request.META.get('REMOTE_ADDR')
        )

        word_matches = search_service.get_search_results(document, query)

        serializer = WordSearchResultSerializer({
            'document': document,
            'query': query,
            'total_matches': len(matches),
            'search_time': search_time,
            'matches': word_matches,
            'search_type': search_type,
            'algorithms_used': ['KMP', 'Boyer-Moore', 'Rabin-Karp', 'Fuzzy']
        })

        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def word_cloud(self, request, pk=None):
        """Получение облака слов для документа"""
        return get_document_word_cloud(request, pk)

    @action(detail=True, methods=['get'])
    def search_suggestions(self, request, pk=None):
        """Получение поисковых подсказок"""
        return get_search_suggestions(request, pk)


class WordMatchViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для найденных слов (только чтение)"""
    queryset = WordMatch.objects.all()
    serializer_class = WordMatchSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['document', 'query', 'match_type']
    ordering_fields = ['position', 'relevance_score', 'created_at']
    ordering = ['-relevance_score', 'position']


class SearchHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для истории поиска (только чтение)"""
    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user', 'document']
    ordering_fields = ['created_at', 'search_time', 'results_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """Ограничение истории текущим пользователем"""
        return SearchHistory.objects.filter(user=self.request.user).select_related('document')

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика поиска пользователя"""
        user_history = self.get_queryset()

        stats = {
            'total_searches': user_history.count(),
            'average_search_time': user_history.aggregate(
                avg_time=Avg('search_time')
            )['avg_time'] or 0,
            'most_searched_words': user_history.values('query').annotate(
                count=Count('query')
            ).order_by('-count')[:10],
            'most_searched_documents': user_history.values(
                'document__title', 'document__id'
            ).annotate(
                count=Count('document')
            ).order_by('-count')[:10]
        }

        return Response(stats)


# Представления для загрузки файлов

class DocumentUploadView(LoginRequiredMixin, CreateView):
    """Представление для загрузки документа из файла"""
    template_name = 'doc_storage/document_upload.html'
    form_class = DocumentUploadForm
    success_url = reverse_lazy('doc_storage:document_list')

    def form_valid(self, form):
        """Обработка валидной формы загрузки файла"""
        uploaded_file = form.cleaned_data['file']
        title = form.cleaned_data['title']
        category = form.cleaned_data['category']
        tags = form.cleaned_data['tags']

        # Создаем документ из файла
        file_service = DocumentFileService()
        document, error = file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title=title,
            category=category,
            author=self.request.user
        )

        if error:
            messages.error(self.request, f"Ошибка загрузки файла: {error}")
            return self.form_invalid(form)

        # Добавляем теги к документу
        for tag in tags:
            DocumentTagRelation.objects.get_or_create(
                document=document,
                tag=tag
            )

        messages.success(
            self.request,
            f'Документ "{document.title}" успешно создан из файла "{uploaded_file.name}"'
        )

        # Перенаправляем на страницу созданного документа
        return redirect('doc_storage:document_detail', pk=document.pk)

    def get_context_data(self, **kwargs):
        """Добавление контекста"""
        context = super().get_context_data(**kwargs)
        context['supported_formats'] = sorted(FileTextExtractor.SUPPORTED_EXTENSIONS)
        context['max_file_size_mb'] = FileTextExtractor.MAX_FILE_SIZE // (1024 * 1024)
        return context


class DocumentCreateView(LoginRequiredMixin, CreateView):
    """Представление для создания документа вручную"""
    model = Document
    template_name = 'doc_storage/document_create.html'
    form_class = DocumentCreateForm

    def form_valid(self, form):
        """Обработка валидной формы создания документа"""
        form.instance.author = self.request.user
        response = super().form_valid(form)

        # Добавляем теги к документу
        tags = form.cleaned_data.get('tags', [])
        for tag in tags:
            DocumentTagRelation.objects.get_or_create(
                document=self.object,
                tag=tag
            )

        messages.success(self.request, f'Документ "{self.object.title}" успешно создан')
        return response

    def get_success_url(self):
        """URL для перенаправления после успешного создания"""
        return reverse('doc_storage:document_detail', kwargs={'pk': self.object.pk})


class DocumentEditView(LoginRequiredMixin, UpdateView):
    """Представление для редактирования документа"""
    model = Document
    template_name = 'doc_storage/document_edit.html'
    form_class = DocumentEditForm

    def get_queryset(self):
        """Ограничение редактирования только своими документами"""
        return Document.objects.filter(author=self.request.user)

    def form_valid(self, form):
        """Обработка валидной формы редактирования"""
        response = super().form_valid(form)
        messages.success(self.request, f'Документ "{self.object.title}" успешно обновлен')
        return response

    def get_success_url(self):
        """URL для перенаправления после успешного обновления"""
        return reverse('doc_storage:document_detail', kwargs={'pk': self.object.pk})


class DocumentReplaceFileView(LoginRequiredMixin, UpdateView):
    """Представление для замены файла в документе"""
    model = Document
    template_name = 'doc_storage/document_replace_file.html'
    form_class = FileReplaceForm

    def get_queryset(self):
        """Ограничение замены файлов только в своих документах"""
        return Document.objects.filter(author=self.request.user)

    def get_form(self, form_class=None):
        """Переопределяем метод для работы с формой файла"""
        if form_class is None:
            form_class = self.get_form_class()

        # Для GET запроса возвращаем пустую форму
        if self.request.method == 'GET':
            return form_class()

        # Для POST запроса передаем данные и файлы
        return form_class(data=self.request.POST, files=self.request.FILES)

    def form_valid(self, form):
        """Обработка замены файла"""
        uploaded_file = form.cleaned_data['file']
        keep_title = form.cleaned_data['keep_title']

        # Обновляем документ из файла
        file_service = DocumentFileService()
        success, error = file_service.update_document_from_file(
            document=self.object,
            uploaded_file=uploaded_file
        )

        if error:
            messages.error(self.request, f"Ошибка замены файла: {error}")
            return self.form_invalid(form)

        # Обновляем заголовок если нужно
        if not keep_title:
            file_name = Path(uploaded_file.name).stem
            self.object.title = file_name
            self.object.save()

        messages.success(
            self.request,
            f'Файл в документе "{self.object.title}" успешно заменен'
        )

        return redirect('doc_storage:document_detail', pk=self.object.pk)

    def get_context_data(self, **kwargs):
        """Добавление контекста"""
        context = super().get_context_data(**kwargs)
        context['supported_formats'] = sorted(FileTextExtractor.SUPPORTED_EXTENSIONS)
        context['max_file_size_mb'] = FileTextExtractor.MAX_FILE_SIZE // (1024 * 1024)
        return context


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upload_document_file_api(request: HttpRequest) -> Response:
    """API функция для загрузки документа из файла"""
    try:
        if 'file' not in request.FILES:
            return Response({
                'error': 'Файл не был загружен'
            }, status=status.HTTP_400_BAD_REQUEST)

        uploaded_file = request.FILES['file']
        title = request.data.get('title', '').strip()
        category_id = request.data.get('category_id')

        # Получаем категорию если указана
        category = None
        if category_id:
            try:
                category = DocumentCategory.objects.get(id=category_id)
            except DocumentCategory.DoesNotExist:
                return Response({
                    'error': 'Указанная категория не существует'
                }, status=status.HTTP_400_BAD_REQUEST)

        # Создаем документ из файла
        file_service = DocumentFileService()
        document, error = file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title=title,
            category=category,
            author=request.user
        )

        if error:
            return Response({
                'error': error
            }, status=status.HTTP_400_BAD_REQUEST)

        # Возвращаем созданный документ
        serializer = DocumentSerializer(document, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({
            'error': f'Неожиданная ошибка: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)