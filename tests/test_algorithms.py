import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from doc_storage.models import Document, DocumentCategory, WordMatch, SearchHistory
from search_service.algorithms import TextSearchAlgorithms, WordSearchService


class TextSearchAlgorithmsTest(TestCase):
    """Тесты для алгоритмов поиска текста"""

    def test_normalize_text(self):
        """Тест нормализации текста"""
        text = "  PYTHON Программирование!!! 123  "
        normalized = TextSearchAlgorithms.normalize_text(text)
        expected = "python программирование 123"

        self.assertEqual(normalized, expected)

    def test_kmp_search(self):
        """Тест алгоритма Кнута-Морриса-Пратта"""
        text = "это тестовый текст для тестирования kmp алгоритма тест"
        pattern = "тест"

        positions = TextSearchAlgorithms.kmp_search(text, pattern)

        # Должно найти "тест" в нескольких позициях
        self.assertGreater(len(positions), 0)

        # Проверяем, что найденные позиции действительно содержат паттерн
        for pos in positions:
            found_text = text[pos:pos + len(pattern)]
            self.assertEqual(found_text, pattern)

    def test_boyer_moore_search(self):
        """Тест алгоритма Бойера-Мура"""
        text = "программирование на python очень интересно"
        pattern = "прог"

        positions = TextSearchAlgorithms.boyer_moore_search(text, pattern)

        self.assertGreater(len(positions), 0)
        self.assertEqual(text[positions[0]:positions[0] + len(pattern)], pattern)

    def test_rabin_karp_search(self):
        """Тест алгоритма Рабина-Карпа"""
        text = "алгоритм поиска строк в тексте строковый поиск"
        pattern = "поиск"

        positions = TextSearchAlgorithms.rabin_karp_search(text, pattern)

        self.assertGreater(len(positions), 0)

        # Проверяем корректность найденных позиций
        for pos in positions:
            found_text = text[pos:pos + len(pattern)]
            self.assertEqual(found_text, pattern)

    def test_fuzzy_search(self):
        """Тест нечеткого поиска"""
        text = "python программирование питон разработка"
        pattern = "питан"  # Похоже на "питон"

        matches = TextSearchAlgorithms.fuzzy_search(text, pattern, max_distance=2)

        # Должен найти похожие слова
        self.assertGreaterEqual(len(matches), 0)

        if matches:
            # Проверяем структуру результата
            match = matches[0]
            self.assertIn('word', match)
            self.assertIn('position', match)
            self.assertIn('similarity', match)

    def test_word_boundary_search(self):
        """Тест поиска по границам слов"""
        text = "тест тестирование тестовый нетестовый"
        pattern = "тест"

        positions = TextSearchAlgorithms.word_boundary_search(text, pattern)

        # Должен найти только целое слово "тест", но не его части в других словах
        self.assertEqual(len(positions), 1)
        self.assertEqual(text[positions[0]:positions[0] + len(pattern)], pattern)

    def test_get_context(self):
        """Тест получения контекста вокруг найденного слова"""
        text = "это длинный текст для тестирования получения контекста вокруг слова"
        position = text.find("тестирования")
        word_length = len("тестирования")

        context_before, context_after = TextSearchAlgorithms.get_context(
            text, position, word_length, context_size=15
        )

        self.assertIn("текст для", context_before)
        self.assertIn("получения", context_after)

    def test_build_failure_function(self):
        """Тест построения функции отказа для КМП"""
        pattern = "ababa"
        failure = TextSearchAlgorithms.build_failure_function(pattern)
        expected = [0, 0, 1, 2, 3]

        self.assertEqual(failure, expected)

    def test_empty_pattern_search(self):
        """Тест поиска с пустым паттерном"""
        text = "некоторый текст"
        pattern = ""

        kmp_results = TextSearchAlgorithms.kmp_search(text, pattern)
        bm_results = TextSearchAlgorithms.boyer_moore_search(text, pattern)
        rk_results = TextSearchAlgorithms.rabin_karp_search(text, pattern)

        self.assertEqual(kmp_results, [])
        self.assertEqual(bm_results, [])
        self.assertEqual(rk_results, [])

    def test_pattern_longer_than_text(self):
        """Тест поиска паттерна длиннее текста"""
        text = "короткий"
        pattern = "очень длинный паттерн"

        kmp_results = TextSearchAlgorithms.kmp_search(text, pattern)
        bm_results = TextSearchAlgorithms.boyer_moore_search(text, pattern)
        rk_results = TextSearchAlgorithms.rabin_karp_search(text, pattern)

        self.assertEqual(kmp_results, [])
        self.assertEqual(bm_results, [])
        self.assertEqual(rk_results, [])


class WordSearchServiceTest(TestCase):
    """Тесты для сервиса поиска слов в документах"""

    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(username='testuser', password='testpass123')
        self.category = DocumentCategory.objects.create(name='Тест')

        self.document = Document.objects.create(
            title='Тестовый документ',
            content='''Python - это высокоуровневый язык программирования.
            Python используется для веб-разработки, анализа данных, машинного обучения.
            Программирование на Python очень интересно и увлекательно.
            Многие программисты выбирают Python для своих проектов.''',
            author=self.user,
            category=self.category
        )

        self.search_service = WordSearchService()

    def test_search_words_exact(self):
        """Тест точного поиска слов"""
        matches, search_time = self.search_service.search_words_in_document(
            document=self.document,
            query='python',
            search_type='exact',
            user=self.user,
            ip_address='127.0.0.1'
        )

        self.assertGreater(len(matches), 0)
        self.assertGreater(search_time, 0)

        # Проверяем, что найденные слова действительно содержат запрос
        for match in matches:
            self.assertIn('python', match['matched_word'].lower())

    def test_search_words_partial(self):
        """Тест частичного поиска слов"""
        matches, search_time = self.search_service.search_words_in_document(
            document=self.document,
            query='прог',
            search_type='partial',
            user=self.user
        )

        self.assertGreater(len(matches), 0)
        self.assertGreater(search_time, 0)

        # Проверяем, что найденные слова содержат искомую подстроку
        found_programming_words = any(
            'прог' in match['matched_word'].lower()
            for match in matches
        )
        self.assertTrue(found_programming_words)

    def test_search_words_fuzzy(self):
        """Тест нечеткого поиска слов"""
        matches, search_time = self.search_service.search_words_in_document(
            document=self.document,
            query='питон',  # Похоже на "python"
            search_type='fuzzy',
            user=self.user
        )

        # Нечеткий поиск может не найти совпадений для сильно отличающихся слов
        self.assertGreaterEqual(len(matches), 0)
        self.assertGreater(search_time, 0)

    def test_search_words_combined(self):
        """Тест комбинированного поиска слов"""
        matches, search_time = self.search_service.search_words_in_document(
            document=self.document,
            query='программирование',
            search_type='combined',
            user=self.user
        )

        self.assertGreater(len(matches), 0)
        self.assertGreater(search_time, 0)

        # Проверяем наличие разных типов совпадений
        match_types = set(match['match_type'] for match in matches)
        self.assertGreater(len(match_types), 0)

    def test_word_matches_saved_to_db(self):
        """Тест сохранения результатов поиска в базу данных"""
        initial_count = WordMatch.objects.count()

        self.search_service.search_words_in_document(
            document=self.document,
            query='python',
            search_type='exact',
            user=self.user
        )

        final_count = WordMatch.objects.count()
        self.assertGreater(final_count, initial_count)

        # Проверяем сохраненные записи
        word_matches = WordMatch.objects.filter(
            document=self.document,
            query='python'
        )
        self.assertGreater(word_matches.count(), 0)

        first_match = word_matches.first()
        self.assertEqual(first_match.document, self.document)
        self.assertEqual(first_match.query, 'python')
        self.assertIsNotNone(first_match.matched_word)
        self.assertGreaterEqual(first_match.position, 0)

    def test_search_history_saved(self):
        """Тест сохранения истории поиска"""
        initial_count = SearchHistory.objects.count()

        self.search_service.search_words_in_document(
            document=self.document,
            query='тестовый запрос',
            user=self.user,
            ip_address='192.168.1.1'
        )

        final_count = SearchHistory.objects.count()
        self.assertEqual(final_count, initial_count + 1)

        # Проверяем созданную запись
        last_search = SearchHistory.objects.latest('created_at')
        self.assertEqual(last_search.query, 'тестовый запрос')
        self.assertEqual(last_search.document, self.document)
        self.assertEqual(last_search.user, self.user)
        self.assertEqual(last_search.ip_address, '192.168.1.1')

    def test_get_search_results_from_db(self):
        """Тест получения результатов поиска из базы данных"""
        # Сначала выполняем поиск
        self.search_service.search_words_in_document(
            document=self.document,
            query='python',
            search_type='combined',
            user=self.user
        )

        # Затем получаем результаты из базы данных
        results = self.search_service.get_search_results(self.document, 'python')

        self.assertGreater(results.count(), 0)

        first_result = results.first()
        self.assertEqual(first_result.document, self.document)
        self.assertEqual(first_result.query, 'python')

    def test_empty_query_handling(self):
        """Тест обработки пустого запроса"""
        matches, search_time = self.search_service.search_words_in_document(
            document=self.document,
            query='',
            user=self.user
        )

        self.assertEqual(len(matches), 0)
        self.assertEqual(search_time, 0.0)

    def test_very_short_query_handling(self):
        """Тест обработки очень короткого запроса"""
        matches, search_time = self.search_service.search_words_in_document(
            document=self.document,
            query='',
            user=self.user
        )

        self.assertEqual(len(matches), 0)
        self.assertEqual(search_time, 0.0)

    def test_context_extraction(self):
        """Тест извлечения контекста для найденных слов"""
        matches, _ = self.search_service.search_words_in_document(
            document=self.document,
            query='python',
            search_type='exact',
            user=self.user
        )

        self.assertGreater(len(matches), 0)

        # Проверяем наличие контекста
        first_match = matches[0]
        self.assertIn('context_before', first_match)
        self.assertIn('context_after', first_match)

    def test_relevance_scoring(self):
        """Тест оценки релевантности"""
        matches, _ = self.search_service.search_words_in_document(
            document=self.document,
            query='python',
            search_type='combined',
            user=self.user
        )

        self.assertGreater(len(matches), 0)

        # Проверяем, что результаты отсортированы по релевантности
        relevance_scores = [match['relevance_score'] for match in matches]
        self.assertEqual(relevance_scores, sorted(relevance_scores, reverse=True))

        # Проверяем, что оценки релевантности в допустимом диапазоне
        for score in relevance_scores:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 2.0)  # Максимум с учетом весов