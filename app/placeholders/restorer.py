"""Восстанавливает HTML-теги из плейсхолдеров после перевода."""
import re
from typing import Dict, List

PLACEHOLDER_PATTERN = re.compile(r"⟦(/?[A-ZА-Я]+\d+)⟧")


class PlaceholderRestorer:
    """Возвращает теги на место плейсхолдеров."""

    def __init__(self, mapping: Dict[str, str]) -> None:
        self.mapping = mapping

    def restore(self, text: str) -> str:
        def replacer(match: re.Match) -> str:
            key = match.group(0)
            return self.mapping.get(key, key)

        return PLACEHOLDER_PATTERN.sub(replacer, text)

    def find_missing(self, text: str) -> List[str]:
        """Находит плейсхолдеры, которые потерялись при переводе."""
        present = set(PLACEHOLDER_PATTERN.findall(text))
        present = {f"⟦{p}⟧" for p in present}
        expected = set(self.mapping.keys())
        return list(expected - present)


def restore_placeholders(text: str, mapping: Dict[str, str]) -> str:
    return PlaceholderRestorer(mapping).restore(text)