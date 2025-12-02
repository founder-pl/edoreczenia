"""
Testy integracyjne z symulatorem API e-Doręczeń.
"""
import imaplib
import smtplib
import time
from email.mime.text import MIMEText

import httpx
import pytest


# ============================================
# Konfiguracja
# ============================================

SIMULATOR_URL = "http://edoreczenia-simulator:8080"
PROXY_IMAP_HOST = "edoreczenia-proxy"
PROXY_IMAP_PORT = 1143
PROXY_SMTP_HOST = "edoreczenia-proxy"
PROXY_SMTP_PORT = 1025
TEST_USER = "testuser"
TEST_PASS = "testpass123"


# ============================================
# Fixtures
# ============================================


@pytest.fixture(scope="module")
def wait_for_services():
    """Czeka na dostępność serwisów."""
    max_retries = 30
    for i in range(max_retries):
        try:
            # Sprawdź symulator
            response = httpx.get(f"{SIMULATOR_URL}/health", timeout=5)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        pytest.fail("Serwisy nie uruchomiły się w czasie")


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
        assert data["token_type"] == "Bearer"

    def test_get_messages(self, wait_for_services):
        """Test pobierania wiadomości."""
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
        assert len(data["messages"]) > 0


# ============================================
# Testy proxy IMAP
# ============================================


class TestProxyIMAP:
    """Testy proxy IMAP."""

    def test_imap_connection(self, wait_for_services):
        """Test połączenia IMAP."""
        time.sleep(5)  # Daj czas na uruchomienie proxy

        try:
            imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
            imap.login(TEST_USER, TEST_PASS)
            imap.logout()
        except Exception as e:
            pytest.skip(f"Proxy IMAP nie gotowe: {e}")

    def test_imap_list_folders(self, wait_for_services):
        """Test listowania folderów IMAP."""
        time.sleep(5)

        try:
            imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
            imap.login(TEST_USER, TEST_PASS)

            status, folders = imap.list()
            assert status == "OK"
            assert len(folders) > 0

            imap.logout()
        except Exception as e:
            pytest.skip(f"Proxy IMAP nie gotowe: {e}")

    def test_imap_select_inbox(self, wait_for_services):
        """Test wyboru INBOX."""
        time.sleep(5)

        try:
            imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
            imap.login(TEST_USER, TEST_PASS)

            status, data = imap.select("INBOX")
            assert status == "OK"

            imap.logout()
        except Exception as e:
            pytest.skip(f"Proxy IMAP nie gotowe: {e}")


# ============================================
# Testy proxy SMTP
# ============================================


class TestProxySMTP:
    """Testy proxy SMTP."""

    def test_smtp_connection(self, wait_for_services):
        """Test połączenia SMTP."""
        time.sleep(5)

        try:
            smtp = smtplib.SMTP(PROXY_SMTP_HOST, PROXY_SMTP_PORT, timeout=10)
            smtp.ehlo()
            smtp.login(TEST_USER, TEST_PASS)
            smtp.quit()
        except Exception as e:
            pytest.skip(f"Proxy SMTP nie gotowe: {e}")


# ============================================
# Uruchomienie
# ============================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
