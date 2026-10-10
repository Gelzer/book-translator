"""Клиент ЮKassa. Работает с тестовым и боевым магазином одинаково."""
import uuid
import httpx

from config import settings


YOOKASSA_API_URL = "https://api.yookassa.ru/v3"


class YooKassaClient:
    def __init__(self):
        self.shop_id = settings.YOOKASSA_SHOP_ID
        self.secret_key = settings.YOOKASSA_SECRET_KEY

    def _auth(self) -> tuple:
        return (self.shop_id, self.secret_key)

    def create_payment(
        self,
        amount_rub: int,
        description: str,
        return_url: str,
        metadata: dict | None = None,
    ) -> dict:
        """Создаёт платёж. Возвращает dict с полем confirmation.confirmation_url."""
        if not self.shop_id or not self.secret_key:
            raise ValueError("ЮKassa не настроена: нет shop_id или secret_key")

        url = f"{YOOKASSA_API_URL}/payments"
        payload = {
            "amount": {"value": f"{amount_rub}.00", "currency": "RUB"},
            "capture": True,
            "confirmation": {"type": "redirect", "return_url": return_url},
            "description": description[:128],
        }
        if metadata:
            payload["metadata"] = metadata

        headers = {"Idempotence-Key": uuid.uuid4().hex}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers, auth=self._auth())
            resp.raise_for_status()
            return resp.json()

    def get_payment(self, payment_id: str) -> dict:
        """Проверяет статус платежа."""
        url = f"{YOOKASSA_API_URL}/payments/{payment_id}"
        with httpx.Client(timeout=30.0) as client:
            resp = client.get(url, auth=self._auth())
            resp.raise_for_status()
            return resp.json()


client = YooKassaClient()