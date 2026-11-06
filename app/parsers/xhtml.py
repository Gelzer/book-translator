"""Разбор XHTML-файлов EPUB с максимальным сохранением вёрстки."""
import re
from html.entities import html5 as HTML5_ENTITIES
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from lxml import etree


BLOCK_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6",
              "blockquote", "li", "div", "td", "th"]

_NAMED_ENTITY_RE = re.compile(r"&([a-zA-Z][a-zA-Z0-9]+);")
_UNESCAPED_AMP_RE = re.compile(r"&(?![a-zA-Z0-9#]+;)")


def _entity_to_char(name: str) -> Optional[str]:
    if name in HTML5_ENTITIES:
        value = HTML5_ENTITIES[name]
    elif name + ";" in HTML5_ENTITIES:
        value = HTML5_ENTITIES[name + ";"]
    else:
        return None
    return value if len(value) == 1 else None


def _clean_entities(html: str) -> str:
    """Заменяет HTML-сущности (&nbsp;) и одиночные & на валидный XML."""
    def repl(m):
        ch = _entity_to_char(m.group(1))
        return f"&#{ord(ch)};" if ch else m.group(0)
    
    # 1. Меняем именованные сущности
    html = _NAMED_ENTITY_RE.sub(repl, html)
    # 2. Чиним неэкранированные амперсанды (например, AT&T), которые ломают XML
    html = _UNESCAPED_AMP_RE.sub("&amp;", html)
    return html


def _check_xml(cleaned_html: str) -> Optional[str]:
    """Возвращает None если XML валиден, иначе текст ошибки."""
    try:
        parser = etree.XMLParser(load_dtd=False, no_network=True,
                                 resolve_entities=False, huge_tree=True)
        etree.fromstring(cleaned_html.encode("utf-8"), parser=parser)
        return None
    except etree.XMLSyntaxError as e:
        print(f"🚨 LXML SYNTAX ERROR: {e}") # <--- ОТЛАДКА
        return str(e)
    except Exception as e:
        print(f"🚨 LXML OTHER ERROR: {e}")  # <--- ОТЛАДКА
        return str(e)


def parse_xhtml(html: str) -> Tuple[BeautifulSoup, Optional[str]]:
    """Парсит XHTML. Возвращает (soup, error_or_none)."""
    # Сначала чистим сущности, чтобы они не мешали проверке XML
    cleaned = _clean_entities(html)
    error = _check_xml(cleaned)

    if error is None:
        print(f"✅ LXML: Ошибок нет. Длина файла: {len(cleaned)} символов.") # <--- ОТЛАДКА
        try:
            return BeautifulSoup(cleaned, "lxml-xml"), None
        except Exception as e:
            error = str(e)

    return BeautifulSoup(html, "lxml"), error


def iter_block_tags(soup: BeautifulSoup):
    """Итерирует блоки для перевода (без вложенных блоков)."""
    for block in soup.find_all(BLOCK_TAGS):
        if block.find(BLOCK_TAGS):
            continue
        yield block
