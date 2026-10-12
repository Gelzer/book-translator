"""Все промпты для перевода в одном месте."""
import re


GLOSSARY = {
    "Ade": "Эйд",
    "George Ade": "Джордж Эйд",
    "Ade's Fables": "Сказки Эйда",
    "John T. McCutcheon": "Джон Т. Маккатчен",
    "Montresor": "Монтрезор",
    "Fortunato": "Фортунато",
}


SYSTEM_PROMPT = """Ты — профессиональный литературный переводчик.

ПРАВИЛА:
1. Переводи точно, сохраняя смысл и стиль оригинала
2. Сохраняй все плейсхолдеры вида ⟦...⟧ ровно как есть, НЕ переводи их содержимое
3. Имена собственные транслитерируй по правилам русского языка
4. Никаких пояснений, комментариев, markdown — ТОЛЬКО перевод
"""


BATCH_SYSTEM_PROMPT = """Ты — профессиональный литературный переводчик.

На вход ты получаешь НЕСКОЛЬКО фрагментов, каждый помечен маркером.
Переведи каждый фрагмент и верни результат В ТОЧНО ТАКОМ ЖЕ формате.

ФОРМАТ ОТВЕТА:
<<<SEG:идентификатор_1>>>
перевод первого фрагмента
<<<SEG:идентификатор_2>>>
перевод второго фрагмента

ПРАВИЛА:
1. Возвращай ВСЕ фрагменты, не пропускай ни один
2. Сохраняй идентификаторы после <<<SEG: в точности как получил
3. НЕ объединяй фрагменты, не меняй их порядок
4. Сохраняй ВСЕ плейсхолдеры вида ⟦...⟧ ровно как есть
5. Никаких пояснений, комментариев, markdown — только перевод
"""


def _lang_name(code: str) -> str:
    lang_map = {
        "en": "английского",
        "es": "испанского",
        "it": "итальянского",
        "ru": "русского",
    }
    return lang_map.get(code, code)


def _build_glossary_block(text: str, glossary: dict | None) -> str:
    """Собирает блок глоссария, только для имён, которые есть в тексте."""
    if not glossary:
        return ""

    relevant = {}
    for key, value in glossary.items():
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            relevant[key] = value

    if not relevant:
        return ""

    lines = [f'  "{k}" → "{v}"' for k, v in relevant.items()]
    return (
        "ГЛОССАРИЙ (используй эти переводы имён):\n"
        + "\n".join(lines) + "\n\n"
    )


def build_user_prompt(
    text: str,
    source_lang: str = "en",
    target_lang: str = "ru",
    glossary: dict | None = None,
) -> str:
    src = _lang_name(source_lang)
    tgt = _lang_name(target_lang)
    glossary_block = _build_glossary_block(text, glossary)

    return f"""{glossary_block}Переведи следующий текст с {src} на {tgt} язык.

ТЕКСТ:
{text}"""


def build_batch_prompt(
    segments: list[tuple[str, str]],
    source_lang: str = "en",
    target_lang: str = "ru",
    glossary: dict | None = None,
) -> str:
    src = _lang_name(source_lang)
    tgt = _lang_name(target_lang)

    combined_text = "\n".join(text for _, text in segments)
    glossary_block = _build_glossary_block(combined_text, glossary)

    body_parts = []
    for seg_id, text in segments:
        body_parts.append(f"<<<SEG:{seg_id}>>>\n{text}")

    body = "\n".join(body_parts)

    return f"""{glossary_block}Переведи следующие фрагменты с {src} на {tgt} язык.
Верни результат в том же формате: маркер <<<SEG:id>>> и после него перевод.

{body}
"""


SEGMENT_PATTERN = re.compile(
    r"<<<SEG:(.+?)>>>\s*\n(.*?)(?=<<<SEG:|$)",
    re.DOTALL,
)


def parse_batch_response(response: str) -> dict:
    """Парсит ответ LLM. Возвращает {segment_id: translated_text}."""
    result = {}
    for match in SEGMENT_PATTERN.finditer(response):
        seg_id = match.group(1).strip()
        text = match.group(2).strip()
        if seg_id and text:
            result[seg_id] = text
    return result
