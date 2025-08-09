"""
Корневой conftest.py для настройки Django окружения

import os
import sys
from pathlib import Path

# Добавляем src в Python path
root_dir = Path(__file__).resolve().parent
src_path = root_dir / 'src'
sys.path.insert(0, str(src_path))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_search.test_settings')

import django
from django.conf import settings

if not settings.configured:
    django.setup()
"""