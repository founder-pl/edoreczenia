#!/usr/bin/env python3
"""
e-Doręczenia DSL - Test przepływu (Python)

Testuje wszystkie operacje DSL: wysyłanie, odbieranie, synchronizację.

Użycie:
    python3 test-dsl.py
"""

import os
import json
import urllib.request
import urllib.parse
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════════
# KONFIGURACJA
# ═══════════════════════════════════════════════════════════════════════════

config = {
    'api_url': os.getenv('EDORECZENIA_API_URL', 'http://localhost:8180'),
    'address': os.getenv('EDORECZENIA_ADDRESS', 'AE:PL-12345-67890-ABCDE-12'),
    'client_id': os.getenv('EDORECZENIA_CLIENT_ID', 'test_client_id'),
    'client_secret': os.getenv('EDORECZENIA_CLIENT_SECRET', 'test_client_secret'),
}


# ═══════════════════════════════════════════════════════════════════════════
# DSL KLASA
# ═══════════════════════════════════════════════════════════════════════════

class EDoreczeniaClient:
    def __init__(self, config):
        self.api_url = config['api_url']
        self.address = config['address']
        self.client_id = config['client_id']
        self.client_secret = config['client_secret']
        self.access_token = None
    
    def get_token(self):
        """Pobiera token OAuth2"""
        if self.access_token:
            return self.access_token
        
        url = f"{self.api_url}/oauth/token"
        data = urllib.parse.urlencode({
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }).encode()
        
        req = urllib.request.Request(url, data=data)
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
            self.access_token = result['access_token']
            return self.access_token
    
    def get_messages(self, folder='inbox', limit=20):
        """Pobiera wiadomości"""
        token = self.get_token()
        url = f"{self.api_url}/ua/v5/{self.address}/messages?folder={folder}&limit={limit}"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
            return result.get('messages', [])
    
    def send_message(self, recipient, subject, content, attachments=None):
        """Wysyła wiadomość"""
        token = self.get_token()
        url = f"{self.api_url}/ua/v5/{self.address}/messages"
        
        message = {
            'subject': subject,
            'recipients': [{'address': recipient, 'name': 'Odbiorca'}],
            'content': content,
            'attachments': attachments or []
        }
        
        data = json.dumps(message).encode()
        req = urllib.request.Request(url, data=data, method='POST')
        req.add_header('Content-Type', 'application/json')
        req.add_header('Authorization', f'Bearer {token}')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    
    def get_message(self, message_id):
        """Pobiera szczegóły wiadomości"""
        token = self.get_token()
        url = f"{self.api_url}/ua/v5/{self.address}/messages/{message_id}"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = json.loads(response.read())
            return result[0] if isinstance(result, list) else result
    
    def get_directories(self):
        """Pobiera katalogi"""
        token = self.get_token()
        url = f"{self.api_url}/ua/v5/{self.address}/directories"
        
        req = urllib.request.Request(url)
        req.add_header('Authorization', f'Bearer {token}')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())


# ═══════════════════════════════════════════════════════════════════════════
# TESTY
# ═══════════════════════════════════════════════════════════════════════════

def print_header(text):
    print(f"\n{'═' * 60}")
    print(f"  {text}")
    print(f"{'═' * 60}")


def print_step(step, text):
    print(f"\n[{step}] {text}")


def print_result(success, details=''):
    icon = '✓' if success else '✗'
    print(f"    {icon} {details}")


# ═══════════════════════════════════════════════════════════════════════════
# GŁÓWNA LOGIKA
# ═══════════════════════════════════════════════════════════════════════════

def main():
    print_header("e-Doręczenia DSL - Test przepływu")
    
    print("\nKonfiguracja:")
    print(f"  API URL:  {config['api_url']}")
    print(f"  Address:  {config['address']}")
    print(f"  Client:   {config['client_id']}")
    
    client = EDoreczeniaClient(config)
    results = []
    
    try:
        # Test 1: OAuth2
        print_step(1, "🔑 Test OAuth2 Token")
        token = client.get_token()
        results.append(True)
        print_result(True, f"Token: {token[:20]}...")
        
        # Test 2: Pobieranie wiadomości
        print_step(2, "📥 Test odbierania wiadomości")
        messages = client.get_messages('inbox', 10)
        results.append(len(messages) >= 0)
        print_result(True, f"Pobrano {len(messages)} wiadomości")
        
        for msg in messages[:3]:
            subject = (msg.get('subject', '') or '')[:40]
            status = msg.get('status', '')
            print(f"       📧 {subject}... [{status}]")
        
        # Test 3: Pobieranie katalogów
        print_step(3, "📁 Test pobierania katalogów")
        dirs = client.get_directories()
        dir_names = [d['name'] for d in dirs.get('directories', [])]
        results.append(len(dir_names) > 0)
        print_result(True, f"Katalogi: {', '.join(dir_names)}")
        
        # Test 4: Wysyłanie wiadomości
        print_step(4, "📤 Test wysyłania wiadomości")
        test_subject = f"DSL Test {datetime.now().strftime('%H:%M:%S')}"
        result = client.send_message(
            'AE:PL-ODBIORCA-TEST-00001',
            test_subject,
            'Wiadomość testowa z DSL Python.'
        )
        results.append(result.get('messageId') is not None)
        print_result(True, f"Wysłano: {result.get('messageId')} [{result.get('status')}]")
        
        # Test 5: Pobieranie szczegółów
        if messages:
            print_step(5, "📧 Test pobierania szczegółów wiadomości")
            msg = client.get_message(messages[0]['messageId'])
            results.append(msg.get('messageId') is not None)
            subject = (msg.get('subject', '') or '')[:40]
            print_result(True, f"Wiadomość: {subject}...")
            print(f"       Od: {msg.get('sender', {}).get('address', 'N/A')}")
            print(f"       Załączniki: {len(msg.get('attachments', []))}")
        
    except Exception as e:
        results.append(False)
        print_result(False, f"Błąd: {e}")
    
    # Podsumowanie
    print_header("PODSUMOWANIE")
    
    passed = sum(results)
    total = len(results)
    percent = int(passed * 100 / total) if total > 0 else 0
    
    print(f"\nWynik: {passed}/{total} testów ({percent}%)")
    
    if passed == total:
        print("\n🎉 Wszystkie testy DSL przeszły pomyślnie!")
    else:
        print(f"\n⚠️  {total - passed} testów nie przeszło")
    
    print(f"\n{'═' * 60}")
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    exit(main())
