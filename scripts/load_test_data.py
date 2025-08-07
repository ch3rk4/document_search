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
    """Создание тестовых данных для демонстрации функциональности поиска слов"""

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
        {'name': 'Алгоритмы', 'description': 'Алгоритмы и структуры данных'},
        {'name': 'Веб-разработка', 'description': 'Современные веб-технологии'},
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
        {'name': 'веб', 'color': '#ff6b6b'},
        {'name': 'данные', 'color': '#4ecdc4'},
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

    # Создание документов с богатым содержимым для поиска слов
    documents_data = [
        {
            'title': 'Введение в Python программирование',
            'content': '''Python - это высокоуровневый интерпретируемый язык программирования общего назначения.
            Python был создан Гвидо ван Россумом и впервые выпущен в 1991 году.

            Основные особенности Python:
            - Простой и понятный синтаксис
            - Богатая стандартная библиотека
            - Кроссплатформенность
            - Поддержка различных парадигм программирования

            Python широко используется в следующих областях:
            1. Веб-разработка (Django, Flask)
            2. Анализ данных и машинное обучение
            3. Автоматизация и скриптинг
            4. Научные вычисления
            5. Разработка игр

            Программирование на Python начинается с изучения основ:
            - Переменные и типы данных
            - Условные конструкции
            - Циклы for и while
            - Функции и методы
            - Работа с файлами

            Python также поддерживает объектно-ориентированное программирование.
            Классы в Python позволяют создавать объекты и наследование.

            Для работы с данными в Python используются библиотеки:
            - NumPy для численных вычислений
            - Pandas для анализа данных
            - Matplotlib для визуализации

            Изучение Python открывает множество возможностей для разработчика.''',
            'category': 'Программирование',
            'tags': ['python', 'алгоритмы'],
            'author': author_user
        },
        {
            'title': 'JavaScript и современная веб-разработка',
            'content': '''JavaScript - динамический язык программирования, который является одной из основных технологий веб-разработки.
            JavaScript был создан Бренданом Айком в 1995 году для браузера Netscape Navigator.

            Современная веб-разработка с JavaScript включает:

            Frontend разработка:
            - Vanilla JavaScript для базовой функциональности
            - React для создания пользовательских интерфейсов
            - Vue.js как прогрессивный фреймворк
            - Angular для корпоративных приложений

            Backend разработка с Node.js:
            - Express.js для создания веб-серверов
            - MongoDB для работы с базами данных
            - Socket.io для real-time приложений

            Ключевые концепции JavaScript:
            1. Асинхронное программирование с Promise и async/await
            2. Замыкания и область видимости
            3. Прототипное наследование
            4. Event-driven программирование
            5. Функциональное программирование

            Инструменты разработки:
            - Webpack для сборки проектов
            - Babel для транспиляции кода
            - ESLint для проверки качества кода
            - Jest для тестирования

            JavaScript непрерывно развивается. Новые возможности добавляются ежегодно.
            Изучение JavaScript открывает путь к full-stack разработке.

            Веб-программирование с JavaScript позволяет создавать интерактивные веб-приложения.''',
            'category': 'Веб-разработка',
            'tags': ['javascript', 'веб'],
            'author': author_user
        },
        {
            'title': 'Алгоритмы поиска и сортировки',
            'content': '''Алгоритмы поиска и сортировки являются фундаментальными в программировании и компьютерных науках.
            Эффективные алгоритмы критически важны для производительности приложений.

            Алгоритмы поиска:

            1. Линейный поиск (Linear Search):
            - Простейший алгоритм поиска
            - Временная сложность: O(n)
            - Подходит для неупорядоченных данных

            2. Двоичный поиск (Binary Search):
            - Работает только с отсортированными данными
            - Временная сложность: O(log n)
            - Принцип "разделяй и властвуй"

            3. Поиск в хеш-таблице:
            - Среднее время: O(1)
            - Худший случай: O(n)
            - Использует хеш-функции

            Алгоритмы сортировки:

            Простые алгоритмы:
            - Пузырьковая сортировка: O(n²)
            - Сортировка выбором: O(n²)
            - Сортировка вставками: O(n²)

            Эффективные алгоритмы:
            - Быстрая сортировка (QuickSort): O(n log n)
            - Сортировка слиянием (MergeSort): O(n log n)
            - Пирамидальная сортировка (HeapSort): O(n log n)

            Специализированные алгоритмы:
            - Сортировка подсчетом для целых чисел
            - Поразрядная сортировка для строк
            - Bucket sort для равномерно распределенных данных

            Выбор алгоритма зависит от:
            - Размера данных
            - Требований к памяти
            - Стабильности сортировки
            - Характера входных данных

            Алгоритмические навыки необходимы каждому программисту для решения сложных задач.''',
            'category': 'Алгоритмы',
            'tags': ['алгоритмы', 'данные'],
            'author': admin_user
        },
        {
            'title': 'Структуры данных в программировании',
            'content': '''Структуры данных - это способы организации и хранения данных в памяти компьютера.
            Выбор правильной структуры данных критически важен для эффективности программы.

            Основные структуры данных:

            1. Массивы (Arrays):
            - Последовательное размещение элементов в памяти
            - Быстрый доступ по индексу: O(1)
            - Фиксированный размер (в статических массивах)

            2. Связные списки (Linked Lists):
            - Динамическое размещение элементов
            - Вставка и удаление: O(1) в начале
            - Поиск элемента: O(n)

            3. Стеки (Stacks):
            - Принцип LIFO (Last In, First Out)
            - Операции push и pop: O(1)
            - Используются в рекурсии и обработке выражений

            4. Очереди (Queues):
            - Принцип FIFO (First In, First Out)
            - Операции enqueue и dequeue: O(1)
            - Применяются в алгоритмах обхода графов

            5. Деревья (Trees):
            - Иерархическая структура данных
            - Бинарные деревья поиска обеспечивают быстрый поиск
            - Сбалансированные деревья (AVL, Red-Black): O(log n)

            6. Хеш-таблицы (Hash Tables):
            - Ключ-значение структуры
            - Среднее время доступа: O(1)
            - Разрешение коллизий: цепочки или открытая адресация

            7. Графы (Graphs):
            - Вершины и рёбра
            - Представление: матрица смежности или список смежности
            - Алгоритмы: DFS, BFS, кратчайший путь

            Выбор структуры данных влияет на:
            - Время выполнения операций
            - Использование памяти
            - Сложность реализации

            Программист должен понимать компромиссы между различными структурами данных.''',
            'category': 'Алгоритмы',
            'tags': ['алгоритмы', 'данные'],
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

    print("\n=== ПРИМЕРЫ ПОИСКА ===")
    print("Попробуйте найти в документах слова:")
    print("- 'python' - найдет точные совпадения")
    print("- 'прог' - найдет части слов (программирование, программист)")
    print("- 'алгоритм' - найдет различные формы слова")
    print("- 'данных' - найдет в контексте структур данных")
    print("- 'веб' - найдет информацию о веб-разработке")


if __name__ == '__main__':
    create_test_data()