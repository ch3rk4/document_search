import re
import time
from typing import List, Dict, Set, Tuple, Optional
from django.db.models import QuerySet, Q, Count
from django.db.models.functions import Length
from doc_storage.models import Document, SearchHistory
from collections import defaultdict
import difflib


class SearchAlgorithms:
    """Класс с алгоритмами поиска по документам"""

    @staticmethod
    def normalize_text(text: str) -> str:
        """Нормализация текста для поиска"""
        # Приведение к нижнему регистру и удаление лишних пробелов
        text = text.lower().strip()
        # Удаление специальных символов, кроме русских и английских букв, цифр и пробелов
        text = re.sub(r'[^\w\s]', ' ', text)
        # Замена множественных пробелов на одинарные
        text = re.sub(r'\s+', ' ', text)
        return text

    @staticmethod
    def create_word_index(documents: QuerySet[Document]) -> Dict[str, Set[int]]:
        """Создание инвертированного индекса слов"""
        word_index = defaultdict(set)

        for doc in documents:
            normalized_content = SearchAlgorithms.normalize_text(doc.content)
            normalized_title = SearchAlgorithms.normalize_text(doc.title)

            # Индексация слов из заголовка (с повышенным весом)
            for word in normalized_title.split():
                if len(word) > 2:  # Игнорируем слова короче 3 символов
                    word_index[word].add(doc.id)

            # Индексация слов из содержимого
            for word in normalized_content.split():
                if len(word) > 2:
                    word_index[word].add(doc.id)

        return dict(word_index)

    @staticmethod
    def substring_search(query: str, documents: QuerySet[Document]) -> List[Dict]:
        """Поиск по подстрокам с использованием алгоритма Boyer-Moore"""
        start_time = time.time()
        normalized_query = SearchAlgorithms.normalize_text(query)
        results = []

        for doc in documents:
            normalized_content = SearchAlgorithms.normalize_text(doc.content)
            normalized_title = SearchAlgorithms.normalize_text(doc.title)

            # Подсчет совпадений в заголовке и тексте
            title_matches = SearchAlgorithms._count_substring_matches(normalized_query, normalized_title)
            content_matches = SearchAlgorithms._count_substring_matches(normalized_query, normalized_content)

            if title_matches > 0 or content_matches > 0:
                # Расчет релевантности (заголовок имеет больший вес)
                relevance_score = title_matches * 2 + content_matches

                results.append({
                    'document': doc,
                    'relevance_score': relevance_score,
                    'title_matches': title_matches,
                    'content_matches': content_matches,
                    'preview': SearchAlgorithms._create_preview(normalized_content, normalized_query)
                })

        # Сортировка по релевантности
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        search_time = time.time() - start_time
        return results, search_time

    @staticmethod
    def _count_substring_matches(query: str, text: str) -> int:
        """Подсчет количества вхождений подстроки в тексте"""
        count = 0
        start = 0
        while True:
            pos = text.find(query, start)
            if pos == -1:
                break
            count += 1
            start = pos + 1
        return count

    @staticmethod
    def _create_preview(content: str, query: str, preview_length: int = 150) -> str:
        """Создание превью с выделенным найденным текстом"""
        pos = content.find(query)
        if pos == -1:
            return content[:preview_length] + "..." if len(content) > preview_length else content

        # Определяем границы превью
        start = max(0, pos - preview_length // 2)
        end = min(len(content), pos + len(query) + preview_length // 2)

        preview = content[start:end]
        if start > 0:
            preview = "..." + preview
        if end < len(content):
            preview = preview + "..."

        return preview

    @staticmethod
    def fuzzy_search(query: str, documents: QuerySet[Document], threshold: float = 0.6) -> List[Dict]:
        """Нечеткий поиск с использованием алгоритма Левенштейна"""
        start_time = time.time()
        normalized_query = SearchAlgorithms.normalize_text(query)
        query_words = normalized_query.split()
        results = []

        for doc in documents:
            normalized_content = SearchAlgorithms.normalize_text(doc.content)
            normalized_title = SearchAlgorithms.normalize_text(doc.title)

            # Проверка совпадений в заголовке
            title_score = SearchAlgorithms._calculate_fuzzy_score(query_words, normalized_title.split(), threshold)

            # Проверка совпадений в содержимом
            content_score = SearchAlgorithms._calculate_fuzzy_score(query_words, normalized_content.split(), threshold)

            total_score = title_score * 2 + content_score  # Заголовок важнее

            if total_score > 0:
                results.append({
                    'document': doc,
                    'relevance_score': total_score,
                    'title_score': title_score,
                    'content_score': content_score,
                    'preview': SearchAlgorithms._create_preview(normalized_content, normalized_query)
                })

        # Сортировка по релевантности
        results.sort(key=lambda x: x['relevance_score'], reverse=True)

        search_time = time.time() - start_time
        return results, search_time

    @staticmethod
    def _calculate_fuzzy_score(query_words: List[str], text_words: List[str], threshold: float) -> float:
        """Расчет нечеткого соответствия между словами запроса и текста"""
        total_score = 0.0

        for query_word in query_words:
            best_match_score = 0.0

            for text_word in text_words:
                # Используем SequenceMatcher для расчета похожести
                similarity = difflib.SequenceMatcher(None, query_word, text_word).ratio()

                if similarity >= threshold:
                    best_match_score = max(best_match_score, similarity)

            total_score += best_match_score

        return total_score / len(query_words) if query_words else 0.0

    @staticmethod
    def combined_search(query: str, documents: QuerySet[Document]) -> List[Dict]:
        """Комбинированный поиск (точный + нечеткий + подстроки)"""
        start_time = time.time()

        # Выполняем разные типы поиска
        exact_results, _ = SearchAlgorithms.exact_word_search(query, documents)
        substring_results, _ = SearchAlgorithms.substring_search(query, documents)
        fuzzy_results, _ = SearchAlgorithms.fuzzy_search(query, documents)

        # Объединяем результаты и убираем дублирование
        combined_results = {}

        # Добавляем результаты точного поиска с максимальным весом
        for result in exact_results:
            doc_id = result['document'].id
            combined_results[doc_id] = result
            combined_results[doc_id]['search_type'] = 'exact'
            combined_results[doc_id]['final_score'] = result['relevance_score'] * 3

        # Добавляем результаты поиска по подстрокам
        for result in substring_results:
            doc_id = result['document'].id
            if doc_id in combined_results:
                combined_results[doc_id]['final_score'] += result['relevance_score'] * 2
            else:
                combined_results[doc_id] = result
                combined_results[doc_id]['search_type'] = 'substring'
                combined_results[doc_id]['final_score'] = result['relevance_score'] * 2

        # Добавляем результаты нечеткого поиска
        for result in fuzzy_results:
            doc_id = result['document'].id
            if doc_id in combined_results:
                combined_results[doc_id]['final_score'] += result['relevance_score']
            else:
                combined_results[doc_id] = result
                combined_results[doc_id]['search_type'] = 'fuzzy'
                combined_results[doc_id]['final_score'] = result['relevance_score']

        # Сортируем по финальному рейтингу
        final_results = list(combined_results.values())
        final_results.sort(key=lambda x: x['final_score'], reverse=True)

        search_time = time.time() - start_time
        return final_results, search_time

    @staticmethod
    def exact_word_search(query: str, documents: QuerySet[Document]) -> List[Dict]:
        """Точный поиск по словам"""
        start_time = time.time()
        normalized_query = SearchAlgorithms.normalize_text(query)
        query_words = set(normalized_query.split())
        results = []

        for doc in documents:
            normalized_content = SearchAlgorithms.normalize_text(doc.content)
            normalized_title = SearchAlgorithms.normalize_text(doc.title)

            title_words = set(normalized_title.split())
            content_words = set(normalized_content.split())

            # Подсчет точных совпадений
            title_matches = len(query_words.intersection(title_words))
            content_matches = len(query_words.intersection(content_words))

            if title_matches > 0 or content_matches > 0:
                relevance_score = title_matches * 2 + content_matches

                results.append({
                    'document': doc,
                    'relevance_score': relevance_score,
                    'title_matches': title_matches,
                    'content_matches': content_matches,
                    'preview': SearchAlgorithms._create_preview(normalized_content, normalized_query)
                })

        results.sort(key=lambda x: x['relevance_score'], reverse=True)
        search_time = time.time() - start_time
        return results, search_time


class SearchService:
    """Сервис для работы с поиском документов"""

    def __init__(self):
        self.algorithms = SearchAlgorithms()

    def search_documents(
            self,
            query: str,
            search_type: str = 'combined',
            user=None,
            ip_address: Optional[str] = None
    ) -> Tuple[List[Dict], float]:
        """Основной метод поиска документов"""

        if not query or len(query.strip()) < 2:
            return [], 0.0

        # Получаем активные документы
        documents = Document.objects.filter(is_active=True).select_related('category', 'author')

        # Выбираем алгоритм поиска
        if search_type == 'exact':
            results, search_time = self.algorithms.exact_word_search(query, documents)
        elif search_type == 'substring':
            results, search_time = self.algorithms.substring_search(query, documents)
        elif search_type == 'fuzzy':
            results, search_time = self.algorithms.fuzzy_search(query, documents)
        else:  # combined
            results, search_time = self.algorithms.combined_search(query, documents)

        # Сохраняем историю поиска
        self._save_search_history(query, len(results), search_time, user, ip_address)

        return results, search_time

    def _save_search_history(
            self,
            query: str,
            results_count: int,
            search_time: float,
            user=None,
            ip_address: Optional[str] = None
    ) -> None:
        """Сохранение истории поиска"""
        SearchHistory.objects.create(
            query=query,
            user=user,
            results_count=results_count,
            search_time=search_time,
            ip_address=ip_address
        )

    def get_popular_queries(self, limit: int = 10) -> QuerySet[SearchHistory]:
        """Получение популярных поисковых запросов"""
        return (SearchHistory.objects
                .values('query')
                .annotate(search_count=Count('query'))
                .order_by('-search_count')[:limit])