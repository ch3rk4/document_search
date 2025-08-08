from django.db import migrations


def create_admin_user(apps, schema_editor):
    """Создание администратора по умолчанию"""
    User = apps.get_model('auth', 'User')

    # Создаем админа, если его еще нет
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123',
            first_name='Администратор',
            last_name='Системы'
        )


def remove_admin_user(apps, schema_editor):
    """Удаление админа при откате миграции"""
    User = apps.get_model('auth', 'User')
    try:
        admin_user = User.objects.get(username='admin')
        admin_user.delete()
    except User.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('doc_storage', '0002_create_anonymous_user'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            create_admin_user,
            remove_admin_user,
        ),
    ]