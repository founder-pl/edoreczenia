"""
Klient REST API e-Doręczeń z obsługą OAuth2.
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
class Message:
    """Reprezentacja wiadomości e-Doręczeń."""

    message_id: str
    subject: str
    sender: str
    recipients: list[str]
    content: str
    attachments: list[dict[str, Any]]
    received_at: datetime
    status: str
    folder: str = "INBOX"
    flags: list[str] = field(default_factory=list)
    raw_data: dict[str, Any] = field(default_factory=dict)


class EDoreczeniaClient:
    """Klient API e-Doręczeń."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self._token: Optional[OAuth2Token] = None
        self._lock = asyncio.Lock()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self._client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._client:
            await self._client.aclose()

    async def _ensure_token(self) -> str:
        """Zapewnia ważny token OAuth2."""
        async with self._lock:
            if self._token is None or self._token.is_expired:
                await self._refresh_token()
            return self._token.access_token

    async def _refresh_token(self) -> None:
        """Odświeża token OAuth2."""
        logger.info("Odświeżanie tokenu OAuth2")

        data = {
            "grant_type": "client_credentials",
            "client_id": self.settings.edoreczenia_client_id,
            "client_secret": self.settings.edoreczenia_client_secret.get_secret_value(),
        }

        try:
            response = await self._client.post(self.settings.edoreczenia_token_url, data=data)
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

    async def _request(
        self,
        method: str,
        endpoint: str,
        **kwargs,
    ) -> dict[str, Any]:
        """Wykonuje żądanie do API."""
        token = await self._ensure_token()
        url = f"{self.settings.edoreczenia_api_base_url}/{endpoint}"

        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        headers["Accept"] = "application/json"

        try:
            response = await self._client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json() if response.content else {}

        except httpx.HTTPError as e:
            logger.error("Błąd API", method=method, endpoint=endpoint, error=str(e))
            raise

    async def get_messages(
        self,
        folder: str = "INBOX",
        limit: int = 50,
        offset: int = 0,
    ) -> list[Message]:
        """Pobiera listę wiadomości."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages"

        params = {
            "limit": limit,
            "offset": offset,
            "folder": self._map_folder_to_api(folder),
        }

        data = await self._request("GET", endpoint, params=params)
        messages = []

        for item in data.get("messages", []):
            msg = self._parse_message(item, folder)
            messages.append(msg)

        logger.info("Pobrano wiadomości", count=len(messages), folder=folder)
        return messages

    async def get_message(self, message_id: str) -> Message:
        """Pobiera szczegóły wiadomości."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}"

        data = await self._request("GET", endpoint)
        return self._parse_message(data, "INBOX")

    async def get_attachment(self, message_id: str, attachment_id: str) -> bytes:
        """Pobiera załącznik."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}/attachments/{attachment_id}"

        token = await self._ensure_token()
        url = f"{self.settings.edoreczenia_api_base_url}/{endpoint}"

        response = await self._client.get(
            url,
            headers={"Authorization": f"Bearer {token}"},
        )
        response.raise_for_status()
        return response.content

    async def send_message(
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
            "recipients": recipients,
            "subject": subject,
            "content": content,
            "attachments": attachments or [],
        }

        result = await self._request("POST", endpoint, json=message_data)
        logger.info("Wiadomość wysłana", message_id=result.get("messageId"))
        return result

    async def update_message_status(
        self,
        message_id: str,
        status: str,
    ) -> None:
        """Aktualizuje status wiadomości (np. przeczytana)."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/messages/{message_id}/status"

        await self._request("PUT", endpoint, json={"status": status})
        logger.info("Status wiadomości zaktualizowany", message_id=message_id, status=status)

    async def get_folders(self) -> list[dict[str, Any]]:
        """Pobiera listę folderów."""
        address = self.settings.edoreczenia_address
        endpoint = f"{address}/folders"

        data = await self._request("GET", endpoint)
        return data.get("folders", [])

    def _parse_message(self, data: dict[str, Any], folder: str) -> Message:
        """Parsuje dane wiadomości z API."""
        return Message(
            message_id=data.get("messageId", ""),
            subject=data.get("subject", "(brak tematu)"),
            sender=data.get("sender", {}).get("address", ""),
            recipients=[r.get("address", "") for r in data.get("recipients", [])],
            content=data.get("content", ""),
            attachments=data.get("attachments", []),
            received_at=datetime.fromisoformat(
                data.get("receivedAt", datetime.now().isoformat())
            ),
            status=data.get("status", "RECEIVED"),
            folder=folder,
            flags=self._map_status_to_flags(data.get("status", "")),
            raw_data=data,
        )

    def _map_folder_to_api(self, imap_folder: str) -> str:
        """Mapuje nazwę folderu IMAP na folder API."""
        mapping = {
            "INBOX": "inbox",
            "Sent": "sent",
            "Drafts": "drafts",
            "Trash": "trash",
            "Archive": "archive",
        }
        return mapping.get(imap_folder, "inbox")

    def _map_status_to_flags(self, status: str) -> list[str]:
        """Mapuje status e-Doręczeń na flagi IMAP."""
        flags = []
        if status in ("READ", "OPENED"):
            flags.append("\\Seen")
        if status == "REPLIED":
            flags.append("\\Answered")
        return flags
