# Второй этап: обновляем модель SearchHistory
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('doc_storage', '0002_add_wordmatch'),
    ]

    operations = [
        # Сначала очищаем таблицу SearchHistory
        migrations.RunSQL(
            "DELETE FROM doc_storage_searchhistory;",
            reverse_sql="",
        ),

        # Добавляем поле document в SearchHistory
        migrations.AddField(
            model_name='searchhistory',
            name='document',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to='doc_storage.document',
                verbose_name='Документ'
            ),
        ),

        # Добавляем индекс для оптимизации
        migrations.AddIndex(
            model_name='searchhistory',
            index=models.Index(fields=['document'], name='doc_storage_search_doc_idx'),
        ),
    ]