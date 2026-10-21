"""Все промпты для перевода в одном месте."""
import re


# ============================================================
# БАЗОВЫЙ СЛОВАРЬ ИМЁН И ТОПОНИМОВ
# ============================================================
# Используется для ВСЕХ книг. Фильтруется по тексту перед отправкой,
# поэтому размер не влияет на стоимость запросов.
# Пополнять по мере накопления отзывов от пользователей.

COMMON_NAMES = {
    # Мужские английские
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
    "Rufus": "Руфус", "Elam": "Элам", "Walter": "Уолтер", "Kenneth": "Кеннет",
    "Hubert": "Хьюберт", "Willoughby": "Уиллоуби", "Sylvester": "Сильвестр",
    "Elam": "Элам", "Ferdinand": "Фердинанд", "Herbert": "Герберт",

    # Женские английские
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
    "Frances": "Фрэнсис", "Jennie": "Дженни", "Ethel": "Этель",
    "Adele": "Адель", "Violet": "Вайолет", "Annie": "Энни", "Selena": "Селина",
    "Luella": "Луэлла", "Elfreda": "Эльфреда", "Elphye": "Эльфи",
}

COMMON_PLACES = {
    # Города
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

    # Страны и регионы
    "England": "Англия", "France": "Франция", "Germany": "Германия",
    "Spain": "Испания", "Italy": "Италия", "Russia": "Россия",
    "America": "Америка", "United States": "Соединённые Штаты",
    "Canada": "Канада", "Australia": "Австралия", "China": "Китай",
    "Japan": "Япония", "India": "Индия", "Egypt": "Египет",
    "India": "Индия", "Scotland": "Шотландия", "Ireland": "Ирландия",
    "Wales": "Уэльс", "Switzerland": "Швейцария", "Sweden": "Швеция",
    "Norway": "Норвегия", "Denmark": "Дания", "Holland": "Голландия",
    "California": "Калифорния", "Texas": "Техас", "Florida": "Флорида",
    "Pennsylvania": "Пенсильвания", "Indiana": "Индиана",
    "Illinois": "Иллинойс", "Ohio": "Огайо", "Michigan": "Мичиган",
    "Virginia": "Вирджиния", "Nevada": "Невада",

    # Известные места
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

# Объединённый базовый глоссарий для всех книг
BASE_GLOSSARY = {**COMMON_NAMES, **COMMON_PLACES}


# ============================================================
# СИСТЕМНЫЕ ПРОМПТЫ
# ============================================================

SYSTEM_PROMPT = """Ты — профессиональный литературный переводчик с большим опытом перевода художественной литературы.
Твоя задача — перевести текст с максимальным сохранением смысла, стиля и эмоциональной окраски оригинала.

ПРАВИЛА ПЕРЕВОДА:
1. СТИЛЬ: Переводи живым, литературным русским языком. Избегай канцеляризмов, кальки с английского и дословного перевода. Диалоги должны звучать естественно.
2. ПОЛ: В русском языке глаголы прошедшего времени и прилагательные согласуются с полом персонажа. Если в оригинале "she said" — переводи "она сказала". Если пол персонажа неочевиден, опирайся на контекст. Не угадывай пол по профессии (врач, учитель).
3. ПЛЕЙСХОЛДЕРЫ: В тексте есть маркеры вида ⟦TAG1⟧ и ⟦/TAG1⟧. Это HTML-теги (курсив, жирный шрифт). Копируй их В ТОЧНОСТИ, не добавляй пробелы внутри маркеров, не переводи их и не меняй их порядок.
4. ИМЕНА: Если имя есть в глоссарии — используй его. Если нет — транслитерируй по правилам практической транскрипции.
5. ФОРМАТ: Не добавляй никаких пояснений, вступлений вроде "Вот перевод:" или комментариев. Выдавай ТОЛЬКО чистый переведённый текст.
"""

BATCH_SYSTEM_PROMPT = """Ты — профессиональный литературный переводчик с большим опытом перевода художественной литературы.
На вход ты получаешь НЕСКОЛЬКО фрагментов текста, каждый помечен маркером <<<SEG:идентификатор>>>.
Твоя задача — перевести каждый фрагмент и вернуть результат В ТОЧНО ТАКОМ ЖЕ ФОРМАТЕ.

ФОРМАТ ОТВЕТА (критически важен):
<<<SEG:идентификатор_1>>>
перевод первого фрагмента
<<<SEG:идентификатор_2>>>
перевод второго фрагмента

ПРАВИЛА:
1. ВОЗВРАЩАЙ ВСЕ ФРАГМЕНТЫ. Не пропускай ни один, не объединяй и не меняй их порядок.
2. ИДЕНТИФИКАТОРЫ: Сохраняй идентификаторы после <<<SEG: в точности как получил (без пробелов).
3. СТИЛЬ: Литературный, живой русский язык. Диалоги — естественные.
4. ПОЛ: Согласовывай глаголы прошедшего времени с полом персонажа (она сказала / он сказал).
5. ПЛЕЙСХОЛДЕРЫ: Сохраняй маркеры вида ⟦TAG1⟧ и ⟦/TAG1⟧ ровно как есть.
6. НИКАКИХ пояснений, комментариев или вступлений. Только перевод.
"""


# ============================================================
# ФИЛЬТРАЦИЯ ГЛОССАРИЯ
# ============================================================

def filter_glossary_for_text(text: str, glossary: dict) -> dict:
    """
    Возвращает только те записи глоссария, чей ключ встречается в тексте.
    Это критично для экономии токенов: вместо 250 имён отправляем только 5-10,
    которые реально есть в конкретном фрагменте.
    """
    if not text or not glossary:
        return {}

    result = {}
    for key, value in glossary.items():
        # Ищем ключ как отдельное слово (с границей слова, регистронезависимо)
        pattern = r"\b" + re.escape(key) + r"\b"
        if re.search(pattern, text, re.IGNORECASE):
            result[key] = value
    return result


# ============================================================
# ФОРМИРОВАНИЕ ПРОМПТОВ
# ============================================================

def _lang_name(code: str) -> str:
    lang_map = {
        "en": "английского",
        "es": "испанского",
        "it": "итальянского",
        "ru": "русского",
    }
    return lang_map.get(code, code)


def _build_glossary_block(text: str, glossary: dict | None) -> str:
    """Собирает блок глоссария, отфильтрованный по тексту."""
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
    """Промпт для перевода ОДНОГО фрагмента."""
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
    """Промпт для перевода БАТЧА фрагментов."""
    src = _lang_name(source_lang)
    tgt = _lang_name(target_lang)

    # Объединяем весь текст батча для фильтрации глоссария
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


# ============================================================
# ПАРСИНГ ОТВЕТА БАТЧА
# ============================================================

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
