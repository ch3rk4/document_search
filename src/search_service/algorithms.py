# mypy: ignore-errors

import difflib
import re
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from django.contrib.auth.models import User

    from doc_storage.models import Document


class TextSearchAlgorithms:
    """Класс с алгоритмами поиска слов внутри текста"""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Нормализация текста для поиска"""
        # Приведение к нижнему регистру и удаление лишних пробелов
        text = text.lower()
        # Удаление специальных символов, кроме русских и английских букв, цифр и пробелов
        text = re.sub(r"[^\w\s]", " ", text)
        # Замена множественных пробелов на одинарные
        text = re.sub(r"\s+", " ", text)
        text = text.strip()
        return text

    @staticmethod
    def build_failure_function(pattern: str) -> List[int]:
        """Построение функции отказа для алгоритма КМП"""
        m = len(pattern)
        failure = [0] * m
        j = 0

        for i in range(1, m):
            while j > 0 and pattern[i] != pattern[j]:
                j = failure[j - 1]
            if pattern[i] == pattern[j]:
                j += 1
            failure[i] = j

        return failure

    @staticmethod
    def kmp_search(text: str, pattern: str) -> List[int]:
        """Поиск всех вхождений паттерна в тексте используя алгоритм Кнута-Морриса-Пратта"""
        if not pattern:
            return []

        n, m = len(text), len(pattern)
        if m > n:
            return []

        failure = TextSearchAlgorithms.build_failure_function(pattern)
        matches = []
        j = 0

        for i in range(n):
            while j > 0 and text[i] != pattern[j]:
                j = failure[j - 1]
            if text[i] == pattern[j]:
                j += 1
            if j == m:
                matches.append(i - m + 1)
                j = failure[j - 1]

        return matches

    @staticmethod
    def boyer_moore_search(text: str, pattern: str) -> List[int]:
        """Поиск всех вхождений паттерна используя упрощенный алгоритм Бойера-Мура"""
        if not pattern:
            return []

        n, m = len(text), len(pattern)
        if m > n:
            return []

        # Создание таблицы плохого символа
        bad_char: Dict[str, int] = {}
        for i in range(m):
            bad_char[pattern[i]] = i

        matches = []
        shift = 0

        while shift <= n - m:
            j = m - 1

            # Сравнение справа налево
            while j >= 0 and pattern[j] == text[shift + j]:
                j -= 1

            if j < 0:
                matches.append(shift)
                # Сдвиг до следующего возможного совпадения
                shift += m - bad_char.get(text[shift + m], -1) - 1 if shift + m < n else 1
            else:
                # Сдвиг основанный на правиле плохого символа
                shift += max(1, j - bad_char.get(text[shift + j], -1))

        return matches

    @staticmethod
    def rabin_karp_search(text: str, pattern: str, prime: int = 101) -> List[int]:
        """Поиск всех вхождений паттерна используя алгоритм Рабина-Карпа"""
        if not pattern:
            return []

        n, m = len(text), len(pattern)
        if m > n:
            return []

        base = 256
        pattern_hash = 0
        text_hash = 0
        h = 1
        matches = []

        # Вычисление h = pow(base, m-1) % prime
        for i in range(m - 1):
            h = (h * base) % prime

        # Вычисление хеша паттерна и первого окна текста
        for i in range(m):
            pattern_hash = (base * pattern_hash + ord(pattern[i])) % prime
            text_hash = (base * text_hash + ord(text[i])) % prime

        # Проход по тексту
        for i in range(n - m + 1):
            # Проверка хешей
            if pattern_hash == text_hash:
                # Проверка символов
                if text[i : i + m] == pattern:
                    matches.append(i)

            # Вычисление хеша следующего окна
            if i < n - m:
                text_hash = (base * (text_hash - ord(text[i]) * h) + ord(text[i + m])) % prime
                if text_hash < 0:
                    text_hash += prime

        return matches

    @staticmethod
    def fuzzy_search(text: str, pattern: str, max_distance: int = 2) -> List[Dict[str, Any]]:
        """Нечеткий поиск с использованием расстояния Левенштейна"""
        normalized_text = TextSearchAlgorithms.normalize_text(text)
        normalized_pattern = TextSearchAlgorithms.normalize_text(pattern)

        words = normalized_text.split()
        matches = []

        for i, word in enumerate(words):
            # Вычисляем позицию слова в исходном тексте
            position = sum(len(w) + 1 for w in words[:i])

            # Вычисляем расстояние Левенштейна
            distance = difflib.SequenceMatcher(None, normalized_pattern, word).ratio()

            if distance >= (1 - max_distance / max(len(normalized_pattern), 1)):
                matches.append({"word": word, "position": position, "distance": 1 - distance, "similarity": distance})

        return sorted(matches, key=lambda x: x["similarity"], reverse=True)

    @staticmethod
    def get_context(text: str, position: int, word_length: int, context_size: int = 50) -> Tuple[str, str]:
        """Получение контекста вокруг найденного слова"""
        start_context = max(0, position - context_size)
        end_context = min(len(text), position + word_length + context_size)

        context_before = text[start_context:position].strip()
        context_after = text[position + word_length : end_context].strip()

        return context_before, context_after

    @staticmethod
    def word_boundary_search(text: str, pattern: str) -> List[int]:
        """Поиск по границам слов"""
        pattern_regex = r"\b" + re.escape(pattern) + r"\b"
        matches = []

        for match in re.finditer(pattern_regex, text, re.IGNORECASE):
            matches.append(match.start())

        return matches


class WordSearchService:
    """Сервис для поиска слов внутри документов"""

    def __init__(self) -> None:
        self.algorithms = TextSearchAlgorithms()

    def search_words_in_document(
        self,
        document: "Document",
        query: str,
        search_type: str = "combined",
        user: Optional["User"] = None,
        ip_address: Optional[str] = None,
    ) -> Tuple[List[Dict[str, Any]], float]:
        """Основной метод поиска слов в документе"""

        if not query or len(query.strip()) < 1:
            return [], 0.0

        start_time = time.time()

        # Импортируем модели здесь, чтобы избежать циклических импортов
        try:
            from doc_storage.models import SearchHistory, WordMatch
        except ImportError:
            # Fallback если импорт не удался
            WordMatch = None
            SearchHistory = None

        # Очищаем старые результаты для этого документа и запроса
        if WordMatch:
            WordMatch.objects.filter(document=document, query=query).delete()

        # Нормализуем запрос и текст
        normalized_query = self.algorithms.normalize_text(query)
        normalized_content = self.algorithms.normalize_text(document.content)

        all_matches: List[Dict[str, Any]] = []

        if search_type in ["exact", "combined"]:
            exact_matches = self._exact_word_search(document, normalized_content, normalized_query)
            all_matches.extend(exact_matches)

        if search_type in ["partial", "combined"]:
            partial_matches = self._partial_word_search(document, normalized_content, normalized_query)
            all_matches.extend(partial_matches)

        if search_type in ["fuzzy", "combined"]:
            fuzzy_matches = self._fuzzy_word_search(document, normalized_content, normalized_query)
            all_matches.extend(fuzzy_matches)

        # Удаляем дубликаты и сортируем по релевантности
        unique_matches = self._remove_duplicates(all_matches)
        unique_matches.sort(key=lambda x: (-x["relevance_score"], x["position"]))

        # Сохраняем результаты в базу данных
        if WordMatch:
            self._save_word_matches(document, query, unique_matches)

        search_time = time.time() - start_time

        # Сохраняем историю поиска
        if SearchHistory:
            self._save_search_history(query, document, len(unique_matches), search_time, user, ip_address)

        return unique_matches, search_time

    def _exact_word_search(self, document: "Document", text: str, query: str) -> List[Dict[str, Any]]:
        """Точный поиск слов с использованием разных алгоритмов"""
        matches = []

        # KMP алгоритм
        kmp_positions = self.algorithms.kmp_search(text, query)
        for pos in kmp_positions:
            context_before, context_after = self.algorithms.get_context(text, pos, len(query))
            matches.append(
                {
                    "document": document,
                    "query": query,
                    "matched_word": query,
                    "position": pos,
                    "context_before": context_before,
                    "context_after": context_after,
                    "match_type": "exact",
                    "relevance_score": 1.0,
                    "algorithm": "KMP",
                }
            )

        # Поиск по границам слов (более точный для целых слов)
        word_positions = self.algorithms.word_boundary_search(text, query)
        for pos in word_positions:
            context_before, context_after = self.algorithms.get_context(text, pos, len(query))
            matches.append(
                {
                    "document": document,
                    "query": query,
                    "matched_word": query,
                    "position": pos,
                    "context_before": context_before,
                    "context_after": context_after,
                    "match_type": "exact",
                    "relevance_score": 1.2,  # Более высокий рейтинг для границ слов
                    "algorithm": "Word Boundary",
                }
            )

        return matches

    def _partial_word_search(self, document: "Document", text: str, query: str) -> List[Dict[str, Any]]:
        """Поиск частей слов"""
        matches = []

        # Boyer-Moore для поиска подстрок
        bm_positions = self.algorithms.boyer_moore_search(text, query)
        for pos in bm_positions:
            # Находим полное слово, содержащее найденную подстроку
            word_start = pos
            while word_start > 0 and text[word_start - 1].isalnum():
                word_start -= 1

            word_end = pos + len(query)
            while word_end < len(text) and text[word_end].isalnum():
                word_end += 1

            matched_word = text[word_start:word_end]
            context_before, context_after = self.algorithms.get_context(text, word_start, len(matched_word))

            matches.append(
                {
                    "document": document,
                    "query": query,
                    "matched_word": matched_word,
                    "position": word_start,
                    "context_before": context_before,
                    "context_after": context_after,
                    "match_type": "partial",
                    "relevance_score": 0.8,
                    "algorithm": "Boyer-Moore",
                }
            )

        # Rabin-Karp для дополнительной проверки
        rk_positions = self.algorithms.rabin_karp_search(text, query)
        for pos in rk_positions:
            word_start = pos
            while word_start > 0 and text[word_start - 1].isalnum():
                word_start -= 1

            word_end = pos + len(query)
            while word_end < len(text) and text[word_end].isalnum():
                word_end += 1

            matched_word = text[word_start:word_end]
            context_before, context_after = self.algorithms.get_context(text, word_start, len(matched_word))

            matches.append(
                {
                    "document": document,
                    "query": query,
                    "matched_word": matched_word,
                    "position": word_start,
                    "context_before": context_before,
                    "context_after": context_after,
                    "match_type": "partial",
                    "relevance_score": 0.7,
                    "algorithm": "Rabin-Karp",
                }
            )

        return matches

    def _fuzzy_word_search(self, document: "Document", text: str, query: str) -> List[Dict[str, Any]]:
        """Нечеткий поиск слов"""
        matches = []
        fuzzy_results = self.algorithms.fuzzy_search(text, query, max_distance=2)

        for result in fuzzy_results[:10]:  # Ограничиваем количество нечетких совпадений
            context_before, context_after = self.algorithms.get_context(text, result["position"], len(result["word"]))

            matches.append(
                {
                    "document": document,
                    "query": query,
                    "matched_word": result["word"],
                    "position": result["position"],
                    "context_before": context_before,
                    "context_after": context_after,
                    "match_type": "fuzzy",
                    "relevance_score": result["similarity"],
                    "algorithm": "Fuzzy",
                }
            )

        return matches

    def _remove_duplicates(self, matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Удаление дубликатов совпадений"""
        seen = set()
        unique_matches = []

        for match in matches:
            # Создаем ключ для уникальности на основе позиции и слова
            key = (match["position"], match["matched_word"])

            if key not in seen:
                seen.add(key)
                unique_matches.append(match)

        return unique_matches

    def _save_word_matches(self, document: "Document", query: str, matches: List[Dict[str, Any]]) -> None:
        """Сохранение найденных слов в базу данных"""
        try:
            from doc_storage.models import WordMatch

            word_matches = []

            for match in matches:
                word_match = WordMatch(
                    document=document,
                    query=query,
                    matched_word=match["matched_word"],
                    position=match["position"],
                    context_before=match["context_before"][:200],
                    context_after=match["context_after"][:200],
                    match_type=match["match_type"],
                    relevance_score=match["relevance_score"],
                )
                word_matches.append(word_match)

            WordMatch.objects.bulk_create(word_matches)
        except Exception as e:
            print(f"Ошибка сохранения совпадений: {e}")

    def _save_search_history(
        self,
        query: str,
        document: "Document",
        results_count: int,
        search_time: float,
        user: Optional["User"] = None,
        ip_address: Optional[str] = None,
    ) -> None:
        """Сохранение истории поиска"""
        try:
            from doc_storage.models import SearchHistory

            SearchHistory.objects.create(
                query=query,
                document=document,
                user=user,
                results_count=results_count,
                search_time=search_time,
                ip_address=ip_address,
            )
        except Exception as e:
            print(f"Ошибка сохранения истории поиска: {e}")

    def get_search_results(self, document: "Document", query: str) -> Any:
        """Получение результатов поиска из базы данных"""
        try:
            from doc_storage.models import WordMatch

            return WordMatch.objects.filter(document=document, query=query).order_by("-relevance_score", "position")
        except Exception as e:
            print(f"Ошибка получения результатов поиска: {e}")
            return []
