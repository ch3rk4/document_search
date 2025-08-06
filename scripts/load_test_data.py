import os
import sys
import django
from pathlib import Path

# Определяем пути
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
src_dir = project_root / 'src'

# Добавляем src директорию в sys.path
sys.path.insert(0, str(src_dir))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'document_search.settings')

# Переходим в src директорию для правильной работы Django
os.chdir(src_dir)

django.setup()

# Импортируем модели ПОСЛЕ setup Django (без "src.")
from django.contrib.auth.models import User
from doc_storage.models import Document, DocumentCategory, DocumentTag, DocumentTagRelation


def create_test_data():
    """Создание тестовых данных для демонстрации функциональности"""

    # Создание пользователей
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'first_name': 'Администратор',
            'last_name': 'Системы',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
        print(f"Создан пользователь: {admin_user.username}")

    author_user, created = User.objects.get_or_create(
        username='author',
        defaults={
            'email': 'author@example.com',
            'first_name': 'Автор',
            'last_name': 'Документов'
        }
    )
    if created:
        author_user.set_password('author123')
        author_user.save()
        print(f"Создан пользователь: {author_user.username}")

    # Создание категорий
    categories_data = [
        {'name': 'Программирование', 'description': 'Статьи о языках программирования и разработке'},
        {'name': 'Наука', 'description': 'Научные статьи и исследования'},
        {'name': 'Технологии', 'description': 'Современные технологии и инновации'},
    ]

    categories = {}
    for cat_data in categories_data:
        category, created = DocumentCategory.objects.get_or_create(
            name=cat_data['name'],
            defaults={'description': cat_data['description']}
        )
        categories[cat_data['name']] = category
        if created:
            print(f"Создана категория: {category.name}")

    # Создание тегов
    tags_data = [
        {'name': 'python', 'color': '#3776ab'},
        {'name': 'javascript', 'color': '#f7df1e'},
        {'name': 'алгоритмы', 'color': '#45b7d1'},
    ]

    tags = {}
    for tag_data in tags_data:
        tag, created = DocumentTag.objects.get_or_create(
            name=tag_data['name'],
            defaults={'color': tag_data['color']}
        )
        tags[tag_data['name']] = tag
        if created:
            print(f"Создан тег: {tag.name}")

    # Создание документов
    documents_data = [
        {
            'title': 'Введение в Python программирование',
            'content': '''Python - это высокоуровневый интерпретируемый язык программирования. 
            Python известен своей простотой и читаемостью кода.

            Основные особенности Python:
            - Простой синтаксис
            - Богатая библиотека
            - Кроссплатформенность

            Python используется в веб-разработке, анализе данных, машинном обучении.''',
            'category': 'Программирование',
            'tags': ['python', 'алгоритмы'],
            'author': author_user
        },
        {
            'title': 'JavaScript для веб-разработки',
            'content': '''JavaScript - динамический язык программирования для веб-страниц.

            Ключевые концепции JavaScript:
            - Асинхронное программирование
            - Замыкания
            - Прототипное наследование

            Современные фреймворки: React, Vue.js, Angular.''',
            'category': 'Программирование',
            'tags': ['javascript', 'алгоритмы'],
            'author': author_user
        },
        {
            'title': 'Алгоритмы поиска',
            'content': '''Алгоритмы поиска являются фундаментальными в программировании.

            Основные алгоритмы:
            - Линейный поиск - O(n)
            - Двоичный поиск - O(log n)
            - Поиск в хеш-таблице - O(1)

            Выбор алгоритма зависит от данных и требований.''',
            'category': 'Наука',
            'tags': ['алгоритмы', 'python'],
            'author': admin_user
        },
    ]

    # Создание документов с тегами
    for doc_data in documents_data:
        document, created = Document.objects.get_or_create(
            title=doc_data['title'],
            defaults={
                'content': doc_data['content'],
                'category': categories[doc_data['category']],
                'author': doc_data['author']
            }
        )

        if created:
            print(f"Создан документ: {document.title}")

            # Добавляем теги к документу
            for tag_name in doc_data['tags']:
                if tag_name in tags:
                    DocumentTagRelation.objects.get_or_create(
                        document=document,
                        tag=tags[tag_name]
                    )

    print("\n=== ТЕСТОВЫЕ ДАННЫЕ СОЗДАНЫ ===")
    print(f"Категорий: {DocumentCategory.objects.count()}")
    print(f"Тегов: {DocumentTag.objects.count()}")
    print(f"Документов: {Document.objects.count()}")
    print(f"Пользователей: {User.objects.count()}")
    print("\n=== ДАННЫЕ ДЛЯ ВХОДА ===")
    print("Админ: логин=admin, пароль=admin123")
    print("Автор: логин=author, пароль=author123")


if __name__ == '__main__':
    create_test_data()