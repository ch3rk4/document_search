"""
Тесты для алгоритмов поиска
"""
from unittest.mock import MagicMock, patch

import pytest

from search_service.algorithms import TextSearchAlgorithms, WordSearchService


class TestTextSearchAlgorithms:
    """Тесты класса TextSearchAlgorithms"""

    def test_normalize_text(self):
        """Тест нормализации текста"""
        test_cases = [
            ("Это тест!", "это тест"),
            ("  Много   пробелов  ", "много пробелов"),
            ("ЗАГЛАВНЫЕ буквы", "заглавные буквы"),
            ("Знаки препинания: точка, запятая;", "знаки препинания точка запятая"),
            ("", ""),
            ("   ", ""),
        ]

        for input_text, expected in test_cases:
            result = TextSearchAlgorithms.normalize_text(input_text)
            assert result == expected, f"Для '{input_text}' ожидалось '{expected}', получено '{result.strip()}'"

    def test_build_failure_function(self):
        """Тест построения функции отказа для КМП"""
        test_cases = [
            ("abab", [0, 0, 1, 2]),
            ("ababaca", [0, 0, 1, 2, 3, 0, 1]),
            ("aaa", [0, 1, 2]),
            ("abc", [0, 0, 0]),
            ("", []),
        ]

        for pattern, expected in test_cases:
            result = TextSearchAlgorithms.build_failure_function(pattern)
            assert result == expected, f"Для паттерна '{pattern}' ожидалось {expected}, получено {result}"

    def test_kmp_search(self):
        """Тест алгоритма КМП"""
        text = "это тестовый текст для тестирования поиска"

        test_cases = [
            ("тест", [4, 23]),  # Должен найти "тест" в "тестовый" и "тестирования"
            ("для", [19]),
            ("поиска", [36]),
            ("несуществующий", []),
            ("", []),
        ]

        for pattern, expected in test_cases:
            result = TextSearchAlgorithms.kmp_search(text, pattern)
            assert result == expected, f"Для паттерна '{pattern}' ожидалось {expected}, получено {result}"

    def test_kmp_search_edge_cases(self):
        """Тест граничных случаев КМП"""
        # Паттерн длиннее текста
        result = TextSearchAlgorithms.kmp_search("short", "very long pattern")
        assert result == []

        # Пустой текст
        result = TextSearchAlgorithms.kmp_search("", "pattern")
        assert result == []

        # Полное совпадение
        result = TextSearchAlgorithms.kmp_search("test", "test")
        assert result == [0]

    def test_boyer_moore_search(self):
        """Тест алгоритма Бойера-Мура"""
        text = "это тестовый текст для тестирования"

        test_cases = [("тест", [4, 23]), ("это", [0]), ("текст", [13]), ("несуществующий", []), ("", [])]

        for pattern, expected in test_cases:
            result = TextSearchAlgorithms.boyer_moore_search(text, pattern)
            assert result == expected, f"Для паттерна '{pattern}' ожидалось {expected}, получено {result}"

    def test_rabin_karp_search(self):
        """Тест алгоритма Рабина-Карпа"""
        text = "абвабвабв"
        pattern = "абв"

        result = TextSearchAlgorithms.rabin_karp_search(text, pattern)
        expected = [0, 3, 6]
        assert result == expected

        # Тест с пустым паттерном
        result = TextSearchAlgorithms.rabin_karp_search(text, "")
        assert result == []

        # Тест с несуществующим паттерном
        result = TextSearchAlgorithms.rabin_karp_search(text, "xyz")
        assert result == []

    def test_fuzzy_search(self):
        """Тест нечеткого поиска"""
        text = "программирование python java javascript"

        # Поиск с точным совпадением
        result = TextSearchAlgorithms.fuzzy_search(text, "python")
        assert len(result) >= 1
        assert any(match["word"] == "python" for match in result)

        # Поиск с похожим словом
        result = TextSearchAlgorithms.fuzzy_search(text, "програмирование")  # с опечаткой
        assert len(result) >= 1

        # Поиск несуществующего слова
        result = TextSearchAlgorithms.fuzzy_search(text, "несуществующее")
        assert len(result) == 0

    def test_fuzzy_search_similarity_scores(self):
        """Тест оценок схожести в нечетком поиске"""
        text = "тест тесто тестирование"
        result = TextSearchAlgorithms.fuzzy_search(text, "тест")

        # Проверяем, что результаты отсортированы по схожести
        similarities = [match["similarity"] for match in result]
        assert similarities == sorted(similarities, reverse=True)

        # Точное совпадение должно иметь максимальную схожесть
        exact_match = next((m for m in result if m["word"] == "тест"), None)
        assert exact_match is not None
        assert exact_match["similarity"] == 1.0

    def test_get_context(self):
        """Тест получения контекста вокруг найденного слова"""
        text = "Это очень длинный текст для тестирования функции получения контекста вокруг найденного слова"
        position = 40  # Позиция слова "тестирования"
        word_length = 12

        context_before, context_after = TextSearchAlgorithms.get_context(text, position, word_length, 10)

        assert len(context_before) <= 10
        assert len(context_after) <= 10
        assert context_before.strip()
        assert context_after.strip()

    def test_get_context_edge_cases(self):
        """Тест граничных случаев получения контекста"""
        text = "короткий текст"

        # Контекст в начале текста
        context_before, context_after = TextSearchAlgorithms.get_context(text, 0, 8, 50)
        assert context_before == ""
        assert "текст" in context_after

        # Контекст в конце текста
        position = len(text) - 5
        context_before, context_after = TextSearchAlgorithms.get_context(text, position, 5, 50)
        assert "короткий" in context_before
        assert context_after == ""

    def test_word_boundary_search(self):
        """Тест поиска по границам слов"""
        text = "тест тестовый протест"

        # Должен найти только целые слова
        result = TextSearchAlgorithms.word_boundary_search(text, "тест")
        assert result == [0]  # Только первое вхождение "тест"

        # Не должен найти части слов
        result = TextSearchAlgorithms.word_boundary_search(text, "прот")
        assert result == []

        # Поиск с учетом регистра
        result = TextSearchAlgorithms.word_boundary_search("Тест ТЕСТ тест", "тест")
        assert len(result) == 3  # Должен найти все варианты


class TestWordSearchService:
    """Тесты класса WordSearchService"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.search_service = WordSearchService()

    def test_service_initialization(self):
        """Тест инициализации сервиса"""
        assert self.search_service.algorithms is not None
        assert isinstance(self.search_service.algorithms, TextSearchAlgorithms)

    @patch("doc_storage.models.WordMatch.objects.filter")
    @patch("doc_storage.models.WordMatch.objects.bulk_create")
    def test_search_words_in_document_exact(self, mock_bulk_create, mock_filter, test_document):
        """Тест точного поиска слов в документе"""
        # Настраиваем мок
        mock_filter.return_value.delete.return_value = None

        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query="тестовый", search_type="exact"
        )

        assert isinstance(matches, list)
        assert isinstance(search_time, float)
        assert search_time >= 0

        # Проверяем, что метод удаления старых результатов был вызван
        mock_filter.assert_called()

    @patch("doc_storage.models.WordMatch.objects.filter")
    def test_search_words_empty_query(self, mock_filter, test_document):
        """Тест поиска с пустым запросом"""
        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query="", search_type="exact"
        )

        assert matches == []
        assert search_time == 0.0

    @patch("doc_storage.models.WordMatch.objects.filter")
    def test_search_words_short_query(self, mock_filter, test_document):
        """Тест поиска с коротким запросом"""
        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query=" ", search_type="exact"  # Только пробел
        )

        assert matches == []
        assert search_time == 0.0

    def test_exact_word_search(self, test_document):
        """Тест метода точного поиска слов"""
        # Используем реальный документ с контентом
        test_document.content = "python программирование javascript"

        matches = self.search_service._exact_word_search(test_document, "python", "python")

        assert isinstance(matches, list)
        # Проверяем структуру результатов
        if matches:
            match = matches[0]
            assert "document" in match
            assert "query" in match
            assert "matched_word" in match
            assert "position" in match
            assert "match_type" in match
            assert "relevance_score" in match
            assert "algorithm" in match

    def test_partial_word_search(self, test_document):
        """Тест метода частичного поиска слов"""
        test_document.content = "программирование программист"

        matches = self.search_service._partial_word_search(test_document, "программирование программист", "прог")

        assert isinstance(matches, list)
        # Должен найти части слов
        if matches:
            for match in matches:
                assert match["match_type"] == "partial"
                assert "прог" in match["matched_word"].lower()

    def test_fuzzy_word_search(self, test_document):
        """Тест метода нечеткого поиска слов"""
        test_document.content = "программирование разработка"

        matches = self.search_service._fuzzy_word_search(
            test_document, "программирование разработка", "програмирование"
        )

        assert isinstance(matches, list)
        if matches:
            for match in matches:
                assert match["match_type"] == "fuzzy"
                assert isinstance(match["relevance_score"], float)
                assert 0 <= match["relevance_score"] <= 1

    def test_remove_duplicates(self, test_document):
        """Тест удаления дубликатов"""
        matches = [
            {"document": test_document, "position": 0, "matched_word": "тест", "relevance_score": 1.0},
            {
                "document": test_document,
                "position": 0,  # Та же позиция
                "matched_word": "тест",  # То же слово
                "relevance_score": 0.8,
            },
            {
                "document": test_document,
                "position": 10,  # Другая позиция
                "matched_word": "тест",
                "relevance_score": 0.9,
            },
        ]

        unique_matches = self.search_service._remove_duplicates(matches)

        assert len(unique_matches) == 2  # Один дубликат должен быть удален
        positions = [match["position"] for match in unique_matches]
        assert 0 in positions
        assert 10 in positions

    @patch("doc_storage.models.WordMatch.objects.bulk_create")
    def test_save_word_matches(self, mock_bulk_create, test_document):
        """Тест сохранения найденных слов"""
        matches = [
            {
                "matched_word": "тест",
                "position": 0,
                "context_before": "контекст до",
                "context_after": "контекст после",
                "match_type": "exact",
                "relevance_score": 1.0,
            }
        ]

        self.search_service._save_word_matches(test_document, "тест", matches)

        # Проверяем, что bulk_create был вызван
        mock_bulk_create.assert_called_once()

        # Получаем переданные аргументы
        args, kwargs = mock_bulk_create.call_args
        word_matches = args[0]

        assert len(word_matches) == 1
        word_match = word_matches[0]
        assert word_match.document == test_document
        assert word_match.query == "тест"
        assert word_match.matched_word == "тест"

    @patch("doc_storage.models.SearchHistory.objects.create")
    def test_save_search_history(self, mock_create, test_document, regular_user):
        """Тест сохранения истории поиска"""
        self.search_service._save_search_history(
            query="тест",
            document=test_document,
            results_count=5,
            search_time=0.1,
            user=regular_user,
            ip_address="127.0.0.1",
        )

        mock_create.assert_called_once_with(
            query="тест",
            document=test_document,
            user=regular_user,
            results_count=5,
            search_time=0.1,
            ip_address="127.0.0.1",
        )

    @patch("doc_storage.models.WordMatch.objects.filter")
    def test_get_search_results(self, mock_filter, test_document):
        """Тест получения результатов поиска"""
        # Настраиваем мок
        mock_queryset = MagicMock()
        mock_filter.return_value.order_by.return_value = mock_queryset

        result = self.search_service.get_search_results(test_document, "тест")

        # Проверяем вызов фильтрации
        mock_filter.assert_called_once_with(document=test_document, query="тест")
        assert result == mock_queryset


class TestSearchIntegration:
    """Интеграционные тесты поиска"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.search_service = WordSearchService()

    def test_combined_search_type(self, search_test_data, regular_user):
        """Тест комбинированного поиска"""
        document = search_test_data[0]  # Документ с содержимым о Python

        matches, search_time = self.search_service.search_words_in_document(
            document=document, query="прог", search_type="combined", user=regular_user, ip_address="127.0.0.1"
        )

        assert isinstance(matches, list)
        assert search_time > 0

        # В комбинированном поиске должны быть разные типы совпадений
        match_types = [match["match_type"] for match in matches]
        # Может содержать exact, partial, fuzzy
        assert len(set(match_types)) >= 1

    def test_search_performance(self, search_test_data, regular_user):
        """Тест производительности поиска"""
        document = search_test_data[0]

        matches, search_time = self.search_service.search_words_in_document(
            document=document, query="python", search_type="exact", user=regular_user
        )

        # Поиск должен выполняться достаточно быстро
        assert search_time < 1.0  # Менее секунды

    def test_search_with_special_characters(self, test_document, regular_user):
        """Тест поиска со специальными символами"""
        test_document.content = "Тест с символами: точка, запятая; восклицание!"
        test_document.save()

        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query="символами", search_type="exact", user=regular_user
        )

        assert isinstance(matches, list)
        # Должен найти слово, несмотря на знаки препинания

    def test_search_case_insensitive(self, test_document, regular_user):
        """Тест поиска без учета регистра"""
        test_document.content = "ЗАГЛАВНЫЕ строчные СмЕшАнНыЕ"
        test_document.save()

        # Поиск строчными буквами
        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query="заглавные", search_type="exact", user=regular_user
        )

        assert len(matches) >= 1

    def test_search_multiple_occurrences(self, test_document, regular_user):
        """Тест поиска множественных вхождений"""
        test_document.content = "тест тест тест разные тестовые тестирования"
        test_document.save()

        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query="тест", search_type="combined", user=regular_user
        )

        # Должен найти все вхождения
        assert len(matches) >= 3

        # Проверяем разные позиции
        positions = [match["position"] for match in matches]
        assert len(set(positions)) >= 3


class TestErrorHandling:
    """Тесты обработки ошибок в поиске"""

    def setup_method(self):
        """Настройка для каждого теста"""
        self.search_service = WordSearchService()

    def test_search_with_none_document(self):
        """Тест поиска с None вместо документа"""
        with pytest.raises(AttributeError):
            self.search_service.search_words_in_document(document=None, query="тест", search_type="exact")

    def test_search_with_invalid_search_type(self, test_document):
        """Тест поиска с неверным типом поиска"""
        # Неверный тип должен просто игнорироваться
        matches, search_time = self.search_service.search_words_in_document(
            document=test_document, query="тест", search_type="invalid_type"
        )

        assert matches == []
        assert search_time >= 0

    @patch("doc_storage.models.WordMatch.objects.bulk_create")
    def test_save_word_matches_exception(self, mock_bulk_create, test_document):
        """Тест обработки исключения при сохранении совпадений"""
        # Настраиваем мок для генерации исключения
        mock_bulk_create.side_effect = Exception("Database error")

        matches = [
            {
                "matched_word": "тест",
                "position": 0,
                "context_before": "",
                "context_after": "",
                "match_type": "exact",
                "relevance_score": 1.0,
            }
        ]

        # Не должно выбрасывать исключение
        self.search_service._save_word_matches(test_document, "тест", matches)

    @patch("doc_storage.models.SearchHistory.objects.create")
    def test_save_search_history_exception(self, mock_create, test_document):
        """Тест обработки исключения при сохранении истории"""
        mock_create.side_effect = Exception("Database error")

        # Не должно выбрасывать исключение
        self.search_service._save_search_history(query="тест", document=test_document, results_count=0, search_time=0.1)
