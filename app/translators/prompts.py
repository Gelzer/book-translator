"""Все промпты для перевода в одном месте."""
import re


# ============================================================
# БАЗОВЫЙ СЛОВАРЬ ИМЁН И ТОПОНИМОВ
# ============================================================

COMMON_NAMES = {
    "John": "Джон", "James": "Джеймс", "Robert": "Роберт", "Michael": "Майкл",
    "William": "Уильям", "David": "Дэвид", "Richard": "Ричард", "Joseph": "Джозеф",
    "Thomas": "Томас", "Charles": "Чарльз", "Christopher": "Кристофер",
    "Daniel": "Дэниэл", "Matthew": "Мэтью", "Anthony": "Энтони", "Donald": "Дональд",
    "Mark": "Марк", "Paul": "Пол", "Steven": "Стивен", "Andrew": "Эндрю",
    "Kenneth": "Кеннет", "Joshua": "Джошуа", "George": "Джордж", "Kevin": "Кевин",
    "Brian": "Брайан", "Edward": "Эдвард", "Ronald": "Рональд", "Timothy": "Тимоти",
    "Jason": "Джейсон", "Jeffrey": "Джеффри", "Ryan": "Райан", "Jacob": "Джейкоб",
    "Gary": "Гэри", "Nicholas": "Николас", "Eric": "Эрик", "Jonathan": "Джонатан",
    "Stephen": "Стивен", "Larry": "Ларри", "Justin": "Джастин", "Scott": "Скотт",
    "Brandon": "Брэндон", "Benjamin": "Бенджамин", "Samuel": "Сэмюэл",
    "Gregory": "Грегори", "Frank": "Фрэнк", "Alexander": "Александр",
    "Raymond": "Рэймонд", "Patrick": "Патрик", "Jack": "Джек", "Dennis": "Деннис",
    "Jerry": "Джерри", "Tyler": "Тайлер", "Aaron": "Аарон", "Adam": "Адам",
    "Nathan": "Нэйтан", "Henry": "Генри", "Zachary": "Закари", "Douglas": "Дуглас",
    "Peter": "Питер", "Kyle": "Кайл", "Noah": "Ноа", "Ethan": "Итан",
    "Jeremy": "Джереми", "Walter": "Уолтер", "Christian": "Кристиан",
    "Keith": "Кит", "Roger": "Роджер", "Terry": "Терри", "Gerald": "Джеральд",
    "Harold": "Гарольд", "Sean": "Шон", "Austin": "Остин", "Carl": "Карл",
    "Arthur": "Артур", "Lawrence": "Лоуренс", "Dylan": "Дилан", "Jesse": "Джесси",
    "Jordan": "Джордан", "Bryan": "Брайан", "Billy": "Билли", "Bruce": "Брюс",
    "Albert": "Альберт", "Gabriel": "Габриэль", "Logan": "Логан", "Alan": "Алан",
    "Wayne": "Уэйн", "Roy": "Рой", "Ralph": "Ральф", "Randy": "Рэнди",
    "Eugene": "Юджин", "Vincent": "Винсент", "Russell": "Рассел", "Elijah": "Элайджа",
    "Louis": "Луи", "Bobby": "Бобби", "Philip": "Филип", "Johnny": "Джонни",
    "Bradley": "Брэдли", "Martin": "Мартин", "Craig": "Крейг", "Leroy": "Лерой",
    "Cyril": "Сайрил", "Hugh": "Хью", "Claude": "Клод", "Cecil": "Сесил",
    "Rufus": "Руфус", "Elam": "Элам", "Hubert": "Хьюберт",
    "Willoughby": "Уиллоуби", "Sylvester": "Сильвестр",
    "Ferdinand": "Фердинанд", "Herbert": "Герберт",
    "Montresor": "Монтрезор", "Fortunato": "Фортунато", "Luchesi": "Лукези",

    "Mary": "Мэри", "Patricia": "Патриция", "Jennifer": "Дженнифер",
    "Linda": "Линда", "Elizabeth": "Элизабет", "Barbara": "Барбара",
    "Susan": "Сьюзан", "Jessica": "Джессика", "Sarah": "Сара", "Karen": "Карен",
    "Nancy": "Нэнси", "Lisa": "Лиза", "Betty": "Бетти", "Margaret": "Маргарет",
    "Sandra": "Сандра", "Ashley": "Эшли", "Kimberly": "Кимберли", "Emily": "Эмили",
    "Donna": "Донна", "Michelle": "Мишель", "Carol": "Кэрол", "Amanda": "Аманда",
    "Dorothy": "Дороти", "Melissa": "Мелисса", "Deborah": "Дебора",
    "Stephanie": "Стефани", "Rebecca": "Ребекка", "Sharon": "Шэрон",
    "Laura": "Лора", "Cynthia": "Синтия", "Kathleen": "Кэтлин", "Amy": "Эми",
    "Angela": "Анджела", "Shirley": "Ширли", "Anna": "Анна", "Brenda": "Бренда",
    "Pamela": "Памела", "Emma": "Эмма", "Nicole": "Николь", "Helen": "Хелен",
    "Samantha": "Саманта", "Katherine": "Кэтрин", "Christine": "Кристин",
    "Debra": "Дебра", "Rachel": "Рэйчел", "Carolyn": "Кэролин", "Janet": "Джанет",
    "Catherine": "Кэтрин", "Maria": "Мария", "Heather": "Хизер", "Diane": "Диана",
    "Ruth": "Рут", "Julie": "Джули", "Olivia": "Оливия", "Joyce": "Джойс",
    "Virginia": "Вирджиния", "Victoria": "Виктория", "Kelly": "Келли",
    "Lauren": "Лорен", "Christina": "Кристина", "Joan": "Джоан",
    "Evelyn": "Эвелин", "Judith": "Джудит", "Megan": "Меган", "Cheryl": "Шерил",
    "Andrea": "Андреа", "Hannah": "Ханна", "Martha": "Марта",
    "Jacqueline": "Жаклин", "Frances": "Фрэнсис", "Gloria": "Глория",
    "Ann": "Энн", "Teresa": "Тереза", "Sara": "Сара", "Janice": "Джанис",
    "Jean": "Джин", "Alice": "Элис", "Madison": "Мэдисон", "Doris": "Дорис",
    "Abigail": "Эбигейл", "Julia": "Джулия", "Judy": "Джуди", "Grace": "Грейс",
    "Denise": "Дениз", "Amber": "Эмбер", "Marilyn": "Мэрилин",
    "Beverly": "Беверли", "Danielle": "Даниэль", "Theresa": "Тереза",
    "Sophia": "София", "Marie": "Мари", "Diana": "Диана", "Brittany": "Бриттани",
    "Natalie": "Натали", "Isabella": "Изабелла", "Charlotte": "Шарлотта",
    "Rose": "Роуз", "Alexis": "Алексис", "Kayla": "Кайла",
    "Bernice": "Бернис", "Loretta": "Лоретта", "Claudine": "Клодин",
    "Jennie": "Дженни", "Ethel": "Этель",
    "Adele": "Адель", "Violet": "Вайолет", "Annie": "Энни", "Selena": "Селина",
    "Luella": "Луэлла", "Elfreda": "Эльфреда", "Elphye": "Эльфи",
}

COMMON_PLACES = {
    "London": "Лондон", "Paris": "Париж", "New York": "Нью-Йорк",
    "Chicago": "Чикаго", "Boston": "Бостон", "Washington": "Вашингтон",
    "Los Angeles": "Лос-Анджелес", "San Francisco": "Сан-Франциско",
    "Berlin": "Берлин", "Moscow": "Москва", "Rome": "Рим",
    "Vienna": "Вена", "Madrid": "Мадрид", "Amsterdam": "Амстердам",
    "Brussels": "Брюссель", "Tokyo": "Токио", "Beijing": "Пекин",
    "Sydney": "Сидней", "Toronto": "Торонто", "Montreal": "Монреаль",
    "Naples": "Неаполь", "Venice": "Венеция", "Florence": "Флоренция",
    "Dublin": "Дублин", "Edinburgh": "Эдинбург", "Liverpool": "Ливерпуль",
    "Manchester": "Манчестер", "Birmingham": "Бирмингем",
    "Philadelphia": "Филадельфия", "Detroit": "Детройт",
    "Cleveland": "Кливленд", "Cincinnati": "Цинциннати",
    "New Orleans": "Новый Орлеан", "Memphis": "Мемфис",
    "England": "Англия", "France": "Франция", "Germany": "Германия",
    "Spain": "Испания", "Italy": "Италия", "Russia": "Россия",
    "America": "Америка", "United States": "Соединённые Штаты",
    "Canada": "Канада", "Australia": "Австралия", "China": "Китай",
    "Japan": "Япония", "India": "Индия", "Egypt": "Египет",
    "Scotland": "Шотландия", "Ireland": "Ирландия",
    "Wales": "Уэльс", "Switzerland": "Швейцария", "Sweden": "Швеция",
    "Norway": "Норвегия", "Denmark": "Дания", "Holland": "Голландия",
    "California": "Калифорния", "Texas": "Техас", "Florida": "Флорида",
    "Pennsylvania": "Пенсильвания", "Indiana": "Индиана",
    "Illinois": "Иллинойс", "Ohio": "Огайо", "Michigan": "Мичиган",
    "Virginia": "Вирджиния", "Nevada": "Невада",
    "Trafalgar Square": "Трафальгарская площадь",
    "Times Square": "Таймс-сквер",
    "Wall Street": "Уолл-стрит",
    "Fifth Avenue": "Пятая авеню",
    "Broadway": "Бродвей",
    "Hyde Park": "Гайд-парк",
    "West Point": "Вест-Пойнт",
    "White House": "Белый дом",
    "Capitol": "Капитолий",
    "Niagara Falls": "Ниагарский водопад",
    "Grand Central": "Гранд-Сентрал",
    "Pennsylvania Avenue": "Пенсильвания-авеню",
}

BASE_GLOSSARY = {**COMMON_NAMES, **COMMON_PLACES}


# ============================================================
# ОПРЕДЕЛЕНИЕ ПОЛА РАССКАЗЧИКА
# ============================================================

GENDER_DETECT_PROMPT = """Ты — литературный аналитик.

Тебе дан фрагмент текста на английском языке. Определи пол рассказчика (главного героя, от чьего лица идёт повествование).

Смотри на:
- Местоимения (he/him → male, she/her → female)
- Обращения к рассказчику
- Глаголы в первом лице — но их в английском нет, поэтому опирайся на контекст

Отвечай ОДНИМ СЛОВОМ:
- male — если рассказчик мужчина
- female — если рассказчица женщина
- unknown — если определить невозможно (например, текст от третьего лица, или рассказчик не человек)

Никаких пояснений. Только одно слово.
"""


def build_system_prompt(gender: str | None = None) -> str:
    """Системный промпт для перевода одного фрагмента."""
    base = """Ты — профессиональный литературный переводчик.

ПРАВИЛА:
1. Переводи точно, сохраняя смысл оригинала
2. Сохраняй стиль автора
3. Сохраняй ВСЕ плейсхолдеры вида ⟦...⟧ ровно как есть, НЕ переводи их
4. Имена собственные транслитерируй по правилам русского языка
5. Никаких пояснений — ТОЛЬКО перевод
6. НЕ используй markdown-разметку (никаких #, **, *, _). Только чистый текст.
7. Звуки (кашель, вздохи, восклицания) передавай естественными русскими аналогами:
   "Ugh! ugh!" → "Кх! кх!" или "Уф! уф!"
   "Ha! ha!" → "Ха! ха!"
   "He! he!" → "Хе! хе!"
   "Ah!" → "Ах!"
   "Oh!" → "О!"
   НЕ используй буквальные транслитерации типа "Уг! уг!"."""

    if gender == "male":
        base += """

КРИТИЧЕСКИ ВАЖНО (о поле рассказчика):
Рассказчик — МУЖЧИНА. Все глаголы от первого лица (я пошёл, я сказал, я подумал), причастия, прилагательные и краткие формы, относящиеся к рассказчику, должны быть в МУЖСКОМ роде."""
    elif gender == "female":
        base += """

КРИТИЧЕСКИ ВАЖНО (о поле рассказчика):
Рассказчица — ЖЕНЩИНА. Все глаголы от первого лица, причастия, прилагательные, относящиеся к рассказчице, должны быть в ЖЕНСКОМ роде."""

    return base


def build_batch_system_prompt(gender: str | None = None) -> str:
    """Системный промпт для пакетного перевода."""
    base = """Ты — профессиональный литературный переводчик.

На вход ты получаешь НЕСКОЛЬКО фрагментов текста, каждый помечен маркером.
Твоя задача — перевести каждый фрагмент отдельно и вернуть результат В ТОЧНО ТАКОМ ЖЕ формате.

ФОРМАТ ОТВЕТА (критически важен):
<<<SEG:идентификатор_1>>>
перевод первого фрагмента
<<<SEG:идентификатор_2>>>
перевод второго фрагмента

ПРАВИЛА:
1. Возвращай ВСЕ фрагменты, не пропускай ни один
2. Сохраняй идентификаторы после <<<SEG: в точности как получил
3. НЕ объединяй фрагменты, не меняй их порядок
4. Сохраняй ВСЕ плейсхолдеры вида ⟦...⟧ ровно как есть, НЕ переводи их
5. НЕ добавляй никаких пояснений, комментариев, вступлений
6. НЕ используй markdown-разметку (никаких #, **, *, _). Только чистый текст.
7. Звуки (кашель, вздохи, восклицания) передавай естественными русскими аналогами:
   "Ugh! ugh!" → "Кх! кх!" или "Уф! уф!"
   "Ha! ha!" → "Ха! ха!"
   "He! he!" → "Хе! хе!"
   НЕ используй буквальные транслитерации."""

    if gender == "male":
        base += """

КРИТИЧЕСКИ ВАЖНО (о поле рассказчика):
Рассказчик — МУЖЧИНА. Все глаголы от первого лица, причастия и прилагательные, относящиеся к рассказчику, должны быть в МУЖСКОМ роде."""
    elif gender == "female":
        base += """

КРИТИЧЕСКИ ВАЖНО (о поле рассказчицы):
Рассказчица — ЖЕНЩИНА. Все глаголы от первого лица, причастия и прилагательные, относящиеся к рассказчице, должны быть в ЖЕНСКОМ роде."""

    return base


# ============================================================
# QA-ПРОХОД (УЗКИЙ — ТОЛЬКО АНГЛИЙСКИЕ СЛОВА)
# ============================================================

QA_SYSTEM_PROMPT = """Ты — корректор русского текста.

Твоя ЕДИНСТВЕННАЯ задача: найти в тексте английские слова (написанные латиницей) и заменить их русскими эквивалентами.

ЧТО ДЕЛАТЬ:
- Найди слова, написанные латинскими буквами: "awake", "discouraging", "the", "and" и т.д.
- Замени их на русский перевод с учётом контекста
- Пример: "Джон уже был awake" → "Джон уже проснулся"
- Пример: "Так discouraging" → "Так обескураживающе"

ЧТО НЕ ДЕЛАТЬ (КРИТИЧЕСКИ ВАЖНО):
- НЕ трогай род глаголов и прилагательных
- НЕ переписывай предложения
- НЕ меняй стиль
- НЕ трогай плейсхолдеры вида ⟦...⟧ — оставь их без изменений
- НЕ удаляй и не добавляй ничего лишнего

Если английских слов НЕТ — верни текст БЕЗ ИЗМЕНЕНИЙ.

ФОРМАТ ОТВЕТА:
<<<SEG:идентификатор_1>>>
исправленный текст
<<<SEG:идентификатор_2>>>
исправленный текст
"""


# ============================================================
# ВСПОМОГАТЕЛЬНОЕ
# ============================================================

def _lang_name(code: str) -> str:
    lang_map = {
        "en": "английского",
        "es": "испанского",
        "it": "итальянского",
        "ru": "русского",
    }
    return lang_map.get(code, code)


def filter_glossary_for_text(text: str, glossary: dict) -> dict:
    """Возвращает только записи глоссария, встречающиеся в тексте."""
    if not text or not glossary:
        return {}
    result = {}
    for key, value in glossary.items():
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            result[key] = value
    return result


def _build_glossary_block(text: str, glossary: dict | None) -> str:
    if not glossary:
        return ""
    relevant = filter_glossary_for_text(text, glossary)
    if not relevant:
        return ""
    lines = [f'  "{k}" → "{v}"' for k, v in relevant.items()]
    return (
        "ОБЯЗАТЕЛЬНЫЙ ГЛОССАРИЙ (используй ТОЛЬКО эти переводы имён и мест):\n"
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
Верни результат строго в том же формате: маркер <<<SEG:id>>> и после него перевод.

{body}
"""


def build_qa_prompt(segments: list[tuple[str, str]]) -> str:
    body_parts = []
    for seg_id, text in segments:
        body_parts.append(f"<<<SEG:{seg_id}>>>\n{text}")

    body = "\n".join(body_parts)

    return f"""Проверь следующие фрагменты русского текста. Найди английские слова (латиницу) и замени их на русский перевод. Род глаголов, стиль и всё остальное НЕ трогай.

Верни результат в том же формате: маркер <<<SEG:id>>> и после него исправленный текст.

{body}
"""


SEGMENT_PATTERN = re.compile(
    r"<<<SEG:(.+?)>>>\s*\n(.*?)(?=<<<SEG:|$)",
    re.DOTALL,
)


def parse_batch_response(response: str) -> dict:
    result = {}
    for match in SEGMENT_PATTERN.finditer(response):
        seg_id = match.group(1).strip()
        text = match.group(2).strip()
        if seg_id and text:
            result[seg_id] = text
    return result
