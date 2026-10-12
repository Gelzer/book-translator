"""Клиент для GenAPI (OpenAI-совместимый формат)."""
import httpx

from config import settings
from app.translators.prompts import (
    GENDER_DETECT_PROMPT,
    QA_SYSTEM_PROMPT,
    build_system_prompt,
    build_batch_system_prompt,
    build_user_prompt,
    build_batch_prompt,
    build_qa_prompt,
    parse_batch_response,
    BASE_GLOSSARY,
)


class GenAPIClient:
    """Клиент для отправки запросов к GenAPI."""

    def __init__(self) -> None:
        self.base_url = settings.GENAPI_BASE_URL.rstrip("/")
        self.api_key = settings.GENAPI_API_KEY
        self.model = settings.GENAPI_MODEL
        self.timeout = httpx.Timeout(300.0, connect=10.0)

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _chat(
        self,
        system: str,
        user: str,
        temperature: float = 0.3,
        max_tokens: int | None = None,
    ) -> str:
        if not self.api_key:
            raise ValueError("GENAPI_API_KEY не задан в .env")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        with httpx.Client(timeout=self.timeout) as client:
            response = client.post(url, headers=self._headers(), json=payload)
            response.raise_for_status()
            data = response.json()

        try:
            return data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Неожиданный ответ от GenAPI: {data}") from e

    def detect_narrator_gender(self, sample_text: str) -> str:
        """
        Определяет пол рассказчика по фрагменту текста.
        Возвращает 'male', 'female' или 'unknown'.
        """
        if settings.MOCK_TRANSLATION:
            return "male"

        try:
            raw = self._chat(
                GENDER_DETECT_PROMPT,
                sample_text[:3000],
                temperature=0.0,
                max_tokens=20,
            )
        except Exception:
            return "unknown"

        raw_lower = raw.lower()
        if "female" in raw_lower:
            return "female"
        if "male" in raw_lower:
            return "male"
        return "unknown"

    def translate(
        self,
        text: str,
        source_lang: str = "en",
        target_lang: str = "ru",
        temperature: float = 0.3,
        glossary: dict | None = None,
        gender: str | None = None,
    ) -> str:
        if settings.MOCK_TRANSLATION:
            return f"[ТЕСТ] {text[:120]}..."
        user = build_user_prompt(text, source_lang, target_lang, glossary)
        system = build_system_prompt(gender)
        return self._chat(system, user, temperature)

    def translate_batch(
        self,
        segments: list[tuple[str, str]],
        source_lang: str = "en",
        target_lang: str = "ru",
        temperature: float = 0.3,
        glossary: dict | None = None,
        gender: str | None = None,
    ) -> dict:
        if settings.MOCK_TRANSLATION:
            return {seg_id: f"[ТЕСТ] {text[:120]}..." for seg_id, text in segments}
        user = build_batch_prompt(segments, source_lang, target_lang, glossary)
        system = build_batch_system_prompt(gender)
        raw = self._chat(system, user, temperature, max_tokens=4000)
        return parse_batch_response(raw)

    def review_batch(
        self,
        segments: list[tuple[str, str]],
        temperature: float = 0.1,
    ) -> dict:
        """QA-проход: только замена английских слов на русские."""
        if settings.MOCK_TRANSLATION:
            return {seg_id: text for seg_id, text in segments}
        user = build_qa_prompt(segments)
        raw = self._chat(QA_SYSTEM_PROMPT, user, temperature, max_tokens=4000)
        return parse_batch_response(raw)


client = GenAPIClient()


def detect_narrator_gender(sample_text: str) -> str:
    return client.detect_narrator_gender(sample_text)


def translate_text(
    text: str,
    source_lang: str = "en",
    target_lang: str = "ru",
    glossary: dict | None = None,
    gender: str | None = None,
) -> str:
    if glossary is None:
        glossary = BASE_GLOSSARY
    return client.translate(text, source_lang, target_lang, glossary=glossary, gender=gender)


def translate_batch(
    segments: list[tuple[str, str]],
    source_lang: str = "en",
    target_lang: str = "ru",
    glossary: dict | None = None,
    gender: str | None = None,
) -> dict:
    if glossary is None:
        glossary = BASE_GLOSSARY
    return client.translate_batch(segments, source_lang, target_lang, glossary=glossary, gender=gender)


def review_batch(segments: list[tuple[str, str]]) -> dict:
    return client.review_batch(segments)
