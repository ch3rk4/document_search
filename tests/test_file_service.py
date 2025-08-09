"""
Тесты для сервисов работы с файлами
"""
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

from django.core.files.uploadedfile import SimpleUploadedFile

from doc_storage.file_service import DocumentFileService, FileTextExtractor


class TestFileTextExtractor:
    """Тесты класса FileTextExtractor"""

    def test_supported_extensions(self):
        """Тест поддерживаемых расширений"""
        supported = FileTextExtractor.SUPPORTED_EXTENSIONS

        expected_extensions = {
            ".txt",
            ".text",
            ".docx",
            ".pdf",
            ".xlsx",
            ".xls",
            ".pptx",
            ".csv",
            ".md",
            ".markdown",
            ".rtf",
            ".xml",
            ".html",
            ".htm",
        }

        assert supported == expected_extensions

    def test_is_supported_file_true(self):
        """Тест проверки поддерживаемых файлов"""
        supported_files = [
            "document.txt",
            "test.docx",
            "report.pdf",
            "data.xlsx",
            "presentation.pptx",
            "readme.md",
            "page.html",
        ]

        for filename in supported_files:
            assert FileTextExtractor.is_supported_file(filename)

    def test_is_supported_file_false(self):
        """Тест проверки неподдерживаемых файлов"""
        unsupported_files = ["image.png", "video.mp4", "audio.mp3", "archive.zip", "executable.exe"]

        for filename in unsupported_files:
            assert not FileTextExtractor.is_supported_file(filename)

    def test_get_file_info_nonexistent(self):
        """Тест получения информации о несуществующем файле"""
        info = FileTextExtractor.get_file_info("/path/to/nonexistent/file.txt")

        assert "error" in info
        assert "не найден" in info["error"].lower()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_get_file_info_too_large(self, mock_stat, mock_exists):
        """Тест получения информации о слишком большом файле"""
        mock_exists.return_value = True

        # Настраиваем мок для большого размера файла
        mock_stat_result = MagicMock()
        mock_stat_result.st_size = FileTextExtractor.MAX_FILE_SIZE + 1
        mock_stat.return_value = mock_stat_result

        info = FileTextExtractor.get_file_info("large_file.txt")

        assert "error" in info
        assert "большой" in info["error"].lower()

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.stat")
    def test_get_file_info_valid(self, mock_stat, mock_exists):
        """Тест получения информации о валидном файле"""
        mock_exists.return_value = True

        mock_stat_result = MagicMock()
        mock_stat_result.st_size = 1024  # 1KB
        mock_stat.return_value = mock_stat_result

        info = FileTextExtractor.get_file_info("test.txt")

        assert "error" not in info
        assert info["name"] == "test.txt"
        assert info["size"] == 1024
        assert info["extension"] == ".txt"
        assert info["supported"] is True

    def test_detect_encoding_utf8(self):
        """Тест определения UTF-8 кодировки"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("Тестовый текст на русском языке")
            temp_path = f.name

        try:
            encoding = FileTextExtractor._detect_encoding(temp_path)
            assert encoding in ["utf-8", "UTF-8"]
        finally:
            Path(temp_path).unlink()

    @patch("chardet.detect")
    @patch("builtins.open", new_callable=mock_open, read_data=b"\xc4\xee\xea\xf3\xec\xe5\xed\xf2")
    def test_detect_encoding_windows1251(self, mock_file, mock_chardet):
        """Тест определения Windows-1251 кодировки"""
        mock_chardet.return_value = {"encoding": "windows-1251"}

        encoding = FileTextExtractor._detect_encoding("test.txt")

        assert encoding == "windows-1251"

    def test_extract_from_text_file(self):
        """Тест извлечения текста из обычного текстового файла"""
        content = "Это тестовый текст\nна нескольких строках"

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write(content)
            temp_path = f.name

        try:
            extracted_text, error = FileTextExtractor._extract_from_text_file(temp_path)

            assert error is None
            assert extracted_text == content
        finally:
            Path(temp_path).unlink()

    def test_extract_from_text_file_empty(self):
        """Тест извлечения из пустого файла"""
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write("")
            temp_path = f.name

        try:
            extracted_text, error = FileTextExtractor._extract_from_text_file(temp_path)

            assert error == "Не удалось определить кодировку файла"
            assert extracted_text == None
        finally:
            Path(temp_path).unlink()

    @patch("doc_storage.file_service.DOCX_AVAILABLE", True)
    @patch("docx.Document")
    def test_extract_from_docx_success(self, mock_docx):
        """Тест успешного извлечения из DOCX файла"""
        # Настраиваем мок
        mock_doc = MagicMock()
        mock_paragraph1 = MagicMock()
        mock_paragraph1.text = "Первый параграф"
        mock_paragraph2 = MagicMock()
        mock_paragraph2.text = "Второй параграф"
        mock_doc.paragraphs = [mock_paragraph1, mock_paragraph2]
        mock_doc.tables = []  # Нет таблиц
        mock_docx.return_value = mock_doc

        extracted_text, error = FileTextExtractor._extract_from_docx("test.docx")

        assert error is None
        assert "Первый параграф" in extracted_text
        assert "Второй параграф" in extracted_text

    @patch("doc_storage.file_service.DOCX_AVAILABLE", False)
    def test_extract_from_docx_not_available(self):
        """Тест извлечения из DOCX когда библиотека недоступна"""
        extracted_text, error = FileTextExtractor._extract_from_docx("test.docx")

        assert extracted_text is None
        assert error is not None
        assert "python-docx" in error

    @patch("doc_storage.file_service.PDF_AVAILABLE", True)
    @patch("builtins.open", new_callable=mock_open, read_data=b"PDF content")
    @patch("PyPDF2.PdfReader")
    def test_extract_from_pdf_success(self, mock_pdf_reader, mock_file):
        """Тест успешного извлечения из PDF файла"""
        # Настраиваем мок
        mock_reader = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Текст из PDF"
        mock_reader.pages = [mock_page]
        mock_pdf_reader.return_value = mock_reader

        extracted_text, error = FileTextExtractor._extract_from_pdf("test.pdf")

        assert error is None
        assert "Текст из PDF" in extracted_text

    @patch("doc_storage.file_service.PDF_AVAILABLE", False)
    def test_extract_from_pdf_not_available(self):
        """Тест извлечения из PDF когда библиотека недоступна"""
        extracted_text, error = FileTextExtractor._extract_from_pdf("test.pdf")

        assert extracted_text is None
        assert error is not None
        assert "PyPDF2" in error

    @patch("doc_storage.file_service.EXCEL_AVAILABLE", True)
    @patch("openpyxl.load_workbook")
    def test_extract_from_excel_success(self, mock_workbook):
        """Тест успешного извлечения из Excel файла"""
        # Настраиваем мок
        mock_wb = MagicMock()
        mock_wb.sheetnames = ["Sheet1"]

        mock_sheet = MagicMock()
        mock_sheet.iter_rows.return_value = [("Заголовок1", "Заголовок2"), ("Значение1", "Значение2")]
        mock_wb.__getitem__.return_value = mock_sheet

        mock_workbook.return_value = mock_wb

        extracted_text, error = FileTextExtractor._extract_from_excel("test.xlsx")

        assert error is None
        assert "Sheet1" in extracted_text
        assert "Заголовок1" in extracted_text
        assert "Значение1" in extracted_text

    @patch("doc_storage.file_service.EXCEL_AVAILABLE", False)
    def test_extract_from_excel_not_available(self):
        """Тест извлечения из Excel когда библиотека недоступна"""
        extracted_text, error = FileTextExtractor._extract_from_excel("test.xlsx")

        assert extracted_text is None
        assert error is not None
        assert "openpyxl" in error

    @patch("doc_storage.file_service.PPTX_AVAILABLE", False)
    def test_extract_from_powerpoint_not_available(self):
        """Тест извлечения из PowerPoint когда библиотека недоступна"""
        extracted_text, error = FileTextExtractor._extract_from_powerpoint("test.pptx")

        assert extracted_text is None
        assert error is not None
        assert "python-pptx" in error

    def test_extract_from_csv(self):
        """Тест извлечения из CSV файла"""
        csv_content = "Заголовок1,Заголовок2\nЗначение1,Значение2\n"

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            extracted_text, error = FileTextExtractor._extract_from_csv(temp_path)

            assert error is None
            assert "Заголовок1" in extracted_text
            assert "Значение1" in extracted_text
        finally:
            Path(temp_path).unlink()

    def test_extract_from_markup(self):
        """Тест извлечения из HTML/XML файлов"""
        html_content = "<html><body><h1>Заголовок</h1><p>Текст параграфа</p></body></html>"

        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", delete=False) as f:
            f.write(html_content)
            temp_path = f.name

        try:
            extracted_text, error = FileTextExtractor._extract_from_markup(temp_path)

            assert error is None
            assert "Заголовок" in extracted_text
            assert "Текст параграфа" in extracted_text
            assert "<html>" not in extracted_text  # HTML теги должны быть удалены
        finally:
            Path(temp_path).unlink()

    @patch.object(FileTextExtractor, "get_file_info")
    @patch.object(FileTextExtractor, "_extract_from_text_file")
    def test_extract_text_txt_file(self, mock_extract, mock_info):
        """Тест общего метода извлечения для текстового файла"""
        mock_info.return_value = {"extension": ".txt", "supported": True}
        mock_extract.return_value = ("Текст файла", None)

        text, error = FileTextExtractor.extract_text("test.txt")

        assert error is None
        assert text == "Текст файла"
        mock_extract.assert_called_once_with("test.txt")

    @patch.object(FileTextExtractor, "get_file_info")
    def test_extract_text_unsupported_file(self, mock_info):
        """Тест извлечения из неподдерживаемого файла"""
        mock_info.return_value = {"extension": ".png", "supported": False}

        text, error = FileTextExtractor.extract_text("image.png")

        assert text is None
        assert error is not None
        assert "неподдерживаемый" in error.lower()

    @patch.object(FileTextExtractor, "get_file_info")
    def test_extract_text_file_error(self, mock_info):
        """Тест извлечения при ошибке получения информации о файле"""
        mock_info.return_value = {"error": "Файл не найден"}

        text, error = FileTextExtractor.extract_text("nonexistent.txt")

        assert text is None
        assert error == "Файл не найден"


class TestDocumentFileService:
    """Тесты класса DocumentFileService"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.service = DocumentFileService()

    def test_service_initialization(self):
        """Тест инициализации сервиса"""
        assert self.service.extractor is not None
        assert isinstance(self.service.extractor, FileTextExtractor)

    @patch.object(FileTextExtractor, "extract_text")
    def test_create_document_from_file_success(self, mock_extract, db, regular_user, test_category):
        """Тест успешного создания документа из файла"""
        # Настраиваем мок
        mock_extract.return_value = ("Содержимое файла", None)

        # Создаем тестовый файл
        uploaded_file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")

        document, error = self.service.create_document_from_file(
            uploaded_file=uploaded_file, title="Тестовый документ", category=test_category, author=regular_user
        )

        assert error is None
        assert document is not None
        assert document.title == "Тестовый документ"
        assert document.content == "Содержимое файла"
        assert document.category == test_category
        assert document.author == regular_user

    @patch.object(FileTextExtractor, "extract_text")
    def test_create_document_from_file_extract_error(self, mock_extract, db):
        """Тест создания документа при ошибке извлечения"""
        mock_extract.return_value = (None, "Ошибка извлечения текста")

        uploaded_file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file)

        assert document is None
        assert error == "Ошибка извлечения текста"

    def test_create_document_large_file(self, db):
        """Тест создания документа из слишком большого файла"""
        # Создаем файл большого размера
        large_content = b"x" * (FileTextExtractor.MAX_FILE_SIZE + 1)
        uploaded_file = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file)

        assert document is None
        assert error is not None
        assert "большой" in error.lower()

    def test_create_document_unsupported_file(self, db):
        """Тест создания документа из неподдерживаемого файла"""
        uploaded_file = SimpleUploadedFile("image.png", b"PNG content", content_type="image/png")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file)

        assert document is None
        assert error is not None
        assert "неподдерживаемый" in error.lower()

    @patch.object(FileTextExtractor, "extract_text")
    def test_create_document_empty_text(self, mock_extract, db):
        """Тест создания документа с пустым текстом"""
        mock_extract.return_value = ("", None)

        uploaded_file = SimpleUploadedFile("empty.txt", b"", content_type="text/plain")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file)

        assert document is None
        assert error is not None
        assert "извлечь текст" in error.lower()

    @patch.object(FileTextExtractor, "extract_text")
    def test_create_document_auto_title(self, mock_extract, db, regular_user):
        """Тест автоматического создания заголовка"""
        mock_extract.return_value = ("Содержимое файла", None)

        uploaded_file = SimpleUploadedFile("test_document.txt", b"Test content", content_type="text/plain")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file, author=regular_user)

        assert error is None
        assert document is not None
        assert document.title == "test_document"  # Имя файла без расширения

    @patch.object(FileTextExtractor, "extract_text")
    def test_update_document_from_file_success(self, mock_extract, test_document):
        """Тест успешного обновления документа из файла"""
        mock_extract.return_value = ("Новое содержимое", None)

        uploaded_file = SimpleUploadedFile("updated.txt", b"New content", content_type="text/plain")

        success, error = self.service.update_document_from_file(document=test_document, uploaded_file=uploaded_file)

        assert success is True
        assert error is None

        # Проверяем обновление
        test_document.refresh_from_db()
        assert test_document.content == "Новое содержимое"

    @patch.object(FileTextExtractor, "extract_text")
    def test_update_document_from_file_error(self, mock_extract, test_document):
        """Тест обновления документа при ошибке извлечения"""
        mock_extract.return_value = (None, "Ошибка чтения файла")

        uploaded_file = SimpleUploadedFile("error.txt", b"Content", content_type="text/plain")

        success, error = self.service.update_document_from_file(document=test_document, uploaded_file=uploaded_file)

        assert success is False
        assert error == "Ошибка чтения файла"

    def test_update_document_large_file(self, test_document):
        """Тест обновления документа файлом большого размера"""
        large_content = b"x" * (FileTextExtractor.MAX_FILE_SIZE + 1)
        uploaded_file = SimpleUploadedFile("large.txt", large_content, content_type="text/plain")

        success, error = self.service.update_document_from_file(document=test_document, uploaded_file=uploaded_file)

        assert success is False
        assert error is not None
        assert "большой" in error.lower()

    def test_get_supported_formats_info(self):
        """Тест получения информации о поддерживаемых форматах"""
        info = self.service.get_supported_formats_info()

        assert "extensions" in info
        assert "max_file_size_mb" in info
        assert "available_extractors" in info

        # Проверяем содержимое
        assert isinstance(info["extensions"], list)
        assert ".txt" in info["extensions"]
        assert ".docx" in info["extensions"]

        assert isinstance(info["max_file_size_mb"], int)
        assert info["max_file_size_mb"] == 50

        extractors = info["available_extractors"]
        assert "docx" in extractors
        assert "pdf" in extractors
        assert "excel" in extractors

    @patch("tempfile.NamedTemporaryFile")
    @patch("os.unlink")
    def test_save_temp_file(self, mock_unlink, mock_tempfile):
        """Тест сохранения временного файла"""
        # Настраиваем мок
        mock_temp = MagicMock()
        mock_temp.name = "/tmp/test_file.txt"
        mock_temp.write = MagicMock()
        mock_temp.close = MagicMock()
        mock_tempfile.return_value = mock_temp

        uploaded_file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")
        uploaded_file.chunks = MagicMock(return_value=[b"Test content"])

        temp_path = self.service._save_temp_file(uploaded_file)

        assert temp_path == "/tmp/test_file.txt"
        mock_temp.write.assert_called_with(b"Test content")
        mock_temp.close.assert_called_once()


class TestFileServiceIntegration:
    """Интеграционные тесты сервиса работы с файлами"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.service = DocumentFileService()

    def test_full_workflow_text_file(self, db, regular_user, test_category):
        """Тест полного рабочего процесса с текстовым файлом"""
        # Создаем настоящий временный файл
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write("Это тестовый документ с русским текстом.")
            temp_path = f.name

        try:
            # Читаем файл как uploaded file
            with open(temp_path, "rb") as f:
                uploaded_file = SimpleUploadedFile("test_document.txt", f.read(), content_type="text/plain")

            # Создаем документ
            document, error = self.service.create_document_from_file(
                uploaded_file=uploaded_file, title="Интеграционный тест", category=test_category, author=regular_user
            )

            assert error is None
            assert document is not None
            assert document.title == "Интеграционный тест"
            assert "русским текстом" in document.content
            assert document.word_count > 0

        finally:
            Path(temp_path).unlink()

    def test_error_handling_workflow(self, db, regular_user):
        """Тест обработки ошибок в рабочем процессе"""
        # Создаем файл с неподдерживаемым расширением
        uploaded_file = SimpleUploadedFile(
            "test.unknown", b"Unknown format content", content_type="application/unknown"
        )

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file, author=regular_user)

        assert document is None
        assert error is not None
        assert "неподдерживаемый" in error.lower()

    def test_encoding_detection_workflow(self, db, regular_user):
        """Тест определения кодировки в рабочем процессе"""
        # Создаем файл в разных кодировках
        russian_text = "Тестовый текст на русском языке"

        # UTF-8
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".txt", delete=False) as f:
            f.write(russian_text)
            utf8_path = f.name

        try:
            with open(utf8_path, "rb") as f:
                uploaded_file = SimpleUploadedFile("utf8_test.txt", f.read(), content_type="text/plain")

            document, error = self.service.create_document_from_file(uploaded_file=uploaded_file, author=regular_user)

            assert error is None
            assert document is not None
            assert "русском языке" in document.content

        finally:
            Path(utf8_path).unlink()


class TestFileServiceErrorHandling:
    """Тесты обработки ошибок в файловом сервисе"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.service = DocumentFileService()

    @patch.object(FileTextExtractor, "extract_text")
    def test_create_document_exception_handling(self, mock_extract, db):
        """Тест обработки исключений при создании документа"""
        # Настраиваем мок для генерации исключения
        mock_extract.side_effect = Exception("Неожиданная ошибка")

        uploaded_file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file)

        assert document is None
        assert error is not None
        assert "ошибка при создании документа" in error.lower()

    @patch.object(FileTextExtractor, "extract_text")
    def test_update_document_exception_handling(self, mock_extract, test_document):
        """Тест обработки исключений при обновлении документа"""
        mock_extract.side_effect = Exception("Неожиданная ошибка")

        uploaded_file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")

        success, error = self.service.update_document_from_file(document=test_document, uploaded_file=uploaded_file)

        assert success is False
        assert error is not None
        assert "ошибка при обновлении документа" in error.lower()

    @patch("tempfile.NamedTemporaryFile")
    def test_temp_file_creation_error(self, mock_tempfile):
        """Тест ошибки создания временного файла"""
        mock_tempfile.side_effect = OSError("Невозможно создать временный файл")

        uploaded_file = SimpleUploadedFile("test.txt", b"Test content", content_type="text/plain")

        document, error = self.service.create_document_from_file(uploaded_file=uploaded_file)

        assert document is None
        assert error is not None


class TestFileValidation:
    """Тесты валидации файлов"""

    def test_validate_file_size_limits(self):
        """Тест ограничений размера файла"""
        max_size = FileTextExtractor.MAX_FILE_SIZE

        # Файл в пределах лимита
        normal_file = SimpleUploadedFile("normal.txt", b"x" * (max_size // 2), content_type="text/plain")
        assert normal_file.size <= max_size

        # Файл превышающий лимит
        large_file = SimpleUploadedFile("large.txt", b"x" * (max_size + 1), content_type="text/plain")
        assert large_file.size > max_size

    def test_validate_file_extensions(self):
        """Тест валидации расширений файлов"""
        test_cases = [
            ("document.txt", True),
            ("document.TXT", True),  # Разный регистр
            ("document.docx", True),
            ("document.pdf", True),
            ("image.png", False),
            ("video.mp4", False),
            ("archive.zip", False),
            ("no_extension", False),
        ]

        for filename, expected in test_cases:
            result = FileTextExtractor.is_supported_file(filename)
            assert result == expected, f"Для {filename} ожидалось {expected}, получено {result}"
