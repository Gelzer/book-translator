"""Разбор XHTML-файлов EPUB с максимальным сохранением вёрстки."""
import re
from html.entities import html5 as HTML5_ENTITIES
from typing import Optional, Tuple

from bs4 import BeautifulSoup
from lxml import etree


BLOCK_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6",
              "blockquote", "li", "div", "td", "th"]

_NAMED_ENTITY_RE = re.compile(r"&([a-zA-Z][a-zA-Z0-9]+);")


def _entity_to_char(name: str) -> Optional[str]:
    if name in HTML5_ENTITIES:
        value = HTML5_ENTITIES[name]
    elif name + ";" in HTML5_ENTITIES:
        value = HTML5_ENTITIES[name + ";"]
    else:
        return None
    return value if len(value) == 1 else None


def _replace_named_entities(html: str) -> str:
    """&nbsp; → &#160;, чтобы строгий XML-парсер прожевал."""
    def repl(m):
        ch = _entity_to_char(m.group(1))
        return f"&#{ord(ch)};" if ch else m.group(0)
    return _NAMED_ENTITY_RE.sub(repl, html)


def _check_xml(html: str) -> Optional[str]:
    """None если XML валиден (или ошибка только про named entities), иначе текст ошибки."""
    try:
        parser = etree.XMLParser(load_dtd=False, no_network=True,
                                 resolve_entities=False, huge_tree=True)
        etree.fromstring(html.encode("utf-8"), parser=parser)
        return None
    except etree.XMLSyntaxError as e:
        msg = str(e)
        if "Entity" in msg and "not defined" in msg:
            return None  # entities развернём сами — это не поломка
        return msg
    except Exception as e:
        return str(e)


def parse_xhtml(html: str) -> Tuple[BeautifulSoup, Optional[str]]:
    """Парсит XHTML. Возвращает (soup, error_or_none).

    error — текст для пользователя, если файл реально сломан.
    При ошибке всё равно возвращает soup (через HTML-фолбэк), чтобы книга обработалась.
    """
    error = _check_xml(html)

    if error is None:
        cleaned = _replace_named_entities(html)
        try:
            return BeautifulSoup(cleaned, "lxml-xml"), None
        except Exception:
            pass

    return BeautifulSoup(html, "lxml"), error


def iter_block_tags(soup: BeautifulSoup):
    """Итерирует блоки для перевода (без вложенных блоков)."""
    for block in soup.find_all(BLOCK_TAGS):
        if block.find(BLOCK_TAGS):
            continue
        yield block
