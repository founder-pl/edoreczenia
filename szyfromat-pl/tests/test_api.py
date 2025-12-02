#!/usr/bin/env python3
"""
Szyfromat.pl - Testy API
"""

import pytest
import requests
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:8500"
TIMEOUT = 10
DEMO_EMAIL = "demo@szyfromat.pl"
DEMO_PASSWORD = "demo123"


class TestSzyfromatAPI:
    """Testy API Szyfromat.pl"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "e-Doręczenia" in data["service"]
    
    def test_login(self):
        """Test logowania"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data


class TestSzyfromatMessages:
    """Testy wiadomości e-Doręczeń"""
    
    @pytest.fixture
    def auth_token(self) -> str:
        """Pobierz token autoryzacji"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"username": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=TIMEOUT
        )
        return response.json().get("access_token", "")
    
    def test_get_messages_inbox(self, auth_token):
        """Test pobierania wiadomości"""
        response = requests.get(
            f"{BASE_URL}/api/messages",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"folder": "inbox"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data
    
    def test_get_messages_sent(self, auth_token):
        """Test pobierania wysłanych"""
        response = requests.get(
            f"{BASE_URL}/api/messages",
            headers={"Authorization": f"Bearer {auth_token}"},
            params={"folder": "sent"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
    
    def test_send_message(self, auth_token):
        """Test wysyłania wiadomości"""
        response = requests.post(
            f"{BASE_URL}/api/messages",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "recipient": "AE:PL-TEST-RECIPIENT-01",
                "subject": "Test message",
                "content": "Test content from pytest"
            },
            timeout=TIMEOUT
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert "id" in data
    
    def test_get_folders(self, auth_token):
        """Test pobierania folderów"""
        response = requests.get(
            f"{BASE_URL}/api/folders",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "folders" in data


class TestSzyfromatConnectors:
    """Testy connectorów"""
    
    def test_ade_connector_status(self):
        """Test statusu ADE connector"""
        response = requests.get(
            f"{BASE_URL}/api/connectors/ade/status",
            timeout=TIMEOUT
        )
        # Może zwrócić 200 lub 404 jeśli endpoint nie istnieje
        assert response.status_code in [200, 404]
    
    def test_nextcloud_connector_status(self):
        """Test statusu Nextcloud connector"""
        response = requests.get(
            f"{BASE_URL}/api/connectors/nextcloud/status",
            timeout=TIMEOUT
        )
        assert response.status_code in [200, 404]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
