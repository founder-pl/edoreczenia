"""
Testy dla e-Doręczenia Middleware Sync.
"""
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from edoreczenia_sync.api_client import EDoreczeniaClient, EDoreczeniaMessage, OAuth2Token
from edoreczenia_sync.config import Settings, SyncDirection
from edoreczenia_sync.models import Database, SyncDirection as ModelSyncDirection, SyncStatus


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
        target_imap_host="localhost",
        target_imap_username="test@example.com",
        target_imap_password="test_password",
        target_smtp_host="localhost",
        target_smtp_username="test@example.com",
        target_smtp_password="test_password",
        database_url="sqlite:///:memory:",
    )


@pytest.fixture
def mock_message():
    """Zwraca przykładową wiadomość e-Doręczeń."""
    return EDoreczeniaMessage(
        message_id="msg-001",
        subject="Test message",
        sender="AE:PL-AAAAA-BBBBB-CCCCC-01",
        recipients=["AE:PL-DDDDD-EEEEE-FFFFF-02"],
        content="Test content",
        content_html="<p>Test content</p>",
        attachments=[],
        received_at=datetime.now(),
        status="RECEIVED",
        epo=None,
        raw_data={},
    )


@pytest.fixture
def database(settings):
    """Zwraca instancję bazy danych w pamięci."""
    db = Database(settings.database_url)
    db.create_tables()
    return db


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
            expires_in=0,
        )
        assert token.is_expired


# ============================================
# Testy EDoreczeniaMessage
# ============================================


class TestEDoreczeniaMessage:
    """Testy klasy EDoreczeniaMessage."""

    def test_has_attachments_false(self, mock_message):
        """Test gdy brak załączników."""
        assert mock_message.has_attachments is False

    def test_has_attachments_true(self, mock_message):
        """Test gdy są załączniki."""
        mock_message.attachments = [{"attachmentId": "att-1"}]
        assert mock_message.has_attachments is True

    def test_is_read_false(self, mock_message):
        """Test nieprzeczytanej wiadomości."""
        assert mock_message.is_read is False

    def test_is_read_true(self, mock_message):
        """Test przeczytanej wiadomości."""
        mock_message.status = "READ"
        assert mock_message.is_read is True


# ============================================
# Testy Settings
# ============================================


class TestSettings:
    """Testy konfiguracji."""

    def test_settings_defaults(self, settings):
        """Test domyślnych wartości."""
        assert settings.sync_interval_minutes == 5
        assert settings.sync_batch_size == 50
        assert settings.sync_direction == SyncDirection.BIDIRECTIONAL
        assert settings.log_level == "INFO"

    def test_settings_folder_mapping(self, settings):
        """Test mapowania folderów."""
        assert "e-Doreczenia" in settings.folder_mapping_inbox
        assert "e-Doreczenia" in settings.folder_mapping_sent


# ============================================
# Testy Database
# ============================================


class TestDatabase:
    """Testy bazy danych."""

    def test_create_tables(self, database):
        """Test tworzenia tabel."""
        # Tabele powinny być już utworzone przez fixture
        session = database.get_session()
        # Sprawdź czy można wykonać zapytanie
        result = database.is_message_synced(session, edoreczenia_id="nonexistent")
        assert result is False
        session.close()

    def test_add_synced_message(self, database):
        """Test dodawania zsynchronizowanej wiadomości."""
        session = database.get_session()

        msg = database.add_synced_message(
            session,
            edoreczenia_id="msg-test-001",
            imap_uid=100,
            direction=ModelSyncDirection.INCOMING,
            status=SyncStatus.SYNCED,
            subject="Test subject",
            sender="sender@test.com",
        )

        assert msg.id is not None
        assert msg.edoreczenia_id == "msg-test-001"
        assert msg.status == SyncStatus.SYNCED

        session.close()

    def test_is_message_synced(self, database):
        """Test sprawdzania czy wiadomość jest zsynchronizowana."""
        session = database.get_session()

        # Dodaj wiadomość
        database.add_synced_message(
            session,
            edoreczenia_id="msg-synced",
            imap_uid=101,
            direction=ModelSyncDirection.INCOMING,
            status=SyncStatus.SYNCED,
        )

        # Sprawdź
        assert database.is_message_synced(session, edoreczenia_id="msg-synced") is True
        assert database.is_message_synced(session, edoreczenia_id="msg-not-exists") is False

        session.close()

    def test_sync_run(self, database):
        """Test śledzenia uruchomień synchronizacji."""
        session = database.get_session()

        # Rozpocznij synchronizację
        run = database.start_sync_run(session)
        assert run.status == "running"

        # Zakończ synchronizację
        run.messages_incoming = 5
        run.messages_outgoing = 3
        database.finish_sync_run(session, run, status="completed")

        assert run.status == "completed"
        assert run.finished_at is not None
        assert run.total_processed == 8

        session.close()

    def test_get_last_sync_run(self, database):
        """Test pobierania ostatniego uruchomienia."""
        session = database.get_session()

        # Brak uruchomień
        assert database.get_last_sync_run(session) is None

        # Dodaj uruchomienie
        run = database.start_sync_run(session)
        database.finish_sync_run(session, run)

        last = database.get_last_sync_run(session)
        assert last is not None
        assert last.id == run.id

        session.close()


# ============================================
# Testy EDoreczeniaClient
# ============================================


class TestEDoreczeniaClient:
    """Testy klienta API."""

    def test_parse_message(self, settings):
        """Test parsowania wiadomości z API."""
        client = EDoreczeniaClient(settings)

        raw_data = {
            "messageId": "msg-123",
            "subject": "Testowa wiadomość",
            "sender": {"address": "AE:PL-11111-22222-33333-44"},
            "recipients": [{"address": "AE:PL-55555-66666-77777-88"}],
            "content": "Treść testowa",
            "contentHtml": "<p>Treść testowa</p>",
            "attachments": [],
            "receivedAt": "2024-01-15T10:30:00",
            "status": "READ",
            "epo": None,
        }

        msg = client._parse_message(raw_data)

        assert msg.message_id == "msg-123"
        assert msg.subject == "Testowa wiadomość"
        assert msg.sender == "AE:PL-11111-22222-33333-44"
        assert len(msg.recipients) == 1
        assert msg.content == "Treść testowa"
        assert msg.is_read is True


# ============================================
# Testy integracyjne (mock)
# ============================================


class TestIntegration:
    """Testy integracyjne z mockami."""

    def test_sync_engine_initialization(self, settings):
        """Test inicjalizacji silnika synchronizacji."""
        from edoreczenia_sync.sync_engine import SyncEngine

        engine = SyncEngine(settings)
        assert engine.settings == settings
        assert engine.db is not None

    def test_application_initialization(self, settings):
        """Test inicjalizacji aplikacji."""
        from edoreczenia_sync.main import Application

        app = Application(settings)
        assert app.settings == settings
        assert app.sync_engine is not None

    def test_get_status(self, settings):
        """Test pobierania statusu."""
        from edoreczenia_sync.main import Application

        app = Application(settings)
        status = app.get_status()

        assert "running" in status
        assert "sync_interval_minutes" in status
        assert "edoreczenia_address" in status
        assert status["sync_direction"] == "bidirectional"


# ============================================
# Uruchomienie testów
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
