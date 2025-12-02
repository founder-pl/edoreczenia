#!/usr/bin/env python3
"""
Szyfromat.pl CLI - Command Line Interface
Zarządzaj wiadomościami e-Doręczeń z poziomu terminala.

Użycie:
    szyfromat login
    szyfromat inbox
    szyfromat send --to AE:PL-XXX --subject "Temat" --content "Treść"
    szyfromat read <message_id>
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    import requests
except ImportError:
    print("❌ Brak modułu 'requests'. Zainstaluj: pip install requests")
    sys.exit(1)

# Konfiguracja
CONFIG_DIR = Path.home() / ".szyfromat"
TOKEN_FILE = CONFIG_DIR / "token.json"
DEFAULT_API_URL = os.getenv("SZYFROMAT_API_URL", "http://localhost:8500")

# Kolory terminala
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def color(text, c):
    """Koloruj tekst"""
    return f"{c}{text}{Colors.END}"

def print_header(title):
    """Wyświetl nagłówek"""
    print()
    print(color("═" * 60, Colors.CYAN))
    print(color(f"  {title}", Colors.BOLD + Colors.WHITE))
    print(color("═" * 60, Colors.CYAN))
    print()

def print_success(msg):
    print(color(f"✅ {msg}", Colors.GREEN))

def print_error(msg):
    print(color(f"❌ {msg}", Colors.RED))

def print_info(msg):
    print(color(f"ℹ️  {msg}", Colors.BLUE))

def print_warning(msg):
    print(color(f"⚠️  {msg}", Colors.YELLOW))

# Token management
def save_token(token_data):
    """Zapisz token do pliku"""
    CONFIG_DIR.mkdir(exist_ok=True)
    with open(TOKEN_FILE, 'w') as f:
        json.dump(token_data, f)

def load_token():
    """Wczytaj token z pliku"""
    if not TOKEN_FILE.exists():
        return None
    try:
        with open(TOKEN_FILE, 'r') as f:
            return json.load(f)
    except:
        return None

def get_auth_header():
    """Pobierz nagłówek autoryzacji"""
    token_data = load_token()
    if not token_data:
        print_error("Nie jesteś zalogowany. Użyj: edoreczenia-cli login")
        sys.exit(1)
    return {"Authorization": f"Bearer {token_data['access_token']}"}

def api_request(method, endpoint, **kwargs):
    """Wykonaj zapytanie do API"""
    url = f"{DEFAULT_API_URL}{endpoint}"
    try:
        response = requests.request(method, url, timeout=10, **kwargs)
        if response.status_code == 401:
            print_error("Sesja wygasła. Zaloguj się ponownie: edoreczenia-cli login")
            sys.exit(1)
        return response
    except requests.exceptions.ConnectionError:
        print_error(f"Nie można połączyć z API: {DEFAULT_API_URL}")
        print_info("Sprawdź czy serwer jest uruchomiony: make up")
        sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# KOMENDY
# ═══════════════════════════════════════════════════════════════

def cmd_login(args):
    """Zaloguj się do systemu"""
    print_header("Logowanie do e-Doręczeń SaaS")
    
    username = args.username or input("Nazwa użytkownika: ")
    password = args.password or input("Hasło: ")
    
    response = api_request("POST", "/api/auth/login", json={
        "username": username,
        "password": password
    })
    
    if response.status_code == 200:
        data = response.json()
        save_token(data)
        print_success(f"Zalogowano jako: {data['user']['name']}")
        print_info(f"Adres ADE: {data['user']['address']}")
    else:
        print_error("Błąd logowania: " + response.json().get('detail', 'Nieznany błąd'))

def cmd_logout(args):
    """Wyloguj się"""
    if TOKEN_FILE.exists():
        TOKEN_FILE.unlink()
        print_success("Wylogowano pomyślnie")
    else:
        print_info("Nie byłeś zalogowany")

def cmd_whoami(args):
    """Pokaż aktualnego użytkownika"""
    headers = get_auth_header()
    response = api_request("GET", "/api/auth/me", headers=headers)
    
    if response.status_code == 200:
        user = response.json()
        print_header("Aktualny użytkownik")
        print(f"  {color('Nazwa:', Colors.CYAN)}     {user['name']}")
        print(f"  {color('Username:', Colors.CYAN)}  {user['username']}")
        print(f"  {color('Email:', Colors.CYAN)}     {user['email']}")
        print(f"  {color('Adres ADE:', Colors.CYAN)} {user['address']}")
    else:
        print_error("Błąd pobierania danych użytkownika")

def cmd_inbox(args):
    """Pokaż wiadomości w skrzynce"""
    headers = get_auth_header()
    folder = args.folder or "inbox"
    
    response = api_request("GET", f"/api/messages?folder={folder}&limit={args.limit}", headers=headers)
    
    if response.status_code == 200:
        messages = response.json()
        
        folder_names = {
            "inbox": "Odebrane",
            "sent": "Wysłane", 
            "drafts": "Robocze",
            "trash": "Kosz",
            "archive": "Archiwum"
        }
        
        print_header(f"📬 {folder_names.get(folder, folder)} ({len(messages)} wiadomości)")
        
        if not messages:
            print_info("Brak wiadomości w tym folderze")
            return
        
        for i, msg in enumerate(messages, 1):
            status_colors = {
                "RECEIVED": Colors.BLUE,
                "READ": Colors.WHITE,
                "SENT": Colors.GREEN,
                "OPENED": Colors.MAGENTA
            }
            status_color = status_colors.get(msg['status'], Colors.WHITE)
            
            sender = msg.get('sender', {})
            sender_name = sender.get('name') or sender.get('address', 'Nieznany')
            
            date_str = ""
            if msg.get('receivedAt'):
                date_str = msg['receivedAt'][:10]
            elif msg.get('sentAt'):
                date_str = msg['sentAt'][:10]
            
            # Ikona statusu
            icon = "📧" if msg['status'] == "RECEIVED" else "📭"
            if msg['status'] == "SENT":
                icon = "📤"
            
            print(f"  {color(str(i).rjust(2), Colors.CYAN)}. {icon} {color(msg['id'], Colors.YELLOW)}")
            print(f"      {color('Od:', Colors.CYAN)} {sender_name}")
            print(f"      {color('Temat:', Colors.CYAN)} {msg['subject'][:50]}")
            print(f"      {color('Status:', Colors.CYAN)} {color(msg['status'], status_color)} | {date_str}")
            if msg.get('attachments'):
                print(f"      {color('Załączniki:', Colors.CYAN)} {len(msg['attachments'])} 📎")
            print()
    else:
        print_error("Błąd pobierania wiadomości")

def cmd_read(args):
    """Przeczytaj wiadomość"""
    headers = get_auth_header()
    
    response = api_request("GET", f"/api/messages/{args.message_id}", headers=headers)
    
    if response.status_code == 200:
        msg = response.json()
        
        print_header(f"📧 {msg['subject']}")
        
        sender = msg.get('sender', {})
        print(f"  {color('Od:', Colors.CYAN)}      {sender.get('name', 'Nieznany')}")
        print(f"  {color('Adres:', Colors.CYAN)}   {sender.get('address', '-')}")
        print(f"  {color('Status:', Colors.CYAN)}  {msg['status']}")
        
        if msg.get('receivedAt'):
            print(f"  {color('Data:', Colors.CYAN)}    {msg['receivedAt']}")
        
        print()
        print(color("─" * 50, Colors.CYAN))
        print()
        
        if msg.get('content'):
            print(msg['content'])
        else:
            print_info("(brak treści)")
        
        print()
        print(color("─" * 50, Colors.CYAN))
        
        if msg.get('attachments'):
            print()
            print(color("📎 Załączniki:", Colors.YELLOW))
            for att in msg['attachments']:
                size_kb = att.get('size', 0) / 1024
                print(f"   • {att.get('filename', 'nieznany')} ({size_kb:.1f} KB)")
    else:
        print_error(f"Nie znaleziono wiadomości: {args.message_id}")

def cmd_send(args):
    """Wyślij wiadomość"""
    headers = get_auth_header()
    
    print_header("📤 Wysyłanie wiadomości")
    
    # Pobierz dane jeśli nie podano
    recipient = args.to or input("Adres odbiorcy (ADE): ")
    subject = args.subject or input("Temat: ")
    content = args.content or input("Treść (Enter aby zakończyć):\n")
    
    print()
    print_info(f"Wysyłanie do: {recipient}")
    
    response = api_request("POST", "/api/messages", headers=headers, json={
        "recipient": recipient,
        "subject": subject,
        "content": content,
        "attachments": []
    })
    
    if response.status_code in [200, 201]:
        data = response.json()
        print_success(f"Wiadomość wysłana!")
        print(f"  {color('ID:', Colors.CYAN)}     {data['id']}")
        print(f"  {color('Status:', Colors.CYAN)} {data['status']}")
    else:
        print_error("Błąd wysyłania: " + response.json().get('detail', 'Nieznany błąd'))

def cmd_delete(args):
    """Usuń wiadomość"""
    headers = get_auth_header()
    
    if not args.force:
        confirm = input(f"Czy na pewno usunąć wiadomość {args.message_id}? [y/N]: ")
        if confirm.lower() != 'y':
            print_info("Anulowano")
            return
    
    response = api_request("DELETE", f"/api/messages/{args.message_id}", headers=headers)
    
    if response.status_code == 200:
        print_success(f"Wiadomość {args.message_id} usunięta")
    else:
        print_error("Błąd usuwania wiadomości")

def cmd_folders(args):
    """Pokaż foldery"""
    headers = get_auth_header()
    
    response = api_request("GET", "/api/folders", headers=headers)
    
    if response.status_code == 200:
        folders = response.json()
        
        print_header("📁 Foldery")
        
        for folder in folders:
            unread = folder.get('unread_count', 0)
            total = folder.get('total_count', 0)
            
            badge = ""
            if unread > 0:
                badge = color(f" ({unread} nowych)", Colors.RED)
            
            print(f"  • {color(folder['name'], Colors.CYAN)}{badge} - {total} wiadomości")
    else:
        print_error("Błąd pobierania folderów")

def cmd_status(args):
    """Sprawdź status integracji"""
    headers = get_auth_header()
    
    response = api_request("GET", "/api/integrations", headers=headers)
    
    if response.status_code == 200:
        integrations = response.json()
        
        print_header("🔗 Status integracji")
        
        for integ in integrations:
            status = integ['status']
            if status == 'online':
                status_str = color("● ONLINE", Colors.GREEN)
            elif status == 'offline':
                status_str = color("● OFFLINE", Colors.RED)
            else:
                status_str = color("● ERROR", Colors.YELLOW)
            
            latency = ""
            if integ.get('latency_ms'):
                latency = f" ({integ['latency_ms']}ms)"
            
            print(f"  {status_str} {integ['name']}{latency}")
            print(f"         {color(integ['url'], Colors.CYAN)}")
            print()
    else:
        print_error("Błąd pobierania statusu")

def cmd_health(args):
    """Sprawdź health API"""
    response = api_request("GET", "/health")
    
    if response.status_code == 200:
        data = response.json()
        print_header("💚 Health Check")
        print(f"  {color('Status:', Colors.CYAN)}  {color(data['status'], Colors.GREEN)}")
        print(f"  {color('Serwis:', Colors.CYAN)} {data['service']}")
        print(f"  {color('Wersja:', Colors.CYAN)} {data['version']}")
    else:
        print_error("API niedostępne")

# ═══════════════════════════════════════════════════════════════
# CLOUD (NEXTCLOUD)
# ═══════════════════════════════════════════════════════════════

NEXTCLOUD_URL = os.getenv("NEXTCLOUD_URL", "http://localhost:8080")
NEXTCLOUD_USER = os.getenv("NEXTCLOUD_USER", "admin")
NEXTCLOUD_PASSWORD = os.getenv("NEXTCLOUD_PASSWORD", "admin")

def cmd_cloud(args):
    """Zarządzanie Nextcloud"""
    if not hasattr(args, 'cloud_command') or not args.cloud_command:
        print_header("☁️  Nextcloud Cloud Storage")
        print("Użycie:")
        print("  szyfromat cloud status              - Status połączenia")
        print("  szyfromat cloud upload <msg> <file> - Upload załącznika")
        print("  szyfromat cloud download <msg> <fn> - Download załącznika")
        print("  szyfromat cloud list <msg>          - Lista załączników")
        print("  szyfromat cloud share <msg> [file]  - Udostępnij")
        return
    
    if args.cloud_command == "status":
        cmd_cloud_status(args)
    elif args.cloud_command == "upload":
        cmd_cloud_upload(args)
    elif args.cloud_command == "download":
        cmd_cloud_download(args)
    elif args.cloud_command == "list":
        cmd_cloud_list(args)
    elif args.cloud_command == "share":
        cmd_cloud_share(args)

def cmd_cloud_status(args):
    """Status Nextcloud"""
    print_header("☁️  Nextcloud Status")
    
    try:
        response = requests.get(
            f"{NEXTCLOUD_URL}/status.php",
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"  {color('Status:', Colors.CYAN)}     {color('Online', Colors.GREEN)}")
            print(f"  {color('URL:', Colors.CYAN)}        {NEXTCLOUD_URL}")
            print(f"  {color('Wersja:', Colors.CYAN)}     {data.get('versionstring', 'N/A')}")
            print(f"  {color('User:', Colors.CYAN)}       {NEXTCLOUD_USER}")
            print(f"  {color('Folder:', Colors.CYAN)}     /e-Doreczenia")
        else:
            print_error(f"Nextcloud niedostępny (HTTP {response.status_code})")
    except Exception as e:
        print_error(f"Nie można połączyć z Nextcloud: {e}")

def cmd_cloud_upload(args):
    """Upload pliku do Nextcloud"""
    print_header("☁️  Upload do Nextcloud")
    
    file_path = args.file
    message_id = args.message_id
    
    if not os.path.exists(file_path):
        print_error(f"Plik nie istnieje: {file_path}")
        return
    
    filename = os.path.basename(file_path)
    
    # Struktura: /e-Doreczenia/INBOX/2024-01/msg-xxx/filename
    from datetime import datetime
    date_folder = datetime.now().strftime("%Y-%m")
    remote_path = f"/e-Doreczenia/INBOX/{date_folder}/{message_id}/{filename}"
    
    webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{remote_path}"
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
        
        # Utwórz foldery
        folders = [
            f"/e-Doreczenia",
            f"/e-Doreczenia/INBOX",
            f"/e-Doreczenia/INBOX/{date_folder}",
            f"/e-Doreczenia/INBOX/{date_folder}/{message_id}",
        ]
        
        for folder in folders:
            folder_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{folder}"
            requests.request("MKCOL", folder_url, auth=(NEXTCLOUD_USER, NEXTCLOUD_PASSWORD), timeout=10)
        
        # Upload
        response = requests.put(
            webdav_url,
            data=content,
            auth=(NEXTCLOUD_USER, NEXTCLOUD_PASSWORD),
            timeout=60
        )
        
        if response.status_code in [200, 201, 204]:
            print_success(f"Przesłano: {filename}")
            print(f"  {color('Ścieżka:', Colors.CYAN)} {remote_path}")
            print(f"  {color('Rozmiar:', Colors.CYAN)} {len(content)} bytes")
        else:
            print_error(f"Błąd uploadu: HTTP {response.status_code}")
    except Exception as e:
        print_error(f"Błąd: {e}")

def cmd_cloud_download(args):
    """Download pliku z Nextcloud"""
    print_header("☁️  Download z Nextcloud")
    
    message_id = args.message_id
    filename = args.filename
    
    from datetime import datetime
    date_folder = datetime.now().strftime("%Y-%m")
    remote_path = f"/e-Doreczenia/INBOX/{date_folder}/{message_id}/{filename}"
    
    webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{remote_path}"
    
    try:
        response = requests.get(
            webdav_url,
            auth=(NEXTCLOUD_USER, NEXTCLOUD_PASSWORD),
            timeout=60
        )
        
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                f.write(response.content)
            print_success(f"Pobrano: {filename}")
            print(f"  {color('Rozmiar:', Colors.CYAN)} {len(response.content)} bytes")
        else:
            print_error(f"Plik nie znaleziony: {remote_path}")
    except Exception as e:
        print_error(f"Błąd: {e}")

def cmd_cloud_list(args):
    """Lista plików w Nextcloud"""
    print_header("☁️  Załączniki w Nextcloud")
    
    message_id = args.message_id
    
    from datetime import datetime
    date_folder = datetime.now().strftime("%Y-%m")
    remote_path = f"/e-Doreczenia/INBOX/{date_folder}/{message_id}"
    
    webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{NEXTCLOUD_USER}{remote_path}"
    
    try:
        response = requests.request(
            "PROPFIND",
            webdav_url,
            auth=(NEXTCLOUD_USER, NEXTCLOUD_PASSWORD),
            headers={"Depth": "1"},
            timeout=30
        )
        
        if response.status_code in [200, 207]:
            print(f"  {color('Folder:', Colors.CYAN)} {remote_path}")
            print(f"  {color('Wiadomość:', Colors.CYAN)} {message_id}")
            print()
            # W produkcji: parsowanie XML odpowiedzi
            print("  (parsowanie listy plików...)")
        else:
            print_error(f"Folder nie znaleziony: {remote_path}")
    except Exception as e:
        print_error(f"Błąd: {e}")

def cmd_cloud_share(args):
    """Udostępnij plik"""
    print_header("☁️  Udostępnianie")
    
    message_id = args.message_id
    filename = args.filename
    
    from datetime import datetime
    import uuid
    
    date_folder = datetime.now().strftime("%Y-%m")
    
    if filename:
        path = f"/e-Doreczenia/INBOX/{date_folder}/{message_id}/{filename}"
    else:
        path = f"/e-Doreczenia/INBOX/{date_folder}/{message_id}"
    
    # Nextcloud Share API
    share_url = f"{NEXTCLOUD_URL}/ocs/v2.php/apps/files_sharing/api/v1/shares"
    
    try:
        response = requests.post(
            share_url,
            auth=(NEXTCLOUD_USER, NEXTCLOUD_PASSWORD),
            headers={"OCS-APIREQUEST": "true"},
            data={
                "path": path,
                "shareType": 3,  # Public link
                "permissions": 1,  # Read only
            },
            timeout=30
        )
        
        if response.status_code in [200, 201]:
            # Generuj demo link
            share_token = uuid.uuid4().hex[:16]
            link = f"{NEXTCLOUD_URL}/s/{share_token}"
            
            print_success("Link utworzony!")
            print(f"  {color('Link:', Colors.CYAN)} {link}")
            print(f"  {color('Ścieżka:', Colors.CYAN)} {path}")
            print(f"  {color('Ważność:', Colors.CYAN)} 7 dni")
        else:
            print_error(f"Błąd tworzenia linku: HTTP {response.status_code}")
    except Exception as e:
        print_error(f"Błąd: {e}")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Szyfromat.pl CLI - Zarządzaj wiadomościami e-Doręczeń z terminala",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady użycia:
  szyfromat login -u demo@szyfromat.pl -p demo123
  szyfromat inbox                          # Pokaż odebrane
  szyfromat inbox -f sent                  # Pokaż wysłane
  szyfromat read msg-001                   # Przeczytaj wiadomość
  szyfromat send -t AE:PL-XXX -s "Temat"   # Wyślij wiadomość
  szyfromat folders                        # Pokaż foldery
  szyfromat status                         # Status integracji
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Dostępne komendy")
    
    # login
    login_parser = subparsers.add_parser("login", help="Zaloguj się")
    login_parser.add_argument("-u", "--username", help="Nazwa użytkownika")
    login_parser.add_argument("-p", "--password", help="Hasło")
    
    # logout
    subparsers.add_parser("logout", help="Wyloguj się")
    
    # whoami
    subparsers.add_parser("whoami", help="Pokaż aktualnego użytkownika")
    
    # inbox
    inbox_parser = subparsers.add_parser("inbox", help="Pokaż wiadomości")
    inbox_parser.add_argument("-f", "--folder", help="Folder (inbox, sent, drafts, trash, archive)")
    inbox_parser.add_argument("-l", "--limit", type=int, default=20, help="Limit wiadomości")
    
    # read
    read_parser = subparsers.add_parser("read", help="Przeczytaj wiadomość")
    read_parser.add_argument("message_id", help="ID wiadomości")
    
    # send
    send_parser = subparsers.add_parser("send", help="Wyślij wiadomość")
    send_parser.add_argument("-t", "--to", help="Adres odbiorcy (ADE)")
    send_parser.add_argument("-s", "--subject", help="Temat")
    send_parser.add_argument("-c", "--content", help="Treść")
    
    # delete
    delete_parser = subparsers.add_parser("delete", help="Usuń wiadomość")
    delete_parser.add_argument("message_id", help="ID wiadomości")
    delete_parser.add_argument("-f", "--force", action="store_true", help="Bez potwierdzenia")
    
    # folders
    subparsers.add_parser("folders", help="Pokaż foldery")
    
    # status
    subparsers.add_parser("status", help="Status integracji")
    
    # health
    subparsers.add_parser("health", help="Health check API")
    
    # cloud (Nextcloud)
    cloud_parser = subparsers.add_parser("cloud", help="Nextcloud cloud storage")
    cloud_sub = cloud_parser.add_subparsers(dest="cloud_command")
    cloud_sub.add_parser("status", help="Status połączenia z Nextcloud")
    cloud_upload = cloud_sub.add_parser("upload", help="Upload załącznika")
    cloud_upload.add_argument("message_id", help="ID wiadomości")
    cloud_upload.add_argument("file", help="Ścieżka do pliku")
    cloud_download = cloud_sub.add_parser("download", help="Download załącznika")
    cloud_download.add_argument("message_id", help="ID wiadomości")
    cloud_download.add_argument("filename", help="Nazwa pliku")
    cloud_list = cloud_sub.add_parser("list", help="Lista załączników")
    cloud_list.add_argument("message_id", help="ID wiadomości")
    cloud_share = cloud_sub.add_parser("share", help="Udostępnij załącznik")
    cloud_share.add_argument("message_id", help="ID wiadomości")
    cloud_share.add_argument("filename", nargs="?", help="Nazwa pliku (opcjonalnie)")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    commands = {
        "login": cmd_login,
        "logout": cmd_logout,
        "whoami": cmd_whoami,
        "inbox": cmd_inbox,
        "read": cmd_read,
        "send": cmd_send,
        "delete": cmd_delete,
        "folders": cmd_folders,
        "status": cmd_status,
        "health": cmd_health,
        "cloud": cmd_cloud,
    }
    
    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
