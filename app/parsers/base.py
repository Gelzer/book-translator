"""Базовый интерфейс для всех парсеров книг."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List


@dataclass
class TextSegment:
    """Один текстовый фрагмент для перевода."""
    id: str           # уникальный ID (например, "ch1_s3")
    text: str         # текст с плейсхолдерами вместо тегов
    chapter: str      # имя файла главы
    order: int        # порядок в книге
    mapping: dict = None  # ⟦SPAN1⟧ → <span>, чтобы потом восстановить HTML


@dataclass
class ParsedBook:
    """Результат парсинга книги."""
    title: str
    author: str
    language: str
    segments: List[TextSegment]
    metadata: dict


class BookParser(ABC):
    """Абстрактный парсер. Наследники: EpubParser, DocxParser, PdfParser."""

    @abstractmethod
    def parse(self, file_path: str) -> ParsedBook:
        """Извлекает сегменты из файла."""
        pass

    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Список расширений, которые поддерживает парсер."""
        pass