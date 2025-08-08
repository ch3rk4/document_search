# mypy: ignore-errors

from pathlib import Path
from typing import Any

from django import forms
from django.core.exceptions import ValidationError

from .file_service import FileTextExtractor
from .models import Document, DocumentCategory, DocumentTag


class DocumentUploadForm(forms.Form):  # type: ignore
    """Форма для загрузки документа из файла"""

    file = forms.FileField(
        label="Выберите файл",
        help_text="Поддерживаемые форматы: .txt, .docx, .pdf, .xlsx, .pptx, .csv, .md, .html",
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".txt,.docx,.pdf,.xlsx,.pptx,.csv,.md,.html,.htm,.xml"}
        ),
    )

    title = forms.CharField(
        label="Заголовок документа",
        max_length=255,
        required=False,
        help_text="Если не указан, будет использовано имя файла",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите заголовок или оставьте пустым"}),
    )

    category = forms.ModelChoiceField(
        label="Категория",
        queryset=DocumentCategory.objects.all(),
        required=False,
        empty_label="Выберите категорию",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    tags = forms.ModelMultipleChoiceField(
        label="Теги",
        queryset=DocumentTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
    )

    def clean_file(self) -> Any:
        """Валидация загружаемого файла"""
        file = self.cleaned_data.get("file")

        if not file:
            return file

        # Проверяем размер файла
        if file.size > FileTextExtractor.MAX_FILE_SIZE:
            raise ValidationError(
                f"Файл слишком большой. Максимальный размер: {FileTextExtractor.MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

        # Проверяем тип файла
        file_extension = Path(file.name).suffix.lower()
        if not FileTextExtractor.is_supported_file(file.name):
            supported_extensions = ", ".join(sorted(FileTextExtractor.SUPPORTED_EXTENSIONS))
            raise ValidationError(
                f"Неподдерживаемый тип файла: {file_extension}. " f"Поддерживаемые форматы: {supported_extensions}"
            )

        return file

    def clean_title(self) -> str:
        """Валидация заголовка"""
        title = self.cleaned_data.get("title", "").strip()

        # Если заголовок не указан, будем использовать имя файла
        if not title:
            return title

        # Проверяем уникальность заголовка только среди активных документов
        if Document.objects.filter(title=title, is_active=True).exists():
            raise ValidationError("Документ с таким заголовком уже существует")

        return title


class DocumentEditForm(forms.ModelForm):  # type: ignore
    """Форма для редактирования документа"""

    class Meta:
        model = Document
        fields = ["title", "content", "category", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите заголовок документа"}),
            "content": forms.Textarea(
                attrs={"class": "form-control", "rows": 15, "placeholder": "Введите содержимое документа..."}
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        category_field = self.fields["category"]
        if hasattr(category_field, "empty_label"):
            category_field.empty_label = "Выберите категорию"  # type: ignore[misc]
        if hasattr(category_field, "queryset"):
            category_field.queryset = DocumentCategory.objects.all()  # type: ignore[misc]


class DocumentCreateForm(forms.ModelForm):  # type: ignore
    """Форма для создания документа вручную"""

    tags = forms.ModelMultipleChoiceField(
        label="Теги",
        queryset=DocumentTag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={"class": "form-check-input"}),
    )

    class Meta:
        model = Document
        fields = ["title", "content", "category"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Введите заголовок документа"}),
            "content": forms.Textarea(
                attrs={"class": "form-control", "rows": 15, "placeholder": "Введите содержимое документа..."}
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        category_field = self.fields["category"]
        if hasattr(category_field, "empty_label"):
            category_field.empty_label = "Выберите категорию"  # type: ignore[misc]
        if hasattr(category_field, "queryset"):
            category_field.queryset = DocumentCategory.objects.all()  # type: ignore[misc]

    def clean_title(self) -> str:
        """Валидация заголовка на уникальность"""
        title = self.cleaned_data.get("title", "").strip()

        if Document.objects.filter(title=title, is_active=True).exists():
            raise ValidationError("Документ с таким заголовком уже существует")

        return title


class FileReplaceForm(forms.Form):  # type: ignore
    """Форма для замены файла в существующем документе"""

    file = forms.FileField(
        label="Новый файл",
        help_text="Текст из нового файла заменит содержимое документа",
        widget=forms.FileInput(
            attrs={"class": "form-control", "accept": ".txt,.docx,.pdf,.xlsx,.pptx,.csv,.md,.html,.htm,.xml"}
        ),
    )

    keep_title = forms.BooleanField(
        label="Сохранить текущий заголовок",
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def clean_file(self) -> Any:
        """Валидация загружаемого файла"""
        file = self.cleaned_data.get("file")

        if not file:
            return file

        # Проверяем размер файла
        if file.size > FileTextExtractor.MAX_FILE_SIZE:
            raise ValidationError(
                f"Файл слишком большой. Максимальный размер: {FileTextExtractor.MAX_FILE_SIZE // (1024 * 1024)}MB"
            )

        # Проверяем тип файла
        file_extension = Path(file.name).suffix.lower()
        if not FileTextExtractor.is_supported_file(file.name):
            supported_extensions = ", ".join(sorted(FileTextExtractor.SUPPORTED_EXTENSIONS))
            raise ValidationError(
                f"Неподдерживаемый тип файла: {file_extension}. " f"Поддерживаемые форматы: {supported_extensions}"
            )

        return file
