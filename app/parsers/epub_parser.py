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

            html = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "lxml")

            order = 0

            for block in soup.find_all(BLOCK_TAGS):
                # Пропускаем контейнеры с вложенными блочными тегами
                if block.find(BLOCK_TAGS):
                    continue

                inner_html = block.decode_contents().strip()
                if not inner_html:
                    continue

                # ФИЛЬТР: короткие div-ы со служебным классом/id — это мусор.
                # Короткие div-ы БЕЗ класса — смысловой текст, переводим.
                if block.name == "div" and len(inner_html) < 30 and (block.get("class") or block.get("id")):
                    continue

                text_with_ph, mapping = extract_placeholders(inner_html)

                if not text_with_ph.strip():
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