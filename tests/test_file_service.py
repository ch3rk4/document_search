import tempfile
import os
from pathlib import Path
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from doc_storage.models import Document, DocumentCategory
from doc_storage.file_service import FileTextExtractor, DocumentFileService


class FileTextExtractorTest(TestCase):
    """Тесты для извлечения текста из файлов"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.extractor = FileTextExtractor()
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Очистка временных файлов"""
        import shutil
        try:
            shutil.rmtree(self.temp_dir)
        except Exception:
            pass

    def create_test_file(self, filename: str, content: str = "Тестовое содержимое файла") -> str:
        """Создание тестового файла"""
        file_path = Path(self.temp_dir) / filename

        # Для текстовых файлов записываем как есть
        if filename.endswith(('.txt', '.md', '.html', '.xml', '.csv')):
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            # Для бинарных файлов создаем пустой файл
            with open(file_path, 'wb') as f:
                f.write(b'')

        return str(file_path)

    def test_is_supported_file(self):
        """Тест проверки поддерживаемых типов файлов"""
        supported_files = [
            'document.txt', 'document.docx', 'document.pdf',
            'document.xlsx', 'document.pptx', 'document.csv',
            'document.md', 'document.html'
        ]

        unsupported_files = [
            'document.exe', 'document.bin', 'document.mp3',
            'document.jpg', 'document.mp4'
        ]

        for filename in supported_files:
            self.assertTrue(
                self.extractor.is_supported_file(filename),
                f"Файл {filename} должен поддерживаться"
            )

        for filename in unsupported_files:
            self.assertFalse(
                self.extractor.is_supported_file(filename),
                f"Файл {filename} не должен поддерживаться"
            )

    def test_text_file_extraction(self):
        """Тест извлечения текста из текстового файла"""
        test_content = "Это тестовый текст для проверки извлечения.\nВторая строка текста."
        file_path = self.create_test_file('test.txt', test_content)

        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(error)
        self.assertIsNotNone(extracted_text)
        self.assertIn("тестовый текст", extracted_text)

    def test_markdown_file_extraction(self):
        """Тест извлечения текста из Markdown файла"""
        test_content = """# Заголовок

Это **жирный** текст в markdown файле.

## Подзаголовок

- Элемент списка 1
- Элемент списка 2

Обычный текст с `кодом`."""

        file_path = self.create_test_file('test.md', test_content)
        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(error)
        self.assertIsNotNone(extracted_text)
        self.assertIn("Заголовок", extracted_text)
        self.assertIn("жирный", extracted_text)

    def test_html_file_extraction(self):
        """Тест извлечения текста из HTML файла"""
        test_content = """<!DOCTYPE html>
<html>
<head>
    <title>Тестовая страница</title>
</head>
<body>
    <h1>Заголовок страницы</h1>
    <p>Это абзац с <strong>важным</strong> текстом.</p>
    <div>Содержимое в div</div>
</body>
</html>"""

        file_path = self.create_test_file('test.html', test_content)
        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(error)
        self.assertIsNotNone(extracted_text)
        self.assertIn("Заголовок страницы", extracted_text)
        self.assertIn("важным", extracted_text)
        # HTML теги должны быть удалены
        self.assertNotIn("<h1>", extracted_text)
        self.assertNotIn("<strong>", extracted_text)

    def test_csv_file_extraction(self):
        """Тест извлечения текста из CSV файла"""
        test_content = """Имя,Возраст,Город
Алексей,25,Москва
Мария,30,Санкт-Петербург
Дмитрий,28,Новосибирск"""

        file_path = self.create_test_file('test.csv', test_content)
        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(error)
        self.assertIsNotNone(extracted_text)
        self.assertIn("Алексей", extracted_text)
        self.assertIn("Москва", extracted_text)

    def test_nonexistent_file(self):
        """Тест обработки несуществующего файла"""
        extracted_text, error = self.extractor.extract_text('/path/to/nonexistent/file.txt')

        self.assertIsNone(extracted_text)
        self.assertIsNotNone(error)
        self.assertIn("не найден", error)

    def test_empty_file(self):
        """Тест обработки пустого файла"""
        file_path = self.create_test_file('empty.txt', '')
        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(extracted_text)
        self.assertIsNotNone(error)
        self.assertIn("пустой", error)

    def test_unsupported_file_type(self):
        """Тест обработки неподдерживаемого типа файла"""
        file_path = self.create_test_file('test.exe', 'binary content')
        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(extracted_text)
        self.assertIsNotNone(error)
        self.assertIn("Неподдерживаемый тип файла", error)

    def test_large_file_handling(self):
        """Тест обработки большого файла"""
        # Создаем файл размером больше лимита
        large_content = "A" * (self.extractor.MAX_FILE_SIZE + 1000)
        file_path = self.create_test_file('large.txt', large_content)

        # Принудительно увеличиваем размер файла
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(large_content)

        extracted_text, error = self.extractor.extract_text(file_path)

        self.assertIsNone(extracted_text)
        self.assertIsNotNone(error)
        self.assertIn("слишком большой", error)

    def test_encoding_detection(self):
        """Тест определения кодировки файла"""
        # Создаем файл с русским текстом в windows-1251
        test_content = "Привет мир! Это текст на русском языке."
        file_path = Path(self.temp_dir) / 'test_encoding.txt'

        # Записываем в windows-1251
        with open(file_path, 'w', encoding='windows-1251') as f:
            f.write(test_content)

        detected_encoding = self.extractor._detect_encoding(str(file_path))
        self.assertIsNotNone(detected_encoding)

        # Проверяем, что можем прочитать файл
        extracted_text, error = self.extractor.extract_text(str(file_path))
        self.assertIsNone(error)
        self.assertIn("Привет мир", extracted_text)


class DocumentFileServiceTest(TestCase):
    """Тесты для сервиса создания документов из файлов"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.category = DocumentCategory.objects.create(
            name='Тестовая категория',
            description='Описание категории'
        )
        self.file_service = DocumentFileService()

    def create_uploaded_file(self, filename: str, content: str = "Тестовое содержимое файла") -> SimpleUploadedFile:
        """Создание объекта загруженного файла для тестов"""
        return SimpleUploadedFile(
            filename,
            content.encode('utf-8'),
            content_type='text/plain'
        )

    def test_create_document_from_text_file(self):
        """Тест создания документа из текстового файла"""
        test_content = "Это содержимое документа для тестирования создания python программирование"
        uploaded_file = self.create_uploaded_file('test_document.txt', test_content)

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title='Тестовый документ',
            category=self.category,
            author=self.user
        )

        self.assertIsNone(error)
        self.assertIsNotNone(document)
        self.assertEqual(document.title, 'Тестовый документ')
        self.assertEqual(document.author, self.user)
        self.assertEqual(document.category, self.category)
        self.assertIn("тестирования", document.content)
        self.assertGreater(document.word_count, 0)

    def test_create_document_without_title(self):
        """Тест создания документа без указания заголовка"""
        test_content = "Содержимое документа без заголовка"
        uploaded_file = self.create_uploaded_file('автоматический_заголовок.txt', test_content)

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            author=self.user
        )

        self.assertIsNone(error)
        self.assertIsNotNone(document)
        self.assertEqual(document.title, 'автоматический_заголовок')  # Имя файла без расширения

    def test_create_document_from_unsupported_file(self):
        """Тест создания документа из неподдерживаемого файла"""
        uploaded_file = self.create_uploaded_file('test.exe', 'binary content')

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            author=self.user
        )

        self.assertIsNone(document)
        self.assertIsNotNone(error)
        self.assertIn("Неподдерживаемый тип файла", error)

    def test_create_document_from_large_file(self):
        """Тест создания документа из слишком большого файла"""
        # Создаем файл, который превышает лимит
        large_content = "A" * (self.file_service.extractor.MAX_FILE_SIZE + 1000)
        uploaded_file = SimpleUploadedFile(
            'large_file.txt',
            large_content.encode('utf-8'),
            content_type='text/plain'
        )

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            author=self.user
        )

        self.assertIsNone(document)
        self.assertIsNotNone(error)
        self.assertIn("слишком большой", error)

    def test_update_document_from_file(self):
        """Тест обновления существующего документа из файла"""
        # Создаем исходный документ
        original_document = Document.objects.create(
            title='Исходный документ',
            content='Исходное содержимое',
            author=self.user
        )

        # Создаем новый файл для обновления
        new_content = "Новое содержимое документа после обновления из файла python разработка"
        uploaded_file = self.create_uploaded_file('updated.txt', new_content)

        success, error = self.file_service.update_document_from_file(
            document=original_document,
            uploaded_file=uploaded_file
        )

        self.assertTrue(success)
        self.assertIsNone(error)

        # Перезагружаем документ из БД
        original_document.refresh_from_db()

        self.assertIn("обновления", original_document.content)
        self.assertNotIn("Исходное содержимое", original_document.content)
        self.assertGreater(original_document.word_count, 0)

    def test_get_supported_formats_info(self):
        """Тест получения информации о поддерживаемых форматах"""
        formats_info = self.file_service.get_supported_formats_info()

        self.assertIn('extensions', formats_info)
        self.assertIn('max_file_size_mb', formats_info)
        self.assertIn('available_extractors', formats_info)

        # Проверяем, что некоторые основные форматы поддерживаются
        extensions = formats_info['extensions']
        self.assertIn('.txt', extensions)
        self.assertIn('.csv', extensions)
        self.assertIn('.md', extensions)

    def test_markdown_file_processing(self):
        """Тест обработки Markdown файла"""
        markdown_content = """# Заголовок документа

Это **важный** текст в markdown формате.

## Подзаголовок

Список задач:
- Первая задача
- Вторая задача

Код на Python:
```python
print("Hello, World!")
```

Обычный текст с python программированием."""

        uploaded_file = self.create_uploaded_file('document.md', markdown_content)

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title='Markdown документ',
            author=self.user
        )

        self.assertIsNone(error)
        self.assertIsNotNone(document)
        self.assertIn("Заголовок документа", document.content)
        self.assertIn("важный", document.content)
        self.assertIn("python программированием", document.content)

    def test_html_file_processing(self):
        """Тест обработки HTML файла"""
        html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Тестовая HTML страница</title>
</head>
<body>
    <h1>Основной заголовок</h1>
    <p>Это абзац с <strong>важным текстом</strong> и python программированием.</p>
    <div>
        <p>Второй абзац в div.</p>
        <ul>
            <li>Первый элемент списка</li>
            <li>Второй элемент</li>
        </ul>
    </div>
</body>
</html>"""

        uploaded_file = self.create_uploaded_file('document.html', html_content)

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title='HTML документ',
            author=self.user
        )

        self.assertIsNone(error)
        self.assertIsNotNone(document)

        # HTML теги должны быть удалены, но содержимое сохранено
        self.assertIn("Основной заголовок", document.content)
        self.assertIn("важным текстом", document.content)
        self.assertIn("python программированием", document.content)
        # HTML теги не должны присутствовать
        self.assertNotIn("<h1>", document.content)
        self.assertNotIn("<strong>", document.content)

    def test_csv_file_processing(self):
        """Тест обработки CSV файла"""
        csv_content = """Название,Язык,Тип,Описание
Python,Python,Язык программирования,Высокоуровневый язык
JavaScript,JavaScript,Язык программирования,Для веб-разработки
HTML,HTML,Разметка,Язык разметки веб-страниц"""

        uploaded_file = self.create_uploaded_file('languages.csv', csv_content)

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title='Языки программирования',
            author=self.user
        )

        self.assertIsNone(error)
        self.assertIsNotNone(document)
        self.assertIn("Python", document.content)
        self.assertIn("программирования", document.content)
        self.assertIn("JavaScript", document.content)

    def test_file_with_different_encodings(self):
        """Тест файлов с разными кодировками"""
        russian_text = "Привет мир! Это текст на русском языке с python программированием."

        # Создаем файл в UTF-8
        file_path_utf8 = Path(self.temp_dir) / 'utf8.txt'
        with open(file_path_utf8, 'w', encoding='utf-8') as f:
            f.write(russian_text)

        extracted_text, error = self.extractor.extract_text(str(file_path_utf8))
        self.assertIsNone(error)
        self.assertIn("Привет мир", extracted_text)

        # Создаем файл в windows-1251
        file_path_cp1251 = Path(self.temp_dir) / 'cp1251.txt'
        with open(file_path_cp1251, 'w', encoding='windows-1251') as f:
            f.write(russian_text)

        extracted_text, error = self.extractor.extract_text(str(file_path_cp1251))
        self.assertIsNone(error)
        self.assertIn("Привет мир", extracted_text)

    def test_document_creation_saves_file_path(self):
        """Тест сохранения пути к файлу при создании документа"""
        test_content = "Содержимое для проверки сохранения пути к файлу"
        uploaded_file = self.create_uploaded_file('path_test.txt', test_content)

        document, error = self.file_service.create_document_from_file(
            uploaded_file=uploaded_file,
            title='Документ с файлом',
            author=self.user
        )

        self.assertIsNone(error)
        self.assertIsNotNone(document)
        self.assertTrue(bool(document.file_path))  # Путь к файлу должен быть сохранен

    def test_document_update_preserves_metadata(self):
        """Тест сохранения метаданных при обновлении документа"""
        # Создаем исходный документ
        original_document = Document.objects.create(
            title='Документ для обновления',
            content='Исходное содержимое',
            author=self.user,
            category=self.category
        )

        original_created_at = original_document.created_at
        original_author = original_document.author
        original_category = original_document.category

        # Обновляем из файла
        new_content = "Обновленное содержимое с python разработкой"
        uploaded_file = self.create_uploaded_file('update.txt', new_content)

        success, error = self.file_service.update_document_from_file(
            document=original_document,
            uploaded_file=uploaded_file
        )

        self.assertTrue(success)
        self.assertIsNone(error)

        # Перезагружаем документ
        original_document.refresh_from_db()

        # Проверяем, что метаданные сохранились
        self.assertEqual(original_document.created_at, original_created_at)
        self.assertEqual(original_document.author, original_author)
        self.assertEqual(original_document.category, original_category)

        # Но содержимое обновилось
        self.assertIn("Обновленное содержимое", original_document.content)
        self.assertNotIn("Исходное содержимое", original_document.content)