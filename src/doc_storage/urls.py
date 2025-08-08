from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# Создание роутера для API
router = DefaultRouter()
router.register(r'documents', views.DocumentViewSet)
router.register(r'categories', views.DocumentCategoryViewSet)
router.register(r'tags', views.DocumentTagViewSet)
router.register(r'word-matches', views.WordMatchViewSet)
router.register(r'search-history', views.SearchHistoryViewSet)

app_name = 'doc_storage'

urlpatterns = [
    # API маршруты
    path('api/v1/', include(router.urls)),

    # Основные API для поиска слов
    path('api/v1/search-words/', views.search_words_in_document_api, name='search_words_api'),
    path('api/v1/upload/', views.upload_document, name='upload_api'),
    path('api/v1/statistics/', views.get_search_statistics, name='statistics_api'),

    # API для работы с отдельными документами
    path('api/v1/documents/<int:document_id>/word-cloud/', views.get_document_word_cloud, name='word_cloud_api'),
    path('api/v1/documents/<int:document_id>/search-suggestions/', views.get_search_suggestions,
         name='suggestions_api'),
    path('api/v1/upload-file/', views.upload_document_file_api, name='upload_file_api'),

    # Авторизация и регистрация
    path('register/', views.UserRegistrationView.as_view(), name='user_register'),
    path('login/', views.UserLoginView.as_view(), name='user_login'),
    path('logout/', views.UserLogoutView.as_view(), name='user_logout'),
    path('profile/', views.UserProfileView.as_view(), name='user_profile'),

    # Web интерфейс маршруты
    path('', views.DocumentListView.as_view(), name='document_list'),
    path('document/<int:pk>/', views.DocumentDetailView.as_view(), name='document_detail'),
    path('document/<int:pk>/search/', views.WordSearchView.as_view(), name='word_search'),
    path('document/<int:pk>/edit/', views.DocumentEditView.as_view(), name='document_edit'),
    path('document/<int:pk>/replace-file/', views.DocumentReplaceFileView.as_view(), name='document_replace_file'),

    # Создание и загрузка документов
    path('upload/', views.DocumentUploadView.as_view(), name='document_upload'),
    path('create/', views.DocumentCreateView.as_view(), name='document_create'),

    # История поиска
    path('search-history/', views.SearchHistoryView.as_view(), name='search_history'),
]