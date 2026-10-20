"""Детерминированные проверки качества перевода (без вызова LLM)."""
import re
from typing import Dict, List, Tuple

# Ищем плейсхолдеры вида ⟦EM1⟧ или ⟦/EM1⟧
PLACEHOLDER_RE = re.compile(r"⟦\s*(/?[A-ZА-ЯЁ]+\d+)\s*⟧")

def validate_translation(
    original_text: str,
    translated_text: str,
    mapping: Dict[str, str]
) -> Tuple[bool, List[str]]:
    """
    Проверяет качество перевода.
    Возвращает (is_valid, list_of_errors).
    """
    errors = []

    # 1. Проверка на пустой ответ
    if not translated_text or not translated_text.strip():
        return False, ["Модель вернула пустой перевод"]

    # 2. Проверка на "галлюцинации" по длине (перевод не должен быть в 4 раза короче или в 4 раза длиннее)
    # Русский текст обычно на 10-20% длиннее английского, но не в 4 раза.
    len_orig = max(len(original_text.strip()), 1)
    len_trans = len(translated_text.strip())
    ratio = len_trans / len_orig
    if ratio < 0.25:
        errors.append(f"Подозрительно короткий перевод (ratio {ratio:.2f})")
    elif ratio > 4.0:
        errors.append(f"Подозрительно длинный перевод (ratio {ratio:.2f})")

    # 3. Проверка плейсхолдеров
    # Собираем все плейсхолдеры из оригинала (по mapping)
    expected = set(mapping.keys())
    
    # Собираем плейсхолдеры из перевода
    found_matches = PLACEHOLDER_RE.findall(translated_text)
    found = {f"⟦{m}⟧" for m in found_matches}

    missing = expected - found
    extra = found - expected

    if missing:
        # Ограничиваем вывод, чтобы не спамить лог
        sample = list(missing)[:3]
        errors.append(f"Потеряны плейсхолдеры: {', '.join(sample)}")
    if extra:
        sample = list(extra)[:3]
        errors.append(f"Добавлены лишние плейсхолдеры: {', '.join(sample)}")

    # 4. Проверка парности (открыт/закрыт)
    # Быстрая эвристика: если количество открывающих != количеству закрывающих
    open_count = sum(1 for p in found if not p.startswith("⟦/"))
    close_count = sum(1 for p in found if p.startswith("⟦/"))
    if open_count != close_count:
        errors.append(f"Нарушена парность тегов: открыто {open_count}, закрыто {close_count}")

    return len(errors) == 0, errors