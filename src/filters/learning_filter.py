# src/filters/learning_filter.py
import json
import re
from pathlib import Path
from collections import Counter
from typing import List


class LearningFilter:
    """Фильтр, который учится на ваших решениях"""

    def __init__(self):
        # Путь к файлу с обратной связью
        self.feedback_file = Path(__file__).parent.parent.parent / 'data' / 'feedback.json'
        self.approved_words = Counter()
        self.rejected_words = Counter()
        self.load_feedback()

    def add_feedback(self, vacancy_text: str, approved: bool):
        """Добавляет обратную связь"""
        if not vacancy_text:
            return

        words = self._extract_keywords(vacancy_text.lower())

        if approved:
            self.approved_words.update(words)
            print(f"📝 Добавлено в одобренные: {words}")
        else:
            self.rejected_words.update(words)
            print(f"📝 Добавлено в отклоненные: {words}")

        self.save_feedback()

    def get_boosted_score(self, vacancy_text: str, base_score: int) -> int:
        """Корректирует рейтинг на основе истории"""
        if not vacancy_text:
            return base_score

        words = set(self._extract_keywords(vacancy_text.lower()))

        # Если слова похожи на одобренные - повышаем рейтинг
        approved_boost = sum(self.approved_words.get(w, 0) for w in words)
        # Если похожи на отклоненные - понижаем
        rejected_penalty = sum(self.rejected_words.get(w, 0) for w in words)

        # Нормализуем, чтобы не было слишком большого влияния
        boost = min(approved_boost, 50) - min(rejected_penalty, 50)

        return base_score + boost

    def _extract_keywords(self, text: str) -> List[str]:
        """Извлекает ключевые слова из текста"""
        # Находим слова длиной от 3 до 20 символов
        words = re.findall(r'\b[а-яa-z]{3,20}\b', text.lower())

        # Стоп-слова, которые не нужно учитывать
        stopwords = {
            'работа', 'компания', 'должность', 'вакансия', 'это', 'также',
            'будет', 'есть', 'нужен', 'требуется', 'ищем', 'своего',
            'команду', 'офис', 'человек', 'сотрудник', 'специалист'
        }

        # Фильтруем стоп-слова и короткие слова
        return [w for w in words if w not in stopwords]

    def load_feedback(self):
        """Загружает обратную связь из файла"""
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.approved_words = Counter(data.get('approved', {}))
                    self.rejected_words = Counter(data.get('rejected', {}))
                    print(
                        f"📚 Загружено обратной связи: одобрено {len(self.approved_words)} слов, отклонено {len(self.rejected_words)} слов")
            except Exception as e:
                print(f"⚠️ Ошибка загрузки feedback: {e}")

    def save_feedback(self):
        """Сохраняет обратную связь в файл"""
        try:
            self.feedback_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.feedback_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'approved': dict(self.approved_words),
                    'rejected': dict(self.rejected_words)
                }, f, indent=2, ensure_ascii=False)
            print(
                f"💾 Сохранена обратная связь: {len(self.approved_words)} одобренных, {len(self.rejected_words)} отклоненных")
        except Exception as e:
            print(f"⚠️ Ошибка сохранения feedback: {e}")

    def get_stats(self) -> dict:
        """Возвращает статистику обучения"""
        return {
            'approved_words_count': len(self.approved_words),
            'rejected_words_count': len(self.rejected_words),
            'total_feedback': sum(self.approved_words.values()) + sum(self.rejected_words.values())
        }