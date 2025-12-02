# e-Doręczenia DSL

DSL (Domain Specific Language) oparty na **Apache Camel**, **Groovy** i **Python** do obsługi wysyłki i odbioru dokumentów e-Doręczeń.

## 🎯 Funkcjonalności

- **Python Client** - pełny klient API z logowaniem do Markdown
- **Groovy DSL** - skrypty Apache Camel do routingu wiadomości
- **Scenariusze testowe** - automatyczne testy z raportami
- **Raporty Markdown** - szczegółowe logi w formacie MD

## 🐳 Docker

### Szybki start

```bash
# Uruchomienie
make up

# Lub w tle
docker-compose up -d --build
```

### Dostępne usługi

| Usługa | URL/Port | Opis |
|--------|----------|------|
| **API Docs** | http://localhost:8380/docs | Swagger dokumentacja API |
| **IMAP** | localhost:31143 | Dovecot IMAP |
| **SMTP** | localhost:31025 | SMTP Proxy |

### Dane testowe

```
IMAP User: mailuser
IMAP Pass: mailpass123

SMTP User: testuser
SMTP Pass: testpass123

API Client ID: test_client_id
API Client Secret: test_client_secret
Test Address: AE:PL-12345-67890-ABCDE-12
```

### Komendy Make

```bash
# Komendy lokalne
make build      # Buduje obrazy
make up         # Uruchamia kontenery
make down       # Zatrzymuje kontenery
make logs       # Pokazuje logi
make status     # Status kontenerów
make clean      # Czyści zasoby

# Komendy wszystkich usług
make all-up     # Uruchamia WSZYSTKIE usługi (proxy + sync + dsl)
make all-down   # Zatrzymuje WSZYSTKIE usługi
make all-status # Status wszystkich usług
make e2e-test   # Testy E2E całego systemu

# Komendy innych usług
make proxy-up   # Uruchamia proxy IMAP/SMTP
make sync-up    # Uruchamia middleware-sync

# Komendy testowe DSL
make test           # Szybki test DSL
make test-scenarios # Pełne testy scenariuszowe (raporty MD)
make send           # Wysyła testową wiadomość
make receive        # Odbiera wiadomości

# Raporty
make show-report    # Wyświetl ostatni raport
make list-reports   # Lista wszystkich raportów
```

## 📤 Wysyłanie wiadomości

### Przez make:
```bash
$ make send
📤 Wysyłanie testowej wiadomości...
[2025-12-02 14:21:50.062] → [AUTH] Pobieranie tokenu OAuth2 z http://localhost:8380
[2025-12-02 14:21:50.087] ✓ [AUTH] Token OAuth2 pobrany
[2025-12-02 14:21:50.087] → [API] Wysyłanie wiadomości do: AE:PL-ODBIORCA-TEST-00001
[2025-12-02 14:21:50.089] ✓ [API] Wiadomość wysłana
✅ Wysłano: msg-d21880e2 [SENT]
```

### Przez Python Client:
```python
from python_client.client import EDoreczeniaClient

client = EDoreczeniaClient()
client.authenticate()
result = client.send_message(
    recipient='AE:PL-ODBIORCA-00001',
    subject='Ważny dokument',
    content='Treść wiadomości'
)
print(f"Wysłano: {result['messageId']}")
```

## 📥 Odbieranie wiadomości

### Przez make:
```bash
$ make receive
📥 Odbieranie wiadomości...
[2025-12-02 14:21:56.245] → [AUTH] Pobieranie tokenu OAuth2 z http://localhost:8380
[2025-12-02 14:21:56.273] ✓ [AUTH] Token OAuth2 pobrany
[2025-12-02 14:21:56.273] → [API] Pobieranie wiadomości z folderu: inbox
[2025-12-02 14:21:56.275] ✓ [API] Pobrano 3 wiadomości
📧 Pobrano 3 wiadomości:
   • Decyzja administracyjna nr 123/2024 [READ]
   • Zawiadomienie o terminie rozprawy [READ]
   • Wezwanie do uzupełnienia dokumentów [RECEIVED]
```

### Przez Python Client:
```python
from python_client.client import EDoreczeniaClient

client = EDoreczeniaClient()
client.authenticate()
messages = client.get_messages(folder='inbox', limit=10)
for msg in messages:
    print(f"📧 {msg['subject']} [{msg['status']}]")
```

## 🧪 Testy scenariuszowe

### Uruchomienie:
```bash
$ make test-scenarios
🧪 Uruchamianie scenariuszy testowych...

════════════════════════════════════════════════════════════
  e-Doręczenia DSL - Scenariusze testowe
════════════════════════════════════════════════════════════

────────────────────────────────────────
  📋 Health Check
────────────────────────────────────────
[2025-12-02 14:18:47.135] → [SCENARIO] Rozpoczęcie: Health Check
[2025-12-02 14:18:47.146] ✓ [API] API healthy: User Agent API Simulator
[2025-12-02 14:18:47.146] → [SCENARIO] Zakończenie: Health Check - ✅ PASS

...

════════════════════════════════════════════════════════════
  PODSUMOWANIE
════════════════════════════════════════════════════════════
  ✅ Health Check
  ✅ OAuth2 Authentication
  ✅ List Messages
  ✅ Send Message
  ✅ Get Message Details
  ✅ List Directories
  ✅ Full Flow

  Wynik: 7/7 (100%)
  Raport: logs/all_scenarios_20251202_141847.md
════════════════════════════════════════════════════════════
```

### Raporty Markdown:
```bash
# Lista raportów
$ make list-reports
📋 Raporty w logs/:
-rw-rw-r-- 1 tom tom 10441 Dec  2 14:17 logs/all_scenarios_20251202_141756.md
-rw-rw-r-- 1 tom tom 10441 Dec  2 14:18 logs/all_scenarios_20251202_141847.md

# Wyświetl ostatni raport
$ make show-report
```

## 🔍 Weryfikacja w przeglądarce i shell

### Panel webowy API:
```bash
open http://localhost:8380/docs
```

### Test IMAP przez shell:
```bash
python3 -c "
import imaplib
m = imaplib.IMAP4('localhost', 31143)
m.login('mailuser', 'mailpass123')
m.select('INBOX.e-Doreczenia')
typ, data = m.search(None, 'ALL')
print(f'Wiadomości: {len(data[0].split())}')
m.logout()
"
```

### Test API przez curl:
```bash
# Health check
curl -s http://localhost:8380/health | python3 -m json.tool

# Token OAuth2
curl -s -X POST http://localhost:8380/oauth/token \
  -d "grant_type=client_credentials&client_id=test_client_id&client_secret=test_client_secret" \
  | python3 -m json.tool
```

## 📁 Struktura projektu

```
edoreczenia-dsl/
├── logs/                     # Raporty Markdown
│   └── all_scenarios_*.md
├── python_client/            # Python DSL Client
│   ├── __init__.py
│   ├── client.py             # Klient API
│   ├── config.py             # Konfiguracja z .env
│   ├── logger.py             # Logger Markdown
│   ├── scenarios.py          # Scenariusze testowe
│   └── run_tests.py          # Runner testów
├── routes/                   # Groovy DSL
│   ├── edoreczenia.groovy
│   ├── send-document.groovy
│   ├── receive-messages.groovy
│   └── test-dsl.py
├── src/main/groovy/          # Apache Camel
├── .env                      # Konfiguracja
├── docker-compose.yml
├── Makefile
└── README.md
```

## 🔗 Powiązane usługi

| Usługa | Folder | Porty | Opis |
|--------|--------|-------|------|
| **Proxy IMAP/SMTP** | `edoreczenia-proxy-imap-smtp` | 8180, 11143, 11025, 9080 | Proxy protokołów |
| **Middleware Sync** | `edoreczenia-middleware-sync` | 8280, 21143, 9180 | Synchronizacja z Dovecot |
| **DSL** | `edoreczenia-dsl` | 8380, 31143, 31025 | Ten projekt |

## 📄 Licencja

MIT
