"""Детерминированные проверки качества перевода (без вызова LLM)."""
import re
from typing import Dict, List, Tuple

# Ищем плейсхолдеры вида ⟦EM1⟧ или ⟦/EM1⟧
PLACEHOLDER_RE = re.compile(r"⟦\s*(/?[A-ZА-ЯЁ]+\d+)\s*⟧")
# Ищем английские слова (от 3 букв), чтобы отлавливать даже короткие типа "the", "and", "behold"
LATIN_WORD_RE = re.compile(r"\b[a-zA-Z]{3,}\b")

def validate_translation(
    original_text: str,
    translated_text: str,
    mapping: Dict[str, str]
) -> Tuple[bool, List[str]]:
    errors = []

    if not translated_text or not translated_text.strip():
        return False, ["Модель вернула пустой перевод"]

    len_orig = max(len(original_text.strip()), 1)
    len_trans = len(translated_text.strip())
    ratio = len_trans / len_orig
    if ratio < 0.25:
        errors.append(f"Подозрительно короткий перевод (ratio {ratio:.2f})")
    elif ratio > 4.0:
        errors.append(f"Подозрительно длинный перевод (ratio {ratio:.2f})")

    # Проверка плейсхолдеров
    expected = set(mapping.keys())
    found_matches = PLACEHOLDER_RE.findall(translated_text)
    found = {f"⟦{m}⟧" for m in found_matches}

    missing = expected - found
    extra = found - expected

    if missing:
        sample = list(missing)[:3]
        errors.append(f"Потеряны плейсхолдеры: {', '.join(sample)}")
    if extra:
        sample = list(extra)[:3]
        errors.append(f"Добавлены лишние плейсхолдеры: {', '.join(sample)}")

    open_count = sum(1 for p in found if not p.startswith("⟦/"))
    close_count = sum(1 for p in found if p.startswith("⟦/"))
    if open_count != close_count:
        errors.append(f"Нарушена парность тегов: открыто {open_count}, закрыто {close_count}")

    # 🚨 5. Проверка на непереведенные английские слова
    # Убираем ссылки из текста, чтобы они не считались ошибкой
    text_without_urls = re.sub(r'(https?://|www\.)\S+', '', translated_text)
    
    # Находим все английские слова длиной от 3 символов
    latin_words = LATIN_WORD_RE.findall(text_without_urls)
    
    if latin_words:
        # Берем первые 3 слова для лога, чтобы не спамить
        sample_words = list(set(latin_words))[:3]
        errors.append(f"В переводе остались английские слова: {', '.join(sample_words)}")

    return len(errors) == 0, errors
