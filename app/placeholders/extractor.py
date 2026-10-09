"""Заменяет HTML-теги на плейсхолдеры."""
import re
from typing import Tuple, Dict, List


# Длинные теги — раньше, чтобы `sub` не съедался как `s`
TAG_PATTERN = re.compile(
    r"<(/?)(strong|em|sup|sub|span|i|b|u|s|a)\b([^>]*)>",
    re.IGNORECASE,
)


class PlaceholderExtractor:
    """Заменяет теги на плейсхолдеры с правильной парностью open/close."""

    def __init__(self) -> None:
        self.mapping: Dict[str, str] = {}
        self._counter = 0
        self._stack: List[Tuple[str, int]] = []

    def extract(self, html: str) -> Tuple[str, Dict[str, str]]:
        self.mapping = {}
        self._counter = 0
        self._stack = []

        def replacer(match: re.Match) -> str:
            is_closing = match.group(1) == "/"
            tag_name = match.group(2).lower()
            attrs = match.group(3) or ""

            if is_closing:
                num = None
                for i in range(len(self._stack) - 1, -1, -1):
                    if self._stack[i][0] == tag_name:
                        num = self._stack[i][1]
                        del self._stack[i]
                        break
                if num is None:
                    self._counter += 1
                    num = self._counter
                key = f"{tag_name.upper()}{num}"
                placeholder = f"⟦/{key}⟧"
                original = f"</{tag_name}>"
            else:
                self._counter += 1
                num = self._counter
                self._stack.append((tag_name, num))
                key = f"{tag_name.upper()}{num}"
                placeholder = f"⟦{key}⟧"
                original = f"<{tag_name}{attrs}>"

            self.mapping[placeholder] = original
            return placeholder

        result = TAG_PATTERN.sub(replacer, html)
        return result, self.mapping


def extract_placeholders(html: str) -> Tuple[str, Dict[str, str]]:
    return PlaceholderExtractor().extract(html)