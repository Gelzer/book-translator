"""Собирает EPUB с переводом, сохраняя вёрстку."""
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

LEFTOVER_PLACEHOLDER = re.compile(r"⟦[^⟧]*⟧")

# Заголовки длиннее этого числа символов — это не заголовок, а абзац.
MAX_HEADING_LENGTH = 100


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

        tag_name = block.name
        tag_attrs = dict(block.attrs)

        # ФИКС: если h1-h6 содержит длинный текст — это не заголовок, а абзац.
        # Конвертируем в <p>, чтобы вёрстка не ломалась.
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
