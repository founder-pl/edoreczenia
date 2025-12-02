"""
Testy dla e-Doręczenia Proxy IMAP/SMTP.
"""
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from edoreczenia_proxy.api_client import EDoreczeniaClient, Message, OAuth2Token
from edoreczenia_proxy.config import Settings


# ============================================
# Fixtures
# ============================================


@pytest.fixture
def settings():
    """Zwraca testowe ustawienia."""
    return Settings(
        edoreczenia_client_id="test_client_id",
        edoreczenia_client_secret="test_secret",
        edoreczenia_address="AE:PL-12345-67890-ABCDE-12",
        local_auth_password="test_password",
    )


@pytest.fixture
def mock_message():
    """Zwraca przykładową wiadomość."""
    return Message(
        message_id="msg-001",
        subject="Test message",
        sender="AE:PL-AAAAA-BBBBB-CCCCC-01",
        recipients=["AE:PL-DDDDD-EEEEE-FFFFF-02"],
        content="Test content",
        attachments=[],
        received_at=datetime.now(),
        status="RECEIVED",
        folder="INBOX",
        flags=[],
        raw_data={},
    )


# ============================================
# Testy OAuth2Token
# ============================================


class TestOAuth2Token:
    """Testy klasy OAuth2Token."""

    def test_token_not_expired(self):
        """Token nie powinien być wygasły zaraz po utworzeniu."""
        token = OAuth2Token(
            access_token="test_token",
            token_type="Bearer",
            expires_in=3600,
        )
        assert not token.is_expired

    def test_token_expired(self):
        """Token powinien być wygasły po upływie czasu."""
        token = OAuth2Token(
            access_token="test_token",
            token_type="Bearer",
            expires_in=0,  # Natychmiastowe wygaśnięcie
        )
        assert token.is_expired


# ============================================
# Testy EDoreczeniaClient
# ============================================


class TestEDoreczeniaClient:
    """Testy klienta API."""

    @pytest.mark.asyncio
    async def test_parse_message(self, settings):
        """Test parsowania wiadomości z API."""
        client = EDoreczeniaClient(settings)

        raw_data = {
            "messageId": "msg-123",
            "subject": "Testowa wiadomość",
            "sender": {"address": "AE:PL-11111-22222-33333-44"},
            "recipients": [{"address": "AE:PL-55555-66666-77777-88"}],
            "content": "Treść testowa",
            "attachments": [],
            "receivedAt": "2024-01-15T10:30:00",
            "status": "READ",
        }

        msg = client._parse_message(raw_data, "INBOX")

        assert msg.message_id == "msg-123"
        assert msg.subject == "Testowa wiadomość"
        assert msg.sender == "AE:PL-11111-22222-33333-44"
        assert len(msg.recipients) == 1
        assert msg.content == "Treść testowa"
        assert "\\Seen" in msg.flags

    def test_map_folder_to_api(self, settings):
        """Test mapowania folderów IMAP na API."""
        client = EDoreczeniaClient(settings)

        assert client._map_folder_to_api("INBOX") == "inbox"
        assert client._map_folder_to_api("Sent") == "sent"
        assert client._map_folder_to_api("Drafts") == "drafts"
        assert client._map_folder_to_api("Unknown") == "inbox"

    def test_map_status_to_flags(self, settings):
        """Test mapowania statusów na flagi IMAP."""
        client = EDoreczeniaClient(settings)

        assert "\\Seen" in client._map_status_to_flags("READ")
        assert "\\Seen" in client._map_status_to_flags("OPENED")
        assert "\\Answered" in client._map_status_to_flags("REPLIED")
        assert client._map_status_to_flags("RECEIVED") == []


# ============================================
# Testy Message
# ============================================


class TestMessage:
    """Testy klasy Message."""

    def test_message_creation(self, mock_message):
        """Test tworzenia wiadomości."""
        assert mock_message.message_id == "msg-001"
        assert mock_message.subject == "Test message"
        assert mock_message.folder == "INBOX"

    def test_message_flags_default(self, mock_message):
        """Flagi powinny być pustą listą domyślnie."""
        assert mock_message.flags == []


# ============================================
# Testy Settings
# ============================================


class TestSettings:
    """Testy konfiguracji."""

    def test_settings_defaults(self, settings):
        """Test domyślnych wartości ustawień."""
        assert settings.imap_port == 1143
        assert settings.smtp_port == 1025
        assert settings.log_level == "INFO"
        assert settings.cache_ttl_seconds == 300

    def test_settings_custom_values(self):
        """Test niestandardowych wartości."""
        settings = Settings(
            edoreczenia_client_id="custom_id",
            edoreczenia_client_secret="custom_secret",
            edoreczenia_address="AE:PL-99999-88888-77777-66",
            local_auth_password="custom_password",
            imap_port=9143,
            smtp_port=9025,
            log_level="DEBUG",
        )

        assert settings.imap_port == 9143
        assert settings.smtp_port == 9025
        assert settings.log_level == "DEBUG"


# ============================================
# Testy integracyjne (mock)
# ============================================


class TestIntegration:
    """Testy integracyjne z mockami."""

    @pytest.mark.asyncio
    async def test_client_context_manager(self, settings):
        """Test context managera klienta."""
        async with EDoreczeniaClient(settings) as client:
            assert client._client is not None

    @pytest.mark.asyncio
    async def test_get_messages_mock(self, settings, mock_message):
        """Test pobierania wiadomości z mockiem."""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            # Mock odpowiedzi tokenu
            mock_token_response = MagicMock()
            mock_token_response.json.return_value = {
                "access_token": "test_token",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
            mock_token_response.raise_for_status = MagicMock()

            # Mock odpowiedzi wiadomości
            mock_messages_response = MagicMock()
            mock_messages_response.json.return_value = {
                "messages": [
                    {
                        "messageId": "msg-001",
                        "subject": "Test",
                        "sender": {"address": "test@sender"},
                        "recipients": [],
                        "content": "Content",
                        "attachments": [],
                        "receivedAt": datetime.now().isoformat(),
                        "status": "RECEIVED",
                    }
                ]
            }
            mock_messages_response.raise_for_status = MagicMock()

            mock_client.post.return_value = mock_token_response
            mock_client.request.return_value = mock_messages_response

            client = EDoreczeniaClient(settings)
            client._client = mock_client

            messages = await client.get_messages()

            assert len(messages) == 1
            assert messages[0].message_id == "msg-001"


# ============================================
# Uruchomienie testów
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
