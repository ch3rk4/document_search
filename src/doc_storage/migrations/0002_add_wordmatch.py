# Первый этап: добавляем модель WordMatch
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('doc_storage', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WordMatch',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('query', models.CharField(max_length=255, verbose_name='Поисковый запрос')),
                ('matched_word', models.CharField(max_length=255, verbose_name='Найденное слово')),
                ('position', models.PositiveIntegerField(verbose_name='Позиция в тексте')),
                ('context_before', models.CharField(blank=True, max_length=200, verbose_name='Контекст до')),
                ('context_after', models.CharField(blank=True, max_length=200, verbose_name='Контекст после')),
                ('match_type', models.CharField(
                    choices=[
                        ('exact', 'Точное совпадение'),
                        ('partial', 'Частичное совпадение'),
                        ('fuzzy', 'Нечеткое совпадение'),
                    ],
                    default='exact',
                    max_length=20,
                    verbose_name='Тип совпадения'
                )),
                ('relevance_score', models.FloatField(default=1.0, verbose_name='Релевантность')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Дата поиска')),
                ('document', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    to='doc_storage.document',
                    verbose_name='Документ'
                )),
            ],
            options={
                'verbose_name': 'Найденное слово',
                'verbose_name_plural': 'Найденные слова',
                'ordering': ['-relevance_score', 'position'],
            },
        ),

        # Добавляем индексы для WordMatch
        migrations.AddIndex(
            model_name='wordmatch',
            index=models.Index(fields=['document', 'query'], name='doc_storage_word_match_doc_query_idx'),
        ),
        migrations.AddIndex(
            model_name='wordmatch',
            index=models.Index(fields=['matched_word'], name='doc_storage_word_match_word_idx'),
        ),
        migrations.AddIndex(
            model_name='wordmatch',
            index=models.Index(fields=['position'], name='doc_storage_word_match_pos_idx'),
        ),
    ]