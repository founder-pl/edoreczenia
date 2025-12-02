"""
Klient REST API e-Doręczeń dla middleware synchronizującego.
"""
import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
import structlog

from .config import Settings

logger = structlog.get_logger(__name__)


@dataclass
class OAuth2Token:
    """Token OAuth2."""

    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_expired(self) -> bool:
        """Sprawdza czy token wygasł."""
        expiry = self.created_at + timedelta(seconds=self.expires_in - 60)
        return datetime.now() >= expiry


@dataclass
class EDoreczeniaMessage:
    """Wiadomość z e-Doręczeń."""

    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    content: str
    content_html: Optional[str]
    attachments: list[dict[str, Any]]
    received_at: datetime
    status: str
    epo: Optional[dict[str, Any]]  # Elektroniczne Poświadczenie Odbioru
    raw_data: dict[str, Any]

    @property
    def has_attachments(self) -> bool:
        """Czy wiadomość ma załączniki."""
        return len(self.attachments) > 0

    @property
    def is_read(self) -> bool:
        """Czy wiadomość została przeczytana."""
        return self.status in ("READ", "OPENED")


class EDoreczeniaClient:
    """Klient synchroniczny API e-Doręczeń."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: Optional[OAuth2Token] = None
        self._client: Optional[httpx.Client] = None

    def __enter__(self):
        self._client = httpx.Client(timeout=30.0)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            self._client.close()

    def _ensure_token(self) -> str:
        """Zapewnia ważny token OAuth2."""
        if self._token is None or self._token.is_expired:
            self._refresh_token()
        return self._token.access_token

    def _refresh_token(self) -> None:
        """Odświeża token OAuth2."""
        logger.info("Odświeżanie tokenu OAuth2")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.settings.edoreczenia_client_id,
            "client_secret": self.settings.edoreczenia_client_secret.get_secret_value(),
        }

        try:
            response = self._client.post(self.settings.edoreczenia_token_url, data=data)
            response.raise_for_status()
            token_data = response.json()

            self._token = OAuth2Token(
                access_token=token_data["access_token"],
                token_type=token_data.get("token_type", "Bearer"),
                expires_in=token_data.get("expires_in", 3600),
                refresh_token=token_data.get("refresh_token"),
            )
            logger.info("Token OAuth2 odświeżony pomyślnie")

        except httpx.HTTPError as e:
            logger.error("Błąd podczas odświeżania tokenu", error=str(e))
            raise

    def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Wykonuje żądanie do API."""
        token = self._ensure_token()
        url = f"{self.settings.edoreczenia_api_base_url}/{endpoint}"

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/json"

        try:
            response = self._client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}

        except httpx.HTTPError as e:
            logger.error("Błąd API", method=method, endpoint=endpoint, error=str(e))
            raise

    def get_messages(
        self,
        folder: str = "inbox",
        limit: int = 50,
        offset: int = 0,
        since: Optional[datetime] = None,
    ) -> list[EDoreczeniaMessage]:
        """Pobiera listę wiadomości."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages"

        params = {
            "limit": limit,
            "offset": offset,
            "folder": folder,
        }

        if since:
            params["since"] = since.isoformat()

        data = self._request("GET", endpoint, params=params)
        messages = []

        for item in data.get("messages", []):
            msg = self._parse_message(item)
            messages.append(msg)

        logger.info("Pobrano wiadomości z e-Doręczeń", count=len(messages), folder=folder)
        return messages

    def get_message(self, message_id: str) -> EDoreczeniaMessage:
        """Pobiera szczegóły wiadomości."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}"

        data = self._request("GET", endpoint)
        return self._parse_message(data)

    def get_attachment(self, message_id: str, attachment_id: str) -> tuple[bytes, str, str]:
        """
        Pobiera załącznik.

        Zwraca: (content, filename, content_type)
        """
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}/attachments/{attachment_id}"

        token = self._ensure_token()
        url = f"{self.settings.edoreczenia_api_base_url}/{endpoint}"

        response = self._client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()

        # Pobierz metadane z nagłówków
        content_disposition = response.headers.get("Content-Disposition", "")
        content_type = response.headers.get("Content-Type", "application/octet-stream")

        # Wyciągnij nazwę pliku
        filename = "attachment"
        if "filename=" in content_disposition:
            import re

            match = re.search(r'filename="?([^";\n]+)"?', content_disposition)
            if match:
                filename = match.group(1)

        return response.content, filename, content_type

    def send_message(
        self,
        recipients: list[str],
        subject: str,
        content: str,
        attachments: Optional[list[dict]] = None,
    ) -> dict[str, Any]:
        """Wysyła wiadomość."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages"

        message_data = {
            "recipients": [{"address": r} for r in recipients],
            "subject": subject,
            "content": content,
            "attachments": attachments or [],
        }

        result = self._request("POST", endpoint, json=message_data)
        logger.info("Wiadomość wysłana do e-Doręczeń", message_id=result.get("messageId"))
        return result

    def mark_as_read(self, message_id: str) -> None:
        """Oznacza wiadomość jako przeczytaną."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}/status"

        self._request("PUT", endpoint, json={"status": "READ"})
        logger.debug("Wiadomość oznaczona jako przeczytana", message_id=message_id)

    def get_epo(self, message_id: str) -> Optional[dict[str, Any]]:
        """Pobiera Elektroniczne Poświadczenie Odbioru."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}/epo"

        try:
            return self._request("GET", endpoint)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    def _parse_message(self, data: dict[str, Any]) -> EDoreczeniaMessage:
        """Parsuje dane wiadomości z API."""
        return EDoreczeniaMessage(
            message_id=data.get("messageId", ""),
            subject=data.get("subject", "(brak tematu)"),
            sender=data.get("sender", {}).get("address", ""),
            recipients=[r.get("address", "") for r in data.get("recipients", [])],
            content=data.get("content", ""),
            content_html=data.get("contentHtml"),
            attachments=data.get("attachments", []),
            received_at=datetime.fromisoformat(
                data.get("receivedAt", datetime.now().isoformat())
            ),
            status=data.get("status", "RECEIVED"),
            epo=data.get("epo"),
            raw_data=data,
        )
