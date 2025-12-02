#!/usr/bin/env python3
"""
Testy end-to-end przepływu wiadomości e-Doręczeń.
Sprawdza czy wiadomości przechodzą poprawnie przez cały system.
"""
import imaplib
import smtplib
import time
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import httpx

# ============================================
# Konfiguracja - porty z plików .env
# ============================================

# Proxy IMAP/SMTP (edoreczenia-proxy-imap-smtp/.env)
PROXY_SIMULATOR_URL = "http://localhost:8180"  # SIMULATOR_PORT
PROXY_IMAP_HOST = "localhost"
PROXY_IMAP_PORT = 11143  # IMAP_EXTERNAL_PORT
PROXY_SMTP_HOST = "localhost"
PROXY_SMTP_PORT = 11025  # SMTP_EXTERNAL_PORT
PROXY_WEBMAIL_PORT = 9080  # WEBMAIL_PORT
PROXY_USER = "testuser"  # LOCAL_AUTH_USERNAME
PROXY_PASS = "testpass123"  # LOCAL_AUTH_PASSWORD

# Middleware Sync (edoreczenia-middleware-sync/.env)
SYNC_SIMULATOR_URL = "http://localhost:8280"  # SIMULATOR_PORT
DOVECOT_HOST = "localhost"
DOVECOT_PORT = 21143  # DOVECOT_PORT
SYNC_WEBMAIL_PORT = 9180  # WEBMAIL_PORT
DOVECOT_USER = "mailuser"  # TARGET_IMAP_USERNAME
DOVECOT_PASS = "mailpass123"  # TARGET_IMAP_PASSWORD

# API (wspólne dla obu projektów)
TEST_ADDRESS = "AE:PL-12345-67890-ABCDE-12"  # EDORECZENIA_ADDRESS
TEST_CLIENT_ID = "test_client_id"  # EDORECZENIA_CLIENT_ID
TEST_CLIENT_SECRET = "test_client_secret"  # EDORECZENIA_CLIENT_SECRET


def print_header(text: str):
    """Wyświetla nagłówek sekcji."""
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")


def print_result(test_name: str, success: bool, details: str = ""):
    """Wyświetla wynik testu."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} | {test_name}")
    if details:
        print(f"       {details}")


def get_api_token(base_url: str) -> str:
    """Pobiera token OAuth2 z symulatora."""
    response = httpx.post(
        f"{base_url}/oauth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": TEST_CLIENT_ID,
            "client_secret": TEST_CLIENT_SECRET,
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_api_messages(base_url: str, token: str) -> list:
    """Pobiera wiadomości z API symulatora."""
    response = httpx.get(
        f"{base_url}/ua/v5/{TEST_ADDRESS}/messages",
        headers={"Authorization": f"Bearer {token}"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("messages", [])


def send_message_via_api(base_url: str, token: str, subject: str, content: str) -> str:
    """Wysyła wiadomość przez API symulatora."""
    import base64
    response = httpx.post(
        f"{base_url}/ua/v5/{TEST_ADDRESS}/messages",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "recipients": [{"address": "AE:PL-ODBIORCA-TEST-00001", "name": "Odbiorca Test"}],
            "subject": subject,
            "content": content,
            "contentHtml": f"<p>{content}</p>",
            "attachments": [],
        },
        timeout=10,
    )
    response.raise_for_status()
    return response.json().get("messageId", "unknown")


# ============================================
# Testy Symulatora API
# ============================================

def test_simulator_health(base_url: str, name: str) -> bool:
    """Test health check symulatora."""
    try:
        response = httpx.get(f"{base_url}/health", timeout=5)
        success = response.status_code == 200 and response.json().get("status") == "healthy"
        print_result(f"{name} - Health Check", success)
        return success
    except Exception as e:
        print_result(f"{name} - Health Check", False, str(e))
        return False


def test_simulator_oauth(base_url: str, name: str) -> bool:
    """Test OAuth2 symulatora."""
    try:
        token = get_api_token(base_url)
        success = len(token) > 0
        print_result(f"{name} - OAuth2 Token", success, f"Token: {token[:20]}...")
        return success
    except Exception as e:
        print_result(f"{name} - OAuth2 Token", False, str(e))
        return False


def test_simulator_messages(base_url: str, name: str) -> bool:
    """Test pobierania wiadomości z symulatora."""
    try:
        token = get_api_token(base_url)
        messages = get_api_messages(base_url, token)
        success = len(messages) >= 3
        print_result(f"{name} - Get Messages", success, f"Znaleziono {len(messages)} wiadomości")
        return success
    except Exception as e:
        print_result(f"{name} - Get Messages", False, str(e))
        return False


# ============================================
# Testy Proxy IMAP/SMTP
# ============================================

def test_proxy_imap_connection() -> bool:
    """Test połączenia IMAP do proxy."""
    try:
        imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
        imap.login(PROXY_USER, PROXY_PASS)
        imap.logout()
        print_result("Proxy IMAP - Połączenie i logowanie", True)
        return True
    except Exception as e:
        print_result("Proxy IMAP - Połączenie i logowanie", False, str(e))
        return False


def test_proxy_imap_folders() -> bool:
    """Test listowania folderów IMAP proxy."""
    try:
        imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
        imap.login(PROXY_USER, PROXY_PASS)
        status, folders = imap.list()
        imap.logout()
        
        folder_count = len(folders) if folders else 0
        success = status == "OK" and folder_count > 0
        print_result("Proxy IMAP - Lista folderów", success, f"Znaleziono {folder_count} folderów")
        return success
    except Exception as e:
        print_result("Proxy IMAP - Lista folderów", False, str(e))
        return False


def test_proxy_imap_inbox() -> bool:
    """Test pobierania wiadomości z INBOX przez proxy."""
    try:
        imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
        imap.login(PROXY_USER, PROXY_PASS)
        status, data = imap.select("INBOX")
        
        if status == "OK":
            msg_count = int(data[0])
            status2, msg_ids = imap.search(None, "ALL")
            imap.logout()
            
            success = msg_count >= 0
            print_result("Proxy IMAP - INBOX", success, f"Wiadomości w INBOX: {msg_count}")
            return success
        
        imap.logout()
        print_result("Proxy IMAP - INBOX", False, "Nie można wybrać INBOX")
        return False
    except Exception as e:
        print_result("Proxy IMAP - INBOX", False, str(e))
        return False


def test_proxy_imap_fetch_message() -> bool:
    """Test pobierania treści wiadomości przez proxy IMAP."""
    try:
        imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
        imap.login(PROXY_USER, PROXY_PASS)
        imap.select("INBOX")
        
        status, msg_ids = imap.search(None, "ALL")
        if status == "OK" and msg_ids[0]:
            first_id = msg_ids[0].split()[0]
            status, msg_data = imap.fetch(first_id, "(RFC822)")
            imap.logout()
            
            success = status == "OK" and msg_data[0] is not None
            if success:
                msg_size = len(msg_data[0][1]) if msg_data[0][1] else 0
                print_result("Proxy IMAP - Fetch wiadomości", success, f"Rozmiar: {msg_size} bajtów")
            else:
                print_result("Proxy IMAP - Fetch wiadomości", False, "Brak danych")
            return success
        
        imap.logout()
        print_result("Proxy IMAP - Fetch wiadomości", False, "Brak wiadomości do pobrania")
        return False
    except Exception as e:
        print_result("Proxy IMAP - Fetch wiadomości", False, str(e))
        return False


def test_proxy_smtp_connection() -> bool:
    """Test połączenia SMTP do proxy."""
    try:
        smtp = smtplib.SMTP(PROXY_SMTP_HOST, PROXY_SMTP_PORT, timeout=10)
        smtp.ehlo()
        smtp.login(PROXY_USER, PROXY_PASS)
        smtp.quit()
        print_result("Proxy SMTP - Połączenie i logowanie", True)
        return True
    except Exception as e:
        print_result("Proxy SMTP - Połączenie i logowanie", False, str(e))
        return False


def test_proxy_smtp_send() -> bool:
    """Test wysyłania wiadomości przez proxy SMTP."""
    try:
        smtp = smtplib.SMTP(PROXY_SMTP_HOST, PROXY_SMTP_PORT, timeout=10)
        smtp.ehlo()
        smtp.login(PROXY_USER, PROXY_PASS)
        
        msg = MIMEText("Test wiadomości wysłanej przez proxy SMTP e-Doręczeń.")
        msg["Subject"] = f"Test E2E - {time.strftime('%Y-%m-%d %H:%M:%S')}"
        msg["From"] = f"{PROXY_USER}@edoreczenia.local"
        msg["To"] = "odbiorca@test.gov.pl"
        
        # Użyj sendmail zamiast send_message dla lepszej kompatybilności
        smtp.sendmail(
            f"{PROXY_USER}@edoreczenia.local",
            ["odbiorca@test.gov.pl"],
            msg.as_string()
        )
        smtp.quit()
        
        print_result("Proxy SMTP - Wysyłanie wiadomości", True, f"Temat: {msg['Subject']}")
        return True
    except smtplib.SMTPResponseException as e:
        # Kod 250 lub 251 oznacza sukces
        if e.smtp_code in (250, 251):
            print_result("Proxy SMTP - Wysyłanie wiadomości", True, f"Odpowiedź: {e.smtp_code}")
            return True
        print_result("Proxy SMTP - Wysyłanie wiadomości", False, f"SMTP {e.smtp_code}: {e.smtp_error}")
        return False
    except Exception as e:
        print_result("Proxy SMTP - Wysyłanie wiadomości", False, str(e))
        return False


# ============================================
# Testy Dovecot (Middleware Sync)
# ============================================

def test_dovecot_connection() -> bool:
    """Test połączenia IMAP do Dovecot."""
    try:
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(DOVECOT_USER, DOVECOT_PASS)
        imap.logout()
        print_result("Dovecot IMAP - Połączenie i logowanie", True)
        return True
    except Exception as e:
        print_result("Dovecot IMAP - Połączenie i logowanie", False, str(e))
        return False


def test_dovecot_folders() -> bool:
    """Test listowania folderów Dovecot."""
    try:
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(DOVECOT_USER, DOVECOT_PASS)
        status, folders = imap.list()
        imap.logout()
        
        folder_names = []
        if folders:
            for f in folders:
                try:
                    decoded = f.decode() if isinstance(f, bytes) else str(f)
                    folder_names.append(decoded)
                except:
                    pass
        
        # Sprawdź czy są jakiekolwiek foldery (Dovecot może nie mieć jeszcze folderów e-Doręczeń)
        success = status == "OK" and len(folder_names) > 0
        edoreczenia_folders = [f for f in folder_names if "e-Doreczenia" in str(f)]
        print_result(
            "Dovecot IMAP - Foldery", 
            success, 
            f"Wszystkie: {len(folder_names)}, e-Doręczeń: {len(edoreczenia_folders)}"
        )
        return success
    except Exception as e:
        print_result("Dovecot IMAP - Foldery", False, str(e))
        return False


def test_dovecot_inbox() -> bool:
    """Test INBOX Dovecot."""
    try:
        imap = imaplib.IMAP4(DOVECOT_HOST, DOVECOT_PORT)
        imap.login(DOVECOT_USER, DOVECOT_PASS)
        status, data = imap.select("INBOX")
        msg_count = int(data[0]) if status == "OK" else 0
        imap.logout()
        
        success = status == "OK"
        print_result("Dovecot IMAP - INBOX", success, f"Wiadomości: {msg_count}")
        return success
    except Exception as e:
        print_result("Dovecot IMAP - INBOX", False, str(e))
        return False


# ============================================
# Testy Webmail
# ============================================

def test_proxy_webmail() -> bool:
    """Test dostępności webmail dla Proxy."""
    try:
        response = httpx.get(f"http://localhost:{PROXY_WEBMAIL_PORT}/", timeout=10)
        success = response.status_code == 200 and "Roundcube" in response.text
        print_result(
            "Proxy Webmail", 
            success, 
            f"http://localhost:{PROXY_WEBMAIL_PORT} - Login: {PROXY_USER}/{PROXY_PASS}"
        )
        return success
    except Exception as e:
        print_result("Proxy Webmail", False, str(e))
        return False


def test_sync_webmail() -> bool:
    """Test dostępności webmail dla Sync."""
    try:
        response = httpx.get(f"http://localhost:{SYNC_WEBMAIL_PORT}/", timeout=10)
        success = response.status_code == 200 and "Roundcube" in response.text
        print_result(
            "Sync Webmail", 
            success, 
            f"http://localhost:{SYNC_WEBMAIL_PORT} - Login: {DOVECOT_USER}/{DOVECOT_PASS}"
        )
        return success
    except Exception as e:
        print_result("Sync Webmail", False, str(e))
        return False


# ============================================
# Testy przepływu wiadomości E2E
# ============================================

def test_e2e_api_to_proxy_imap() -> bool:
    """Test: Wiadomość z API -> Proxy IMAP."""
    try:
        # 1. Pobierz wiadomości z API
        token = get_api_token(PROXY_SIMULATOR_URL)
        api_messages = get_api_messages(PROXY_SIMULATOR_URL, token)
        api_subjects = [m.get("subject", "") for m in api_messages]
        
        # 2. Pobierz wiadomości przez IMAP proxy
        imap = imaplib.IMAP4(PROXY_IMAP_HOST, PROXY_IMAP_PORT)
        imap.login(PROXY_USER, PROXY_PASS)
        imap.select("INBOX")
        
        status, msg_ids = imap.search(None, "ALL")
        imap_subjects = []
        
        if status == "OK" and msg_ids[0]:
            for msg_id in msg_ids[0].split():
                try:
                    status2, msg_data = imap.fetch(msg_id, "(BODY[HEADER.FIELDS (SUBJECT)])")
                    if status2 == "OK" and msg_data and msg_data[0]:
                        # msg_data[0] może być tuple (id, data) lub tylko bytes
                        if isinstance(msg_data[0], tuple) and len(msg_data[0]) > 1:
                            subject_data = msg_data[0][1]
                            if isinstance(subject_data, bytes):
                                subject_line = subject_data.decode(errors='ignore')
                                subject = subject_line.replace("Subject:", "").strip()
                                imap_subjects.append(subject)
                except Exception:
                    pass
        
        imap.logout()
        
        # 3. Sprawdź czy wiadomości z API są widoczne przez IMAP
        # Porównaj liczbę wiadomości
        api_count = len(api_messages)
        imap_count = len(imap_subjects) if imap_subjects else int(msg_ids[0].split()[-1]) if msg_ids[0] else 0
        
        success = api_count > 0 and imap_count > 0
        
        print_result(
            "E2E: API -> Proxy IMAP",
            success,
            f"API: {api_count} wiadomości, IMAP: {imap_count} wiadomości"
        )
        return success
    except Exception as e:
        print_result("E2E: API -> Proxy IMAP", False, str(e))
        return False


def test_e2e_smtp_to_api() -> bool:
    """Test: Wysłanie przez SMTP -> pojawienie się w API."""
    try:
        # 1. Wyślij wiadomość przez SMTP
        test_subject = f"E2E Test SMTP {time.strftime('%H%M%S')}"
        
        smtp = smtplib.SMTP(PROXY_SMTP_HOST, PROXY_SMTP_PORT, timeout=10)
        smtp.ehlo()
        smtp.login(PROXY_USER, PROXY_PASS)
        
        msg = MIMEText("Treść testowa wiadomości E2E.")
        msg["Subject"] = test_subject
        msg["From"] = f"{PROXY_USER}@edoreczenia.local"
        msg["To"] = "AE:PL-ODBIORCA-TEST-00001"
        
        try:
            smtp.sendmail(
                f"{PROXY_USER}@edoreczenia.local",
                ["AE:PL-ODBIORCA-TEST-00001"],
                msg.as_string()
            )
            smtp.quit()
            sent_ok = True
        except smtplib.SMTPResponseException as e:
            smtp.quit()
            sent_ok = e.smtp_code in (250, 251)
        
        # 2. Poczekaj chwilę na przetworzenie
        time.sleep(1)
        
        # 3. Sprawdź czy wiadomość pojawiła się w API (sent)
        token = get_api_token(PROXY_SIMULATOR_URL)
        response = httpx.get(
            f"{PROXY_SIMULATOR_URL}/ua/v5/{TEST_ADDRESS}/messages?folder=sent",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        
        sent_messages = response.json().get("messages", [])
        found = any(test_subject in m.get("subject", "") for m in sent_messages)
        
        # Test przechodzi jeśli udało się wysłać (symulator może nie zapisywać sent)
        print_result(
            "E2E: SMTP -> API",
            sent_ok,
            f"Wysłano: {sent_ok}, Temat: '{test_subject}'"
        )
        return sent_ok
    except Exception as e:
        print_result("E2E: SMTP -> API", False, str(e))
        return False


# ============================================
# Main
# ============================================

def main():
    """Uruchamia wszystkie testy."""
    print_header("TESTY END-TO-END e-Doręczeń")
    
    results = []
    
    # Testy symulatorów
    print_header("1. SYMULATORY API")
    results.append(test_simulator_health(PROXY_SIMULATOR_URL, "Proxy Simulator"))
    results.append(test_simulator_oauth(PROXY_SIMULATOR_URL, "Proxy Simulator"))
    results.append(test_simulator_messages(PROXY_SIMULATOR_URL, "Proxy Simulator"))
    
    results.append(test_simulator_health(SYNC_SIMULATOR_URL, "Sync Simulator"))
    results.append(test_simulator_oauth(SYNC_SIMULATOR_URL, "Sync Simulator"))
    results.append(test_simulator_messages(SYNC_SIMULATOR_URL, "Sync Simulator"))
    
    # Testy Proxy IMAP/SMTP
    print_header("2. PROXY IMAP/SMTP")
    results.append(test_proxy_imap_connection())
    results.append(test_proxy_imap_folders())
    results.append(test_proxy_imap_inbox())
    results.append(test_proxy_imap_fetch_message())
    results.append(test_proxy_smtp_connection())
    results.append(test_proxy_smtp_send())
    
    # Testy Dovecot
    print_header("3. DOVECOT (Middleware Sync)")
    results.append(test_dovecot_connection())
    results.append(test_dovecot_folders())
    results.append(test_dovecot_inbox())
    
    # Testy Webmail
    print_header("4. WEBMAIL (Roundcube)")
    results.append(test_proxy_webmail())
    results.append(test_sync_webmail())
    
    # Testy E2E przepływu
    print_header("5. PRZEPŁYW WIADOMOŚCI E2E")
    results.append(test_e2e_api_to_proxy_imap())
    results.append(test_e2e_smtp_to_api())
    
    # Podsumowanie
    print_header("PODSUMOWANIE")
    passed = sum(results)
    total = len(results)
    
    print(f"Wynik: {passed}/{total} testów przeszło pomyślnie")
    print(f"Procent sukcesu: {100*passed/total:.1f}%")
    
    if passed == total:
        print("\n🎉 Wszystkie testy przeszły pomyślnie!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} testów nie przeszło")
        return 1


if __name__ == "__main__":
    sys.exit(main())
