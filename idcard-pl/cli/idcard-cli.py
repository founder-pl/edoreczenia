#!/usr/bin/env python3
"""
IDCard.pl CLI - Interfejs wiersza poleceń
DSL do zarządzania integracjami usług cyfrowych
"""

import argparse
import json
import os
import sys
from datetime import datetime

try:
    import requests
except ImportError:
    print("Instaluję requests...")
    os.system("pip install requests")
    import requests

# Konfiguracja
API_URL = os.getenv("IDCARD_API_URL", "http://localhost:4000")
TOKEN_FILE = os.path.expanduser("~/.idcard_token")

# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════

def save_token(token: str):
    with open(TOKEN_FILE, "w") as f:
        f.write(token)

def load_token() -> str:
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return f.read().strip()
    return None

def get_headers():
    token = load_token()
    if not token:
        print("❌ Nie zalogowano. Użyj: idcard login")
        sys.exit(1)
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

def print_json(data):
    print(json.dumps(data, indent=2, ensure_ascii=False))

def print_table(headers, rows):
    widths = [max(len(str(h)), max(len(str(r[i])) for r in rows) if rows else 0) for i, h in enumerate(headers)]
    fmt = " | ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt.format(*[str(c) for c in row]))

# ═══════════════════════════════════════════════════════════════
# COMMANDS
# ═══════════════════════════════════════════════════════════════

def cmd_login(args):
    """Logowanie do IDCard.pl"""
    email = args.email or input("Email: ")
    password = args.password or input("Hasło: ")
    
    r = requests.post(f"{API_URL}/api/auth/login", json={
        "email": email,
        "password": password
    })
    
    if r.status_code == 200:
        data = r.json()
        save_token(data["access_token"])
        print(f"✅ Zalogowano jako: {data['user']['email']}")
        print(f"   Nazwa: {data['user']['name']}")
    else:
        print(f"❌ Błąd logowania: {r.json().get('detail', 'Nieznany błąd')}")
        sys.exit(1)

def cmd_register(args):
    """Rejestracja nowego konta"""
    email = args.email or input("Email: ")
    password = args.password or input("Hasło: ")
    name = args.name or input("Imię i nazwisko: ")
    
    r = requests.post(f"{API_URL}/api/auth/register", json={
        "email": email,
        "password": password,
        "name": name
    })
    
    if r.status_code == 200:
        data = r.json()
        save_token(data["access_token"])
        print(f"✅ Zarejestrowano: {data['user']['email']}")
    else:
        print(f"❌ Błąd rejestracji: {r.json().get('detail', 'Nieznany błąd')}")
        sys.exit(1)

def cmd_whoami(args):
    """Informacje o zalogowanym użytkowniku"""
    r = requests.get(f"{API_URL}/api/auth/me", headers=get_headers())
    
    if r.status_code == 200:
        data = r.json()
        print(f"👤 Użytkownik: {data['name']}")
        print(f"   Email: {data['email']}")
        print(f"   ID: {data['id']}")
        if data.get('company_name'):
            print(f"   Firma: {data['company_name']}")
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_services(args):
    """Lista dostępnych usług"""
    r = requests.get(f"{API_URL}/api/services")
    
    if r.status_code == 200:
        data = r.json()
        print("\n📋 Dostępne usługi:\n")
        for s in data["services"]:
            status = "🟢" if s["status"] == "available" else "🟡"
            print(f"{status} {s['name']} ({s['provider']})")
            print(f"   {s['description']}")
            print(f"   Metody auth: {', '.join(s['auth_methods'])}")
            print()
    else:
        print(f"❌ Błąd: {r.text}")

def cmd_connections(args):
    """Lista połączeń użytkownika"""
    r = requests.get(f"{API_URL}/api/services/connections", headers=get_headers())
    
    if r.status_code == 200:
        data = r.json()
        if not data["connections"]:
            print("📭 Brak połączeń. Użyj: idcard connect <service>")
            return
        
        print("\n🔗 Twoje połączenia:\n")
        headers = ["ID", "Usługa", "Status", "Adres"]
        rows = [[c["id"][:12], c["service_type"], c["status"], c.get("external_address", "-")] 
                for c in data["connections"]]
        print_table(headers, rows)
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_connect(args):
    """Połącz z usługą"""
    service = args.service
    
    credentials = {}
    config = {"auth_method": args.auth_method or "oauth2"}
    
    if service == "edoreczenia":
        credentials["ade_address"] = args.address or input("Adres e-Doręczeń (AE:PL-...): ")
    
    r = requests.post(f"{API_URL}/api/services/connect", headers=get_headers(), json={
        "service_type": service,
        "credentials": credentials,
        "config": config
    })
    
    if r.status_code == 200:
        data = r.json()
        print(f"✅ Połączono z {service}")
        print(f"   Connection ID: {data['connection_id']}")
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_disconnect(args):
    """Rozłącz usługę"""
    r = requests.delete(f"{API_URL}/api/services/connections/{args.connection_id}", headers=get_headers())
    
    if r.status_code == 200:
        print(f"✅ Rozłączono: {args.connection_id}")
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_inbox(args):
    """Zunifikowana skrzynka odbiorcza"""
    r = requests.get(f"{API_URL}/api/inbox", headers=get_headers())
    
    if r.status_code == 200:
        data = r.json()
        if not data.get("messages"):
            print("📭 Skrzynka pusta")
            return
        
        print(f"\n📬 Wiadomości ({data.get('total', 0)}):\n")
        for msg in data["messages"][:10]:
            status = "📩" if not msg.get("is_read") else "📧"
            print(f"{status} [{msg['service']}] {msg['subject']}")
            print(f"   Od: {msg['sender']} | {msg['received_at'][:10]}")
            print()
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_notifications(args):
    """Powiadomienia"""
    r = requests.get(f"{API_URL}/api/notifications", headers=get_headers())
    
    if r.status_code == 200:
        data = r.json()
        if not data.get("notifications"):
            print("🔔 Brak powiadomień")
            return
        
        print("\n🔔 Powiadomienia:\n")
        for n in data["notifications"][:10]:
            icon = "🔴" if not n.get("is_read") else "⚪"
            print(f"{icon} [{n['service']}] {n['title']}")
            print(f"   {n['message']}")
            print()
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_dashboard(args):
    """Dashboard użytkownika"""
    r = requests.get(f"{API_URL}/api/dashboard", headers=get_headers())
    
    if r.status_code == 200:
        data = r.json()
        user = data.get("user", {})
        stats = data.get("stats", {})
        
        print(f"\n📊 Dashboard - {user.get('name', 'Użytkownik')}\n")
        print(f"   Połączone usługi: {stats.get('connected_services', 0)}")
        print(f"   Nieprzeczytane:   {stats.get('unread_messages', 0)}")
        print(f"   Powiadomienia:    {stats.get('pending_notifications', 0)}")
    else:
        print(f"❌ Błąd: {r.json().get('detail', 'Nieznany błąd')}")

def cmd_health(args):
    """Sprawdź status API"""
    try:
        r = requests.get(f"{API_URL}/health", timeout=5)
        if r.status_code == 200:
            data = r.json()
            print(f"✅ IDCard.pl API: {data['status']}")
            print(f"   URL: {API_URL}")
        else:
            print(f"⚠️ Status: {r.status_code}")
    except Exception as e:
        print(f"❌ Nie można połączyć z {API_URL}")
        print(f"   Błąd: {e}")

def cmd_logout(args):
    """Wyloguj"""
    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
    print("✅ Wylogowano")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="IDCard.pl CLI - Zarządzanie integracjami usług cyfrowych",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Przykłady:
  idcard login -u demo@idcard.pl -p demo123
  idcard services
  idcard connect edoreczenia --address "AE:PL-JAN-KOWAL-1234-01"
  idcard inbox
  idcard dashboard
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Dostępne komendy")
    
    # login
    p = subparsers.add_parser("login", help="Zaloguj się")
    p.add_argument("-u", "--email", help="Email")
    p.add_argument("-p", "--password", help="Hasło")
    p.set_defaults(func=cmd_login)
    
    # register
    p = subparsers.add_parser("register", help="Zarejestruj konto")
    p.add_argument("-u", "--email", help="Email")
    p.add_argument("-p", "--password", help="Hasło")
    p.add_argument("-n", "--name", help="Imię i nazwisko")
    p.set_defaults(func=cmd_register)
    
    # whoami
    p = subparsers.add_parser("whoami", help="Informacje o użytkowniku")
    p.set_defaults(func=cmd_whoami)
    
    # services
    p = subparsers.add_parser("services", help="Lista usług")
    p.set_defaults(func=cmd_services)
    
    # connections
    p = subparsers.add_parser("connections", help="Lista połączeń")
    p.set_defaults(func=cmd_connections)
    
    # connect
    p = subparsers.add_parser("connect", help="Połącz z usługą")
    p.add_argument("service", choices=["edoreczenia", "epuap", "ksef", "detax"], help="Nazwa usługi")
    p.add_argument("--address", help="Adres zewnętrzny (np. ADE)")
    p.add_argument("--auth-method", default="oauth2", help="Metoda autoryzacji")
    p.set_defaults(func=cmd_connect)
    
    # disconnect
    p = subparsers.add_parser("disconnect", help="Rozłącz usługę")
    p.add_argument("connection_id", help="ID połączenia")
    p.set_defaults(func=cmd_disconnect)
    
    # inbox
    p = subparsers.add_parser("inbox", help="Zunifikowana skrzynka")
    p.set_defaults(func=cmd_inbox)
    
    # notifications
    p = subparsers.add_parser("notifications", help="Powiadomienia")
    p.set_defaults(func=cmd_notifications)
    
    # dashboard
    p = subparsers.add_parser("dashboard", help="Dashboard")
    p.set_defaults(func=cmd_dashboard)
    
    # health
    p = subparsers.add_parser("health", help="Status API")
    p.set_defaults(func=cmd_health)
    
    # logout
    p = subparsers.add_parser("logout", help="Wyloguj")
    p.set_defaults(func=cmd_logout)
    
    args = parser.parse_args()
    
    if args.command is None:
        parser.print_help()
        sys.exit(0)
    
    args.func(args)

if __name__ == "__main__":
    main()
