from typing import List, Union

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path

URLPatternList = List[Union[URLPattern, URLResolver]]

urlpatterns: URLPatternList = [
    path("admin/", admin.site.urls),
    path("", include("doc_storage.urls")),
    path("api-auth/", include("rest_framework.urls")),
]

# Добавление маршрутов для медиа файлов в режиме отладки
if settings.DEBUG:
    media_patterns = static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    static_patterns = static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns.extend(media_patterns)
    urlpatterns.extend(static_patterns)
