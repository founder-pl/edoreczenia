#!/usr/bin/env python3
"""
IDCard.pl - Testy API
"""

import pytest
import requests
from typing import Dict, Any

# Configuration
BASE_URL = "http://localhost:4000"
TIMEOUT = 10
DEMO_EMAIL = "demo@idcard.pl"
DEMO_PASSWORD = "demo123"


class TestIDCardAPI:
    """Testy API IDCard.pl"""
    
    def test_health_check(self):
        """Test health endpoint"""
        response = requests.get(f"{BASE_URL}/health", timeout=TIMEOUT)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "IDCard.pl Integration Gateway"
    
    def test_login_demo_user(self):
        """Test logowania demo użytkownika"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "user" in data
        assert data["user"]["email"] == DEMO_EMAIL
    
    def test_login_invalid_credentials(self):
        """Test logowania z błędnymi danymi"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": "invalid@test.pl", "password": "wrong"},
            timeout=TIMEOUT
        )
        assert response.status_code in [401, 400]
    
    def test_register_new_user(self):
        """Test rejestracji nowego użytkownika"""
        import uuid
        test_email = f"test_{uuid.uuid4().hex[:8]}@test.pl"
        
        response = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={
                "email": test_email,
                "password": "Test123!",
                "name": "Test User"
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == test_email


class TestIDCardConnections:
    """Testy połączeń z usługami"""
    
    @pytest.fixture
    def auth_token(self) -> str:
        """Pobierz token autoryzacji"""
        response = requests.post(
            f"{BASE_URL}/api/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=TIMEOUT
        )
        return response.json().get("access_token", "")
    
    def test_get_connections(self, auth_token):
        """Test pobierania połączeń"""
        response = requests.get(
            f"{BASE_URL}/api/services/connections",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
    
    def test_connect_edoreczenia(self, auth_token):
        """Test połączenia z e-Doręczeniami"""
        response = requests.post(
            f"{BASE_URL}/api/services/connect",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "service_type": "edoreczenia",
                "credentials": {"ade_address": "AE:PL-TEST-001"},
                "config": {"auth_method": "oauth2"}
            },
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "connection_id" in data
    
    def test_get_unified_inbox(self, auth_token):
        """Test zunifikowanej skrzynki"""
        response = requests.get(
            f"{BASE_URL}/api/inbox",
            headers={"Authorization": f"Bearer {auth_token}"},
            timeout=TIMEOUT
        )
        assert response.status_code == 200
        data = response.json()
        assert "messages" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
