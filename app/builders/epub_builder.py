"""Собирает EPUB с переводом, сохраняя вёрстку идеально."""
import os
import re
import zipfile
from pathlib import Path
from typing import Tuple

from bs4 import BeautifulSoup

from app.parsers.epub_parser import BLOCK_TAGS
from app.placeholders.extractor import extract_placeholders
from app.placeholders.restorer import restore_placeholders


SKIP_FILES = {
    "mimetype",
    "META-INF/container.xml",
    "content.opf",
    "toc.ncx",
    "toc.xhtml",
    "nav.xhtml",
}

# Убираем оставшиеся плейсхолдеры (если LLM что-то сломала)
LEFTOVER_PLACEHOLDER = re.compile(r"⟦[^⟧]*⟧")

# Markdown-очистка (умная):
# 1. # или ## или ### В НАЧАЛЕ СТРОКИ, за которыми идёт пробел → это заголовок, убираем решётки
MARKDOWN_HASH = re.compile(r"(?m)^\s*#{1,6}\s+")
# 2. **text** или __text__ — убираем обёртку, оставляем текст (только если внутри нет * или _)
MARKDOWN_BOLD = re.compile(r"\*{2}([^*\n]+?)\*{2}|__([^_\n]+?)__")
# 3. Одиночные * или _ в начале строки (markdown списки) — убираем
MARKDOWN_ITALIC_LINE = re.compile(r"(?m)^\s*[\*_]\s+")
# 4. Inline одинарные * или _ вокруг слова (только если буква внутри, чтобы не трогать ***)
MARKDOWN_ITALIC_INLINE = re.compile(r"(?<!\*)\*(?!\*)([^*\n]{2,}?)(?<!\*)\*(?!\*)")

# Длинный h1-h6 → превращаем в p
MAX_HEADING_LENGTH = 100

# Схлопываем множественные пробелы (кроме переносов строк)
MULTIPLE_SPACES = re.compile(r"[ \t]{2,}")


def _is_content_html(filename: str) -> bool:
    lower = filename.lower()
    if not (lower.endswith(".xhtml") or lower.endswith(".html") or lower.endswith(".htm")):
        return False
    if filename in SKIP_FILES:
        return False
    if filename.startswith("META-INF/"):
        return False
    base = filename.rsplit("/", 1)[-1].lower()
    if base in ("nav.xhtml", "toc.xhtml", "toc.ncx"):
        return False
    return True


def _clean_markdown(text: str) -> str:
    """Убирает markdown-разметку, добавленную LLM. НЕ трогает *** в начале строки."""
    # Не трогаем, если это целиком *** Gutenberg *** — тут ничего не делаем
    stripped = text.strip()
    if stripped.startswith("***") and stripped.endswith("***") and len(stripped) < 200:
        return text

    # 1. Убираем ** text ** и __ text __
    text = MARKDOWN_BOLD.sub(lambda m: m.group(1) or m.group(2), text)

    # 2. Убираем # в начале строк
    text = MARKDOWN_HASH.sub("", text)

    # 3. Убираем markdown-списки (* item, _ item)
    text = MARKDOWN_ITALIC_LINE.sub("", text)

    # 4. Убираем inline курсив (только если это НЕ ***)
    text = MARKDOWN_ITALIC_INLINE.sub(r"\1", text)

    # 5. Схлопываем множественные пробелы
    text = MULTIPLE_SPACES.sub(" ", text)

    return text.strip()


def build_translated_epub(
    source_path: str,
    output_path: str,
    translations: dict,
) -> Tuple[str, int]:
    src = Path(source_path)
    out = Path(output_path)

    if not src.exists():
        raise FileNotFoundError(f"Не найден файл: {source_path}")

    replaced_count = 0
    files_to_write = []

    with zipfile.ZipFile(src, "r") as zin:
        for entry in zin.infolist():
            filename = entry.filename
            data = zin.read(filename)

            if filename == "mimetype":
                files_to_write.append((entry, data, zipfile.ZIP_STORED))
                continue

            if _is_content_html(filename):
                try:
                    html = data.decode("utf-8", errors="ignore")
                    file_key = os.path.basename(filename).rsplit(".", 1)[0]

                    modified_html, this_replaced = _process_html(
                        html,
                        file_key=file_key,
                        translations=translations,
                    )
                    replaced_count += this_replaced["replaced"]
                    files_to_write.append(
                        (entry, modified_html.encode("utf-8"), zipfile.ZIP_DEFLATED)
                    )
                except Exception:
                    files_to_write.append((entry, data, zipfile.ZIP_DEFLATED))
            else:
                files_to_write.append((entry, data, zipfile.ZIP_DEFLATED))

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zout:
        for entry, data, compress_type in files_to_write:
            new_entry = zipfile.ZipInfo(entry.filename, date_time=entry.date_time)
            new_entry.compress_type = compress_type
            new_entry.external_attr = entry.external_attr
            zout.writestr(new_entry, data)

    return str(out), replaced_count


def _process_html(html: str, file_key: str, translations: dict) -> Tuple[str, dict]:
    soup = BeautifulSoup(html, "html.parser")

    order = 0
    replaced = 0

    for block in soup.find_all(BLOCK_TAGS):
        if block.find(BLOCK_TAGS):
            continue

        inner_html = block.decode_contents().strip()
        if not inner_html:
            continue

        text_with_ph, mapping = extract_placeholders(inner_html)
        if not text_with_ph.strip():
            continue

        seg_id = f"{file_key}__s{order}"
        order += 1

        if seg_id not in translations:
            continue

        translated_html = restore_placeholders(translations[seg_id], mapping)

        # Убираем оставшиеся плейсхолдеры
        translated_html = LEFTOVER_PLACEHOLDER.sub("", translated_html)

        # Убираем markdown-разметку, добавленную LLM
        translated_html = _clean_markdown(translated_html)

        tag_name = block.name
        tag_attrs = dict(block.attrs)

        # ФИКС: длинный h1-h6 → превращаем в p (это не заголовок, а абзац)
        if tag_name in ("h1", "h2", "h3", "h4", "h5", "h6"):
            if len(translated_html) > MAX_HEADING_LENGTH:
                tag_name = "p"

        wrapper = BeautifulSoup(
            f"<{tag_name}>{translated_html}</{tag_name}>",
            "html.parser",
        )
        new_tag = wrapper.find(tag_name)
        if new_tag is None:
            continue

        for attr_name, attr_value in tag_attrs.items():
            new_tag[attr_name] = attr_value

        block.replace_with(new_tag)
        replaced += 1

    if replaced == 0:
        return html, {"replaced": 0, "order_advance": order}

    return str(soup), {"replaced": replaced, "order_advance": order}
