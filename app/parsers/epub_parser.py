"""
Парсер EPUB. Извлекает текстовые сегменты с сохранением вёрстки.
"""
from pathlib import Path
from typing import List

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup

from app.parsers.base import BookParser, ParsedBook, TextSegment
from app.placeholders.extractor import extract_placeholders


BLOCK_TAGS = ["p", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "li", "div"]

# Классы служебных блоков Gutenberg
BOILERPLATE_CLASSES = {
    "pg-boilerplate",
    "pgheader",
    "pgfooter",
    "pg-header",
    "pg-footer",
    "transcriber",
    "transcriber-notes",
    "pgtranscriber",
}

# Служебные фразы — если сегмент их содержит, пропускаем
BOILERPLATE_PHRASES = [
    "START OF THE PROJECT GUTENBERG",
    "END OF THE PROJECT GUTENBERG",
    "START OF THIS PROJECT GUTENBERG",
    "END OF THIS PROJECT GUTENBERG",
    "START: FULL LICENSE",
    "Transcriber's Notes",
    "Transcriber’s Notes",
    "Updated editions will replace",
    "Creating the works from print editions",
    "PLEASE READ THIS BEFORE",
    "Most recently updated:",
    "**Section 1.",
    "Section 1. General Terms",
    "Section 2. Information about",
    "Section 3. Information about",
    "Section 4. Information about",
    "Section 5. General Information",
    "THE FULL PROJECT GUTENBERG",
    "1.A. By reading",
    "1.B. \"Project Gutenberg\"",
    "1.C. The Project Gutenberg",
    "1.D. The copyright laws",
    "1.E. Unless you have removed",
    "1.F.",
    "1.F.1.",
    "1.F.2.",
    "1.F.3.",
    "1.F.4.",
    "1.F.5.",
    "1.F.6.",
    "Professor Michael S. Hart",
    "This website includes information about Project Gutenberg",
]

# Имена файлов, которые пропускаем целиком (это footer/backmatter)
BOILERPLATE_FILENAMES_KEYWORDS = [
    "pg-footer",
    "pgfooter",
    "colophon",
    "backmatter",
    "back-matter",
    "end-matter",
]


class EpubParser(BookParser):
    """Парсер EPUB-файлов."""

    def supported_extensions(self) -> List[str]:
        return [".epub"]

    def parse(self, file_path: str) -> ParsedBook:
        book_path = Path(file_path)
        if not book_path.exists():
            raise FileNotFoundError(f"Файл не найден: {file_path}")

        book = epub.read_epub(str(book_path))

        title = self._get_meta(book, "title") or book_path.stem
        author = self._get_meta(book, "creator") or "Unknown"
        language = self._get_meta(book, "language") or "en"

        segments: List[TextSegment] = []

        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            chapter_name = item.get_name()
            file_key = Path(chapter_name).name.rsplit(".", 1)[0]

            # Пропускаем служебные файлы по имени
            if self._is_boilerplate_file(chapter_name):
                continue

            html = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "lxml")

            order = 0

            for block in soup.find_all(BLOCK_TAGS):
                if block.find(BLOCK_TAGS):
                    continue

                if self._is_boilerplate(block):
                    continue

                inner_html = block.decode_contents().strip()
                if not inner_html:
                    continue

                if block.name == "div" and len(inner_html) < 30 and (block.get("class") or block.get("id")):
                    continue

                text_with_ph, mapping = extract_placeholders(inner_html)

                if not text_with_ph.strip():
                    continue

                if self._has_boilerplate_phrase(text_with_ph):
                    continue

                segments.append(TextSegment(
                    id=f"{file_key}__s{order}",
                    text=text_with_ph,
                    chapter=chapter_name,
                    order=order,
                    mapping=mapping,
                ))
                order += 1

        return ParsedBook(
            title=title,
            author=author,
            language=language,
            segments=segments,
            metadata={
                "file_path": str(book_path),
                "total_segments": len(segments),
            },
        )

    def _is_boilerplate_file(self, filename: str) -> bool:
        """Пропускает файлы с служебными именами."""
        lower = filename.lower()
        for kw in BOILERPLATE_FILENAMES_KEYWORDS:
            if kw in lower:
                return True
        return False

    def _is_boilerplate(self, block) -> bool:
        classes = block.get("class") or []
        if isinstance(classes, str):
            classes = [classes]
        for cls in classes:
            if cls in BOILERPLATE_CLASSES:
                return True

        block_id = block.get("id") or ""
        if block_id.startswith(("pg-footer", "pg-header")):
            return True

        for parent in block.parents:
            parent_classes = parent.get("class") or []
            if isinstance(parent_classes, str):
                parent_classes = [parent_classes]
            for cls in parent_classes:
                if cls in BOILERPLATE_CLASSES:
                    return True
            parent_id = parent.get("id") or ""
            if parent_id.startswith(("pg-footer", "pg-header")):
                return True

        return False

    def _has_boilerplate_phrase(self, text: str) -> bool:
        upper = text.upper()
        for phrase in BOILERPLATE_PHRASES:
            if phrase.upper() in upper:
                return True
        return False

    @staticmethod
    def _get_meta(book: epub.EpubBook, field: str) -> str:
        try:
            values = book.get_metadata("DC", field)
            if values:
                return values[0][0]
        except Exception:
            pass
        return ""


def parse_epub(file_path: str) -> ParsedBook:
    return EpubParser().parse(file_path)
