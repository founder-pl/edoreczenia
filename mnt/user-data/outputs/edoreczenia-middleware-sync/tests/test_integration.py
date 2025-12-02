"""
Testy integracyjne middleware z symulatorem i Dovecot.
"""
import imaplib
import time

import httpx
import pytest


# ============================================
# Konfiguracja
# ============================================

SIMULATOR_URL = "http://edoreczenia-simulator:8080"
DOVECOT_HOST = "dovecot"
DOVECOT_PORT = 143
MAIL_USER = "mailuser"
MAIL_PASS = "mailpass123"


# ============================================
# Fixtures
# ============================================


@pytest.fixture(scope="module")
def wait_for_services():
    """Czeka na dostępność serwisów."""
    max_retries = 30

    # Czekaj na symulator
    for i in range(max_retries):
        try:
            response = httpx.get(f"{SIMULATOR_URL}/health", timeout=5)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail("Symulator nie uruchomił się w czasie")

    # Czekaj na Dovecot
    for i in range(max_retries):
        try:
            imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
            imap.logout()
            break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail("Dovecot nie uruchomił się w czasie")


# ============================================
# Testy symulatora
# ============================================


class TestSimulator:
    """Testy symulatora API."""

    def test_health_check(self, wait_for_services):
        """Test health check symulatora."""
        response = httpx.get(f"{SIMULATOR_URL}/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_get_token(self, wait_for_services):
        """Test pobierania tokenu OAuth2."""
        response = httpx.post(
            f"{SIMULATOR_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_get_messages(self, wait_for_services):
        """Test pobierania wiadomości z symulatora."""
        # Pobierz token
        token_response = httpx.post(
            f"{SIMULATOR_URL}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": "test_client_id",
                "client_secret": "test_client_secret",
            },
        )
        token = token_response.json()["access_token"]

        # Pobierz wiadomości
        response = httpx.get(
            f"{SIMULATOR_URL}/ua/v5/AE:PL-12345-67890-ABCDE-12/messages",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
        assert len(data["messages"]) >= 3  # Mamy 3 przykładowe wiadomości


# ============================================
# Testy Dovecot
# ============================================


class TestDovecot:
    """Testy serwera Dovecot."""

    def test_imap_connection(self, wait_for_services):
        """Test połączenia IMAP."""
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(MAIL_USER, MAIL_PASS)
        imap.logout()

    def test_imap_list_folders(self, wait_for_services):
        """Test listowania folderów."""
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(MAIL_USER, MAIL_PASS)

        status, folders = imap.list()
        assert status == "OK"

        imap.logout()

    def test_imap_select_inbox(self, wait_for_services):
        """Test wyboru INBOX."""
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(MAIL_USER, MAIL_PASS)

        status, data = imap.select("INBOX")
        assert status == "OK"

        imap.logout()

    def test_edoreczenia_folders_exist(self, wait_for_services):
        """Test czy foldery e-Doręczeń istnieją."""
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(MAIL_USER, MAIL_PASS)

        status, folders = imap.list()
        folder_names = [f.decode() for f in folders]

        # Sprawdź czy są foldery e-Doręczeń
        edoreczenia_folders = [f for f in folder_names if "e-Doreczenia" in f]
        assert len(edoreczenia_folders) > 0, "Brak folderów e-Doręczeń"

        imap.logout()


# ============================================
# Testy integracji sync
# ============================================


class TestSyncIntegration:
    """Testy integracji synchronizacji."""

    def test_sync_engine_creation(self, wait_for_services):
        """Test tworzenia silnika synchronizacji."""
        from edoreczenia_sync.config import get_settings
        from edoreczenia_sync.sync_engine import SyncEngine

        settings = get_settings()
        engine = SyncEngine(settings)
        assert engine is not None

    def test_api_client_connection(self, wait_for_services):
        """Test połączenia klienta API."""
        from edoreczenia_sync.api_client import EDoreczeniaClient
        from edoreczenia_sync.config import get_settings

        settings = get_settings()

        with EDoreczeniaClient(settings) as client:
            messages = client.get_messages()
            assert len(messages) >= 3

    def test_imap_client_connection(self, wait_for_services):
        """Test połączenia klienta IMAP."""
        from edoreczenia_sync.config import get_settings
        from edoreczenia_sync.imap_client import IMAPMailbox

        settings = get_settings()

        with IMAPMailbox(settings) as imap:
            folders = imap.list_folders()
            assert len(folders) > 0


# ============================================
# Uruchomienie
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
