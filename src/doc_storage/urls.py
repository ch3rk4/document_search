from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создание роутера для API
router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet)
router.register(r'categories', views.DocumentCategoryViewSet)
router.register(r'tags', views.DocumentTagViewSet)
router.register(r'search-history', views.SearchHistoryViewSet)

app_name = 'doc_storage'

urlpatterns = [
    # API маршруты
    path('api/v1/', include(router.urls)),
    path('api/v1/search/', views.search_documents_api, name='search_api'),
    path('api/v1/upload/', views.upload_document, name='upload_api'),
    path('api/v1/statistics/', views.get_search_statistics, name='statistics_api'),

    # Web интерфейс маршруты
    path('', views.DocumentListView.as_view(), name='document_list'),
    path('document/<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('search-history/', views.SearchHistoryView.as_view(), name='search_history'),
]