"""
Сервис для извлечения текста из различных типов файлов
"""
import os
import mimetypes
import chardet
import tempfile
from typing import Optional, Tuple
from pathlib import Path

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    docx = None
    DOCX_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PyPDF2 = None
    PDF_AVAILABLE = False

try:
    import openpyxl
    EXCEL_AVAILABLE = True
except ImportError:
    openpyxl = None
    EXCEL_AVAILABLE = False

try:
    from pptx import Presentation
    PPTX_AVAILABLE = True
except ImportError:
    Presentation = None
    PPTX_AVAILABLE = False


class FileTextExtractor:
    """Класс для извлечения текста из различных типов файлов"""

    SUPPORTED_EXTENSIONS = {
        '.txt', '.text',
        '.docx',
        '.pdf',
        '.xlsx', '.xls',
        '.pptx',
        '.csv',
        '.md', '.markdown',
        '.rtf',
        '.xml', '.html', '.htm'
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

    @classmethod
    def is_supported_file(cls, file_path: str) -> bool:
        """Проверка, поддерживается ли тип файла"""
        extension = Path(file_path).suffix.lower()
        return extension in cls.SUPPORTED_EXTENSIONS

    @classmethod
    def get_file_info(cls, file_path: str) -> dict:
        """Получение информации о файле"""
        file_path = Path(file_path)

        if not file_path.exists():
            return {'error': 'Файл не найден'}

        file_size = file_path.stat().st_size
        if file_size > cls.MAX_FILE_SIZE:
            return {'error': f'Файл слишком большой (максимум {cls.MAX_FILE_SIZE // (1024 * 1024)}MB)'}

        mime_type, _ = mimetypes.guess_type(str(file_path))

        return {
            'name': file_path.name,
            'size': file_size,
            'extension': file_path.suffix.lower(),
            'mime_type': mime_type,
            'supported': cls.is_supported_file(str(file_path))
        }

    @classmethod
    def extract_text(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Извлечение текста из файла
        Возвращает: (извлеченный_текст, ошибка)
        """
        try:
            file_info = cls.get_file_info(file_path)

            if 'error' in file_info:
                return None, file_info['error']

            if not file_info['supported']:
                return None, f"Неподдерживаемый тип файла: {file_info['extension']}"

            extension = file_info['extension']

            # Обработка различных типов файлов
            if extension in ['.txt', '.text', '.md', '.markdown']:
                return cls._extract_from_text_file(file_path)
            elif extension == '.docx':
                return cls._extract_from_docx(file_path)
            elif extension == '.pdf':
                return cls._extract_from_pdf(file_path)
            elif extension in ['.xlsx', '.xls']:
                return cls._extract_from_excel(file_path)
            elif extension in ['.pptx']:
                return cls._extract_from_powerpoint(file_path)
            elif extension == '.csv':
                return cls._extract_from_csv(file_path)
            elif extension in ['.xml', '.html', '.htm']:
                return cls._extract_from_markup(file_path)
            else:
                return None, f"Обработчик для {extension} файлов не реализован"

        except Exception as e:
            return None, f"Ошибка при обработке файла: {str(e)}"

    @classmethod
    def _detect_encoding(cls, file_path: str) -> str:
        """Определение кодировки файла"""
        try:
            with open(file_path, 'rb') as file:
                raw_data = file.read(10000)  # Читаем первые 10KB
                result = chardet.detect(raw_data)
                encoding = result.get('encoding', 'utf-8')
                if encoding is None:
                    encoding = 'utf-8'
                # Проверяем на популярные кодировки
                if encoding.lower() in ['windows-1251', 'cp1251']:
                    return 'windows-1251'
                return encoding
        except Exception:
            return 'utf-8'

    @classmethod
    def _extract_from_text_file(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из обычного текстового файла"""
        try:
            encoding = cls._detect_encoding(file_path)

            # Пробуем разные кодировки
            encodings_to_try = [encoding, 'utf-8', 'windows-1251', 'cp1251', 'latin-1']

            for enc in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=enc, errors='ignore') as file:
                        content = file.read()

                    if content.strip():
                        return content, None
                except UnicodeDecodeError:
                    continue

            return None, "Не удалось определить кодировку файла"

        except Exception as e:
            return None, f"Ошибка чтения текстового файла: {str(e)}"

    @classmethod
    def _extract_from_docx(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из файла Word (.docx)"""
        if not DOCX_AVAILABLE:
            return None, "Для работы с .docx файлами установите библиотеку: pip install python-docx"

        try:
            doc = docx.Document(file_path)

            # Извлекаем текст из всех параграфов
            paragraphs = []
            for paragraph in doc.paragraphs:
                text = paragraph.text.strip()
                if text:
                    paragraphs.append(text)

            # Извлекаем текст из таблиц
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        text = cell.text.strip()
                        if text:
                            paragraphs.append(text)

            content = '\n\n'.join(paragraphs)

            if not content.strip():
                return None, "Документ Word не содержит текста"

            return content, None

        except Exception as e:
            return None, f"Ошибка чтения файла Word: {str(e)}"

    @classmethod
    def _extract_from_pdf(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из PDF файла"""
        if not PDF_AVAILABLE:
            return None, "Для работы с PDF файлами установите библиотеку: pip install PyPDF2"

        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)

                if len(pdf_reader.pages) == 0:
                    return None, "PDF файл не содержит страниц"

                pages_text = []
                for page in pdf_reader.pages:
                    try:
                        text = page.extract_text()
                        if text.strip():
                            pages_text.append(text.strip())
                    except Exception:
                        continue  # Пропускаем проблемные страницы

                content = '\n\n'.join(pages_text)

                if not content.strip():
                    return None, "PDF файл не содержит извлекаемого текста"

                return content, None

        except Exception as e:
            return None, f"Ошибка чтения PDF файла: {str(e)}"

    @classmethod
    def _extract_from_excel(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из файла Excel"""
        if not EXCEL_AVAILABLE:
            return None, "Для работы с Excel файлами установите библиотеку: pip install openpyxl"

        try:
            # Используем openpyxl для .xlsx и .xls
            workbook = openpyxl.load_workbook(file_path, data_only=True, read_only=True)
            sheets_text = []

            for sheet_name in workbook.sheetnames:
                sheet = workbook[sheet_name]
                sheet_text = []

                for row in sheet.iter_rows(values_only=True):
                    row_text = []
                    for cell_value in row:
                        if cell_value is not None:
                            row_text.append(str(cell_value))
                    if row_text:
                        sheet_text.append(' | '.join(row_text))

                if sheet_text:
                    sheets_text.append(f"=== Лист: {sheet_name} ===\n" + '\n'.join(sheet_text))

            content = '\n\n'.join(sheets_text)

            if not content.strip():
                return None, "Excel файл не содержит данных"

            return content, None

        except Exception as e:
            return None, f"Ошибка чтения Excel файла: {str(e)}"

    @classmethod
    def _extract_from_powerpoint(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из файла PowerPoint"""
        if not PPTX_AVAILABLE:
            return None, "Для работы с PowerPoint файлами установите библиотеку: pip install python-pptx"

        try:
            prs = Presentation(file_path)
            slides_text = []

            for i, slide in enumerate(prs.slides, 1):
                slide_text = [f"=== Слайд {i} ==="]

                for shape in slide.shapes:
                    if hasattr(shape, "text") and shape.text.strip():
                        slide_text.append(shape.text.strip())

                if len(slide_text) > 1:  # Больше чем только заголовок слайда
                    slides_text.append('\n'.join(slide_text))

            content = '\n\n'.join(slides_text)

            if not content.strip():
                return None, "PowerPoint файл не содержит текста"

            return content, None

        except Exception as e:
            return None, f"Ошибка чтения PowerPoint файла: {str(e)}"

    @classmethod
    def _extract_from_csv(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из CSV файла"""
        try:
            encoding = cls._detect_encoding(file_path)

            # Пробуем разные кодировки для CSV
            encodings_to_try = [encoding, 'utf-8', 'windows-1251', 'cp1251']

            for enc in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=enc, errors='ignore') as file:
                        lines = file.readlines()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return None, "Не удалось прочитать CSV файл"

            if not lines:
                return None, "CSV файл пустой"

            # Обрабатываем CSV как текст с разделителями
            content = ''.join(lines)

            return content, None

        except Exception as e:
            return None, f"Ошибка чтения CSV файла: {str(e)}"

    @classmethod
    def _extract_from_markup(cls, file_path: str) -> Tuple[Optional[str], Optional[str]]:
        """Извлечение текста из HTML/XML файлов"""
        try:
            encoding = cls._detect_encoding(file_path)

            encodings_to_try = [encoding, 'utf-8', 'windows-1251', 'cp1251']

            for enc in encodings_to_try:
                try:
                    with open(file_path, 'r', encoding=enc, errors='ignore') as file:
                        content = file.read()
                    break
                except UnicodeDecodeError:
                    continue
            else:
                return None, "Не удалось прочитать HTML/XML файл"

            # Простое удаление HTML тегов
            import re
            text = re.sub(r'<[^>]+>', ' ', content)
            text = re.sub(r'\s+', ' ', text).strip()

            if not text:
                return None, "HTML/XML файл не содержит текста"

            return text, None

        except Exception as e:
            return None, f"Ошибка чтения HTML/XML файла: {str(e)}"


class DocumentFileService:
    """Сервис для создания документов из загруженных файлов"""

    def __init__(self):
        self.extractor = FileTextExtractor()

    def create_document_from_file(self, uploaded_file, title: str = None, category=None, author=None) -> Tuple[
        Optional['Document'], Optional[str]]:
        """
        Создание документа из загруженного файла

        Args:
            uploaded_file: Django UploadedFile объект
            title: Заголовок документа (если не указан, берется из имени файла)
            category: Категория документа
            author: Автор документа

        Returns:
            (document, error_message)
        """
        from .models import Document

        try:
            # Проверяем размер файла
            if uploaded_file.size > self.extractor.MAX_FILE_SIZE:
                return None, f"Файл слишком большой (максимум {self.extractor.MAX_FILE_SIZE // (1024 * 1024)}MB)"

            # Проверяем тип файла
            file_name = uploaded_file.name
            if not self.extractor.is_supported_file(file_name):
                return None, f"Неподдерживаемый тип файла: {Path(file_name).suffix}"

            # Сохраняем временный файл для обработки
            temp_file_path = self._save_temp_file(uploaded_file)

            try:
                # Извлекаем текст
                extracted_text, error = self.extractor.extract_text(temp_file_path)

                if error:
                    return None, error

                if not extracted_text or not extracted_text.strip():
                    return None, "Не удалось извлечь текст из файла"

                # Создаем заголовок если не указан
                if not title:
                    title = Path(file_name).stem  # Имя файла без расширения

                # Создаем документ
                document = Document.objects.create(
                    title=title,
                    content=extracted_text,
                    file_path=uploaded_file,
                    category=category,
                    author=author
                )

                return document, None

            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

        except Exception as e:
            return None, f"Ошибка при создании документа: {str(e)}"

    def _save_temp_file(self, uploaded_file) -> str:
        """Сохранение временного файла для обработки"""
        # Создаем временный файл с правильным расширением
        file_extension = Path(uploaded_file.name).suffix
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension
        )

        # Записываем содержимое
        for chunk in uploaded_file.chunks():
            temp_file.write(chunk)

        temp_file.close()
        return temp_file.name

    def update_document_from_file(self, document, uploaded_file) -> Tuple[bool, Optional[str]]:
        """
        Обновление существующего документа из файла

        Returns:
            (success, error_message)
        """
        try:
            # Проверяем размер файла
            if uploaded_file.size > self.extractor.MAX_FILE_SIZE:
                return False, f"Файл слишком большой (максимум {self.extractor.MAX_FILE_SIZE // (1024 * 1024)}MB)"

            # Проверяем тип файла
            if not self.extractor.is_supported_file(uploaded_file.name):
                return False, f"Неподдерживаемый тип файла: {Path(uploaded_file.name).suffix}"

            # Сохраняем временный файл
            temp_file_path = self._save_temp_file(uploaded_file)

            try:
                # Извлекаем текст
                extracted_text, error = self.extractor.extract_text(temp_file_path)

                if error:
                    return False, error

                if not extracted_text or not extracted_text.strip():
                    return False, "Не удалось извлечь текст из файла"

                # Обновляем документ
                document.content = extracted_text
                document.file_path = uploaded_file
                document.save()

                return True, None

            finally:
                # Удаляем временный файл
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    pass

        except Exception as e:
            return False, f"Ошибка при обновлении документа: {str(e)}"

    def get_supported_formats_info(self) -> dict:
        """Получение информации о поддерживаемых форматах"""
        return {
            'extensions': list(self.extractor.SUPPORTED_EXTENSIONS),
            'max_file_size_mb': self.extractor.MAX_FILE_SIZE // (1024 * 1024),
            'available_extractors': {
                'docx': DOCX_AVAILABLE,
                'pdf': PDF_AVAILABLE,
                'excel': EXCEL_AVAILABLE,
                'powerpoint': PPTX_AVAILABLE,
            }
        }