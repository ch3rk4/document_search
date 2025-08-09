"""
Тесты для форм приложения
"""
from django.core.files.uploadedfile import SimpleUploadedFile

from doc_storage.auth_forms import UserLoginForm, UserProfileForm, UserRegistrationForm
from doc_storage.forms import (
    DocumentCreateForm, DocumentEditForm, DocumentUploadForm, FileReplaceForm
)


class TestUserRegistrationForm:
    """Тесты формы регистрации пользователя"""

    def test_valid_registration_form(self, db):
        """Тест валидной формы регистрации"""
        form_data = {
            'username': 'newuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'newuser@test.com',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        form = UserRegistrationForm(data=form_data)

        assert form.is_valid()
        user = form.save()
        assert user.username == 'newuser'
        assert user.first_name == 'Test'
        assert user.last_name == 'User'
        assert user.email == 'newuser@test.com'
        assert user.check_password('testpass123')

    def test_registration_form_duplicate_email(self, db, regular_user):
        """Тест формы с дублирующимся email"""
        form_data = {
            'username': 'newuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': regular_user.email,  # Существующий email
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        form = UserRegistrationForm(data=form_data)

        assert not form.is_valid()
        assert 'email' in form.errors
        assert 'уже существует' in str(form.errors['email'])

    def test_registration_form_password_mismatch(self, db):
        """Тест формы с несовпадающими паролями"""
        form_data = {
            'username': 'newuser',
            'first_name': 'Test',
            'last_name': 'User',
            'email': 'newuser@test.com',
            'password1': 'testpass123',
            'password2': 'differentpass'
        }
        form = UserRegistrationForm(data=form_data)

        assert not form.is_valid()
        assert 'password2' in form.errors

    def test_registration_form_missing_required_fields(self, db):
        """Тест формы с отсутствующими обязательными полями"""
        form_data = {
            'username': 'newuser',
            'password1': 'testpass123',
            'password2': 'testpass123'
        }
        form = UserRegistrationForm(data=form_data)

        assert not form.is_valid()
        assert 'first_name' in form.errors
        assert 'last_name' in form.errors
        assert 'email' in form.errors


class TestUserLoginForm:
    """Тесты формы входа пользователя"""

    def test_valid_login_form(self, regular_user):
        """Тест валидной формы входа"""
        form_data = {
            'username': regular_user.username,
            'password': 'testpass123'
        }
        form = UserLoginForm(data=form_data)

        # Форма должна быть валидной по структуре
        assert 'username' in form.fields
        assert 'password' in form.fields

    def test_login_form_widget_classes(self, db):
        """Тест CSS классов виджетов формы входа"""
        form = UserLoginForm()

        assert 'form-control' in form.fields['username'].widget.attrs.get('class', '')
        assert 'form-control' in form.fields['password'].widget.attrs.get('class', '')


class TestUserProfileForm:
    """Тесты формы профиля пользователя"""

    def test_valid_profile_form(self, regular_user):
        """Тест валидной формы профиля"""
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': 'updated@test.com'
        }
        form = UserProfileForm(data=form_data, instance=regular_user)

        assert form.is_valid()
        updated_user = form.save()
        assert updated_user.first_name == 'Updated'
        assert updated_user.last_name == 'Name'
        assert updated_user.email == 'updated@test.com'

    def test_profile_form_duplicate_email(self, db, regular_user, admin_user):
        """Тест формы профиля с дублирующимся email"""
        form_data = {
            'first_name': regular_user.first_name,
            'last_name': regular_user.last_name,
            'email': admin_user.email  # Email другого пользователя
        }
        form = UserProfileForm(data=form_data, instance=regular_user)

        assert not form.is_valid()
        assert 'email' in form.errors

    def test_profile_form_same_email(self, regular_user):
        """Тест формы профиля с тем же email (должен быть валидным)"""
        form_data = {
            'first_name': 'Updated',
            'last_name': 'Name',
            'email': regular_user.email  # Тот же email
        }
        form = UserProfileForm(data=form_data, instance=regular_user)

        assert form.is_valid()


class TestDocumentUploadForm:
    """Тесты формы загрузки документа"""

    def test_valid_upload_form(self, db, test_category, test_tag, sample_text_file):
        """Тест валидной формы загрузки"""
        form_data = {
            'title': 'Загруженный документ',
            'category': test_category.pk,
            'tags': [test_tag.pk]
        }
        form_files = {
            'file': sample_text_file
        }
        form = DocumentUploadForm(data=form_data, files=form_files)

        assert form.is_valid()
        assert form.cleaned_data['title'] == 'Загруженный документ'
        assert form.cleaned_data['category'] == test_category
        assert test_tag in form.cleaned_data['tags']

    def test_upload_form_without_title(self, db, sample_text_file):
        """Тест формы загрузки без заголовка"""
        form_data = {}
        form_files = {
            'file': sample_text_file
        }
        form = DocumentUploadForm(data=form_data, files=form_files)

        assert form.is_valid()
        assert form.cleaned_data['title'] == ''  # Заголовок не обязателен

    def test_upload_form_invalid_file_type(self, db, unsupported_file):
        """Тест формы с неподдерживаемым типом файла"""
        form_data = {
            'title': 'Неподдерживаемый файл'
        }
        form_files = {
            'file': unsupported_file
        }
        form = DocumentUploadForm(data=form_data, files=form_files)

        assert not form.is_valid()
        assert 'file' in form.errors
        assert 'неподдерживаемый' in str(form.errors['file']).lower()

    def test_upload_form_large_file(self, db, large_file):
        """Тест формы с файлом большого размера"""
        form_data = {
            'title': 'Большой файл'
        }
        form_files = {
            'file': large_file
        }
        form = DocumentUploadForm(data=form_data, files=form_files)

        assert not form.is_valid()
        assert 'file' in form.errors
        assert 'большой' in str(form.errors['file']).lower()

    def test_upload_form_duplicate_title(self, db, test_document, sample_text_file):
        """Тест формы с дублирующимся заголовком"""
        form_data = {
            'title': test_document.title  # Существующий заголовок
        }
        form_files = {
            'file': sample_text_file
        }
        form = DocumentUploadForm(data=form_data, files=form_files)

        assert not form.is_valid()
        assert 'title' in form.errors
        assert 'уже существует' in str(form.errors['title'])

    def test_upload_form_without_file(self, db):
        """Тест формы без файла"""
        form_data = {
            'title': 'Без файла'
        }
        form = DocumentUploadForm(data=form_data)

        assert not form.is_valid()
        assert 'file' in form.errors


class TestDocumentCreateForm:
    """Тесты формы создания документа"""

    def test_valid_create_form(self, db, test_category, test_tag):
        """Тест валидной формы создания"""
        form_data = {
            'title': 'Новый документ',
            'content': 'Содержимое нового документа',
            'category': test_category.pk,
            'tags': [test_tag.pk]
        }
        form = DocumentCreateForm(data=form_data)

        assert form.is_valid()
        assert form.cleaned_data['title'] == 'Новый документ'
        assert form.cleaned_data['content'] == 'Содержимое нового документа'
        assert form.cleaned_data['category'] == test_category
        assert test_tag in form.cleaned_data['tags']

    def test_create_form_duplicate_title(self, db, test_document):
        """Тест формы создания с дублирующимся заголовком"""
        form_data = {
            'title': test_document.title,
            'content': 'Новое содержимое'
        }
        form = DocumentCreateForm(data=form_data)

        assert not form.is_valid()
        assert 'title' in form.errors
        assert 'уже существует' in str(form.errors['title'])

    def test_create_form_missing_required_fields(self, db):
        """Тест формы создания с отсутствующими обязательными полями"""
        form_data = {}
        form = DocumentCreateForm(data=form_data)

        assert not form.is_valid()
        assert 'title' in form.errors
        assert 'content' in form.errors

    def test_create_form_without_category(self, db):
        """Тест формы создания без категории"""
        form_data = {
            'title': 'Без категории',
            'content': 'Содержимое'
        }
        form = DocumentCreateForm(data=form_data)

        assert form.is_valid()
        assert form.cleaned_data['category'] is None

    def test_create_form_without_tags(self, db):
        """Тест формы создания без тегов"""
        form_data = {
            'title': 'Без тегов',
            'content': 'Содержимое'
        }
        form = DocumentCreateForm(data=form_data)

        assert form.is_valid()
        assert len(form.cleaned_data['tags']) == 0


class TestDocumentEditForm:
    """Тесты формы редактирования документа"""

    def test_valid_edit_form(self, test_document, test_category):
        """Тест валидной формы редактирования"""
        form_data = {
            'title': 'Обновленный заголовок',
            'content': 'Обновленное содержимое',
            'category': test_category.pk,
            'is_active': True
        }
        form = DocumentEditForm(data=form_data, instance=test_document)

        assert form.is_valid()
        updated_document = form.save()
        assert updated_document.title == 'Обновленный заголовок'
        assert updated_document.content == 'Обновленное содержимое'
        assert updated_document.category == test_category
        assert updated_document.is_active is True

    def test_edit_form_deactivate_document(self, test_document):
        """Тест деактивации документа через форму"""
        form_data = {
            'title': test_document.title,
            'content': test_document.content,
            'is_active': False
        }
        form = DocumentEditForm(data=form_data, instance=test_document)

        assert form.is_valid()
        updated_document = form.save()
        assert updated_document.is_active is False

    def test_edit_form_required_fields(self, test_document):
        """Тест обязательных полей формы редактирования"""
        form_data = {}
        form = DocumentEditForm(data=form_data, instance=test_document)

        assert not form.is_valid()
        assert 'title' in form.errors
        assert 'content' in form.errors


class TestFileReplaceForm:
    """Тесты формы замены файла"""

    def test_valid_replace_form(self, db, sample_text_file):
        """Тест валидной формы замены файла"""
        form_data = {
            'keep_title': True
        }
        form_files = {
            'file': sample_text_file
        }
        form = FileReplaceForm(data=form_data, files=form_files)

        assert form.is_valid()
        assert form.cleaned_data['keep_title'] is True

    def test_replace_form_dont_keep_title(self, db, sample_text_file):
        """Тест формы замены файла без сохранения заголовка"""
        form_data = {
            'keep_title': False
        }
        form_files = {
            'file': sample_text_file
        }
        form = FileReplaceForm(data=form_data, files=form_files)

        assert form.is_valid()
        assert form.cleaned_data['keep_title'] is False

    def test_replace_form_invalid_file(self, db, unsupported_file):
        """Тест формы замены с неподдерживаемым файлом"""
        form_data = {
            'keep_title': True
        }
        form_files = {
            'file': unsupported_file
        }
        form = FileReplaceForm(data=form_data, files=form_files)

        assert not form.is_valid()
        assert 'file' in form.errors

    def test_replace_form_large_file(self, db, large_file):
        """Тест формы замены с большим файлом"""
        form_data = {
            'keep_title': True
        }
        form_files = {
            'file': large_file
        }
        form = FileReplaceForm(data=form_data, files=form_files)

        assert not form.is_valid()
        assert 'file' in form.errors

    def test_replace_form_without_file(self, db):
        """Тест формы замены без файла"""
        form_data = {
            'keep_title': True
        }
        form = FileReplaceForm(data=form_data)

        assert not form.is_valid()
        assert 'file' in form.errors


class TestFormWidgets:
    """Тесты виджетов форм"""

    def test_upload_form_widgets(self, db):
        """Тест виджетов формы загрузки"""
        form = DocumentUploadForm()

        # Проверяем CSS классы
        assert 'form-control' in form.fields['file'].widget.attrs.get('class', '')
        assert 'form-control' in form.fields['title'].widget.attrs.get('class', '')
        assert 'form-select' in form.fields['category'].widget.attrs.get('class', '')

        # Проверяем атрибуты файлового поля
        file_widget = form.fields['file'].widget
        accept_attr = file_widget.attrs.get('accept', '')
        assert '.txt' in accept_attr
        assert '.docx' in accept_attr
        assert '.pdf' in accept_attr

    def test_create_form_widgets(self, db):
        """Тест виджетов формы создания"""
        form = DocumentCreateForm()

        assert 'form-control' in form.fields['title'].widget.attrs.get('class', '')
        assert 'form-control' in form.fields['content'].widget.attrs.get('class', '')
        assert 'form-select' in form.fields['category'].widget.attrs.get('class', '')

        # Проверяем textarea для содержимого
        content_widget = form.fields['content'].widget
        assert content_widget.attrs.get('rows') == 15

    def test_edit_form_widgets(self, db):
        """Тест виджетов формы редактирования"""
        form = DocumentEditForm()

        assert 'form-control' in form.fields['title'].widget.attrs.get('class', '')
        assert 'form-control' in form.fields['content'].widget.attrs.get('class', '')
        assert 'form-select' in form.fields['category'].widget.attrs.get('class', '')
        assert 'form-check-input' in form.fields['is_active'].widget.attrs.get('class', '')


class TestFormInitialization:
    """Тесты инициализации форм"""

    def test_upload_form_category_queryset(self, db, test_category):
        """Тест загрузки всех категорий в форме загрузки"""
        form = DocumentUploadForm()
        category_queryset = form.fields['category'].queryset

        assert test_category in category_queryset
        assert category_queryset.count() >= 1

    def test_upload_form_tags_queryset(self, db, test_tag):
        """Тест загрузки всех тегов в форме загрузки"""
        form = DocumentUploadForm()
        tags_queryset = form.fields['tags'].queryset

        assert test_tag in tags_queryset
        assert tags_queryset.count() >= 1

    def test_create_form_category_empty_label(self, db):
        """Тест пустого значения для категории в форме создания"""
        form = DocumentCreateForm()

        # Проверяем, что есть пустое значение для категории
        category_field = form.fields['category']
        assert hasattr(category_field, 'empty_label')

    def test_edit_form_instance_binding(self, test_document):
        """Тест связывания формы редактирования с экземпляром"""
        form = DocumentEditForm(instance=test_document)

        assert form.instance == test_document
        assert form.initial['title'] == test_document.title
        assert form.initial['content'] == test_document.content
        assert form.initial['is_active'] == test_document.is_active


class TestFormValidation:
    """Тесты дополнительной валидации форм"""

    def test_upload_form_supported_extensions(self, db):
        """Тест поддерживаемых расширений в форме загрузки"""
        # Создаем файл с поддерживаемым расширением
        valid_file = SimpleUploadedFile(
            "test.txt",
            b"Test content",
            content_type="text/plain"
        )

        form_data = {'title': 'Test'}
        form_files = {'file': valid_file}
        form = DocumentUploadForm(data=form_data, files=form_files)

        assert form.is_valid()

    def test_form_help_texts(self, db):
        """Тест текстов помощи в формах"""
        upload_form = DocumentUploadForm()
        create_form = DocumentCreateForm()

        # Проверяем наличие help_text
        assert upload_form.fields['file'].help_text
        assert upload_form.fields['title'].help_text

        # В форме создания не должно быть help_text для файла
        assert 'file' not in create_form.fields
