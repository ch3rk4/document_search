from django.db import migrations


def create_anonymous_user(apps, schema_editor):
    """Создание анонимного пользователя для неавторизованных пользователей"""
    User = apps.get_model('auth', 'User')

    if not User.objects.filter(username='anonymous').exists():
        anonymous_user = User(
            username='anonymous',
            email='anonymous@example.com',
            first_name='Анонимный',
            last_name='Пользователь',
            is_active=True,
            is_staff=False,
            is_superuser=False,
            password='!',  # unusable password
        )
        anonymous_user.save()




def remove_anonymous_user(apps, schema_editor):
    """Удаление анонимного пользователя при откате миграции"""
    User = apps.get_model('auth', 'User')
    try:
        anonymous_user = User.objects.get(username='anonymous')
        anonymous_user.delete()
    except User.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ('doc_storage', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(
            create_anonymous_user,
            remove_anonymous_user,
        ),
    ]