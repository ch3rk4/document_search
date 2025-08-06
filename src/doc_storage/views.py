from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import ListView, DetailView
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
import json
from typing import Any, Dict, List

from .models import Document, DocumentCategory, DocumentTag, SearchHistory
from .serializers import (
    DocumentSerializer, DocumentListSerializer, DocumentCategorySerializer,
    DocumentTagSerializer, SearchResultSerializer, SearchHistorySerializer
)
from search_service.algorithms import SearchService


# Function-Based Views (FBV)

@api_view(['GET'])
def search_documents_api(request: HttpRequest) -> Response:
    """API функция для поиска документов"""
    query = request.GET.get('q', '').strip()
    search_type = request.GET.get('type', 'combined')

    if not query:
        return Response({
            'error': 'Параметр запроса "q" обязателен'
        }, status=status.HTTP_400_BAD_REQUEST)

    # Получаем IP адрес пользователя
    ip_address = request.META.get('REMOTE_ADDR')
    user = request.user if request.user.is_authenticated else None

    # Выполняем поиск
    search_service = SearchService()
    results, search_time = search_service.search_documents(
        query=query,
        search_type=search_type,
        user=user,
        ip_address=ip_address
    )

    # Сериализуем результаты
    serializer = SearchResultSerializer(results, many=True)

    return Response({
        'query': query,
        'search_type': search_type,
        'total_results': len(results),
        'search_time': round(search_time, 4),
        'results': serializer.data
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

    # Общая статистика
    total_searches = SearchHistory.objects.count()
    total_documents = Document.objects.filter(is_active=True).count()

    return Response({
        'total_searches': total_searches,
        'total_documents': total_documents,
        'popular_queries': list(popular_queries),
        'average_search_time': SearchHistory.objects.aggregate(
            avg_time=models.Avg('search_time')
        )['avg_time'] or 0
    })


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

        context['similar_documents'] = similar_documents
        context['document_tags'] = document.tag_relations.select_related('tag')
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
        ).order_by('-created_at')


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

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Переключение активности документа"""
        document = self.get_object()
        document.is_active = not document.is_active
        document.save()

        return Response({
            'id': document.id,
            'is_active': document.is_active,
            'message': f'Документ {"активирован" if document.is_active else "деактивирован"}'
        })

    @action(detail=False, methods=['get'])
    def my_documents(self, request):
        """Получение документов текущего пользователя"""
        documents = self.get_queryset().filter(author=request.user)

        page = self.paginate_queryset(documents)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(documents, many=True)
        return Response(serializer.data)


class SearchHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet для истории поиска (только чтение)"""
    queryset = SearchHistory.objects.all()
    serializer_class = SearchHistorySerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['user']
    ordering_fields = ['created_at', 'search_time', 'results_count']
    ordering = ['-created_at']

    def get_queryset(self):
        """Ограничение истории текущим пользователем"""
        return SearchHistory.objects.filter(user=self.request.user)

    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Статистика поиска пользователя"""
        user_history = self.get_queryset()

        stats = {
            'total_searches': user_history.count(),
            'average_search_time': user_history.aggregate(
                avg_time=models.Avg('search_time')
            )['avg_time'] or 0,
            'most_searched_queries': user_history.values('query').annotate(
                count=Count('query')
            ).order_by('-count')[:10]
        }

        return Response(stats)