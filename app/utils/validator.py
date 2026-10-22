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

    # 🚨 5. Проверка на непереведенную латиницу (Английские слова в русском тексте)
    # Ищем английские буквы (исключая возможные URL и имена собственные из глоссария)
    latin_chars = re.findall(r'[a-zA-Z]', translated_text)
    # Если осталось больше 10 английских букв — это явный косяк перевода
    if len(latin_chars) > 10:
        errors.append(f"В переводе осталось слишком много английских букв (возможно, кусок текста не переведен)")

    return len(errors) == 0, errors
