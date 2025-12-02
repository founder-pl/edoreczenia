# e-Doręczenia Proxy IMAP/SMTP

Most między protokołami pocztowymi IMAP/SMTP a REST API e-Doręczeń. Umożliwia korzystanie z e-Doręczeń przez standardowe klienty poczty (Thunderbird, Outlook, Apple Mail, itp.).

## 🎯 Funkcjonalności

- **Serwer IMAP** - emuluje protokół IMAP4rev1, tłumacząc komendy na wywołania REST API
- **Serwer SMTP** - przyjmuje wiadomości i przekazuje je do API e-Doręczeń
- **OAuth2** - automatyczna obsługa tokenów autoryzacyjnych
- **Mapowanie folderów** - translacja folderów IMAP ↔ e-Doręczenia
- **Synchronizacja flag** - przeczytane, odpowiedziane, usunięte

## 📦 Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/softreck/edoreczenia-proxy-imap-smtp.git
cd edoreczenia-proxy-imap-smtp

# Utworzenie środowiska wirtualnego
python -m venv venv
source venv/bin/activate  # Linux/macOS
# lub: venv\Scripts\activate  # Windows

# Instalacja zależności
pip install -e ".[dev]"
```

## ⚙️ Konfiguracja

1. Skopiuj plik `.env.example` do `.env`:
```bash
cp .env.example .env
```

2. Uzupełnij dane w pliku `.env`:
```env
# OAuth2 - dane z panelu e-Doręczeń
EDORECZENIA_CLIENT_ID=twoj_client_id
EDORECZENIA_CLIENT_SECRET=twoj_client_secret
EDORECZENIA_ADDRESS=AE:PL-12345-67890-ABCDE-12

# Lokalna autoryzacja IMAP/SMTP
LOCAL_AUTH_USERNAME=edoreczenia
LOCAL_AUTH_PASSWORD=bezpieczne_haslo
```

## 🚀 Uruchomienie

```bash
# Uruchomienie serwera
edoreczenia-proxy

# Lub bezpośrednio
python -m edoreczenia_proxy.main
```

Domyślne porty:
- IMAP: `1143`
- SMTP: `1025`

## 📧 Konfiguracja klienta poczty

### Thunderbird

1. **Ustawienia serwera poczty przychodzącej:**
   - Protokół: IMAP
   - Serwer: `localhost`
   - Port: `1143`
   - Bezpieczeństwo: Brak (lub STARTTLS z certyfikatem)
   - Metoda uwierzytelniania: Hasło normalne

2. **Ustawienia serwera poczty wychodzącej:**
   - Serwer: `localhost`
   - Port: `1025`
   - Bezpieczeństwo: Brak
   - Metoda uwierzytelniania: Hasło normalne

3. **Dane logowania:**
   - Użytkownik: wartość `LOCAL_AUTH_USERNAME` z `.env`
   - Hasło: wartość `LOCAL_AUTH_PASSWORD` z `.env`

## 🏗️ Architektura

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Klient poczty  │────▶│  Proxy IMAP/SMTP     │────▶│  API e-Doręczeń │
│  (Thunderbird)  │◀────│  (ten projekt)       │◀────│  (REST + OAuth2)│
└─────────────────┘     └──────────────────────┘     └─────────────────┘
       IMAP/SMTP              Translacja                   REST API
```

### Mapowanie folderów

| Folder IMAP | Folder e-Doręczeń |
|-------------|-------------------|
| INBOX       | inbox             |
| Sent        | sent              |
| Drafts      | drafts            |
| Trash       | trash             |
| Archive     | archive           |

### Mapowanie statusów/flag

| Status e-Doręczeń | Flaga IMAP    |
|-------------------|---------------|
| READ              | \Seen         |
| OPENED            | \Seen         |
| REPLIED           | \Answered     |
| RECEIVED          | (brak flag)   |

## 🧪 Testy

```bash
# Uruchomienie testów
pytest

# Z pokryciem kodu
pytest --cov=edoreczenia_proxy

# Tylko szybkie testy jednostkowe
pytest -m "not integration"
```

## 🔒 Bezpieczeństwo

⚠️ **Ważne uwagi bezpieczeństwa:**

1. Proxy przechowuje lokalnie dane uwierzytelniające - używaj silnych haseł
2. W środowisku produkcyjnym włącz SSL/TLS
3. Nie udostępniaj portów proxy w sieci publicznej
4. Regularnie rotuj tokeny OAuth2

### Włączenie SSL

```env
IMAP_SSL_CERT=/path/to/cert.pem
IMAP_SSL_KEY=/path/to/key.pem
SMTP_SSL_CERT=/path/to/cert.pem
SMTP_SSL_KEY=/path/to/key.pem
```

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
| **Webmail** | http://localhost:9080 | Roundcube - panel webowy |
| **API Docs** | http://localhost:8180/docs | Swagger dokumentacja API |
| **IMAP** | localhost:11143 | Serwer IMAP proxy |
| **SMTP** | localhost:11025 | Serwer SMTP proxy |

### Dane testowe

```
IMAP/SMTP User: testuser
IMAP/SMTP Pass: testpass123

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
make test       # Uruchamia testy
make status     # Status kontenerów
make clean      # Czyści zasoby

# Komendy wszystkich usług
make all-up     # Uruchamia WSZYSTKIE usługi (proxy + sync + dsl)
make all-down   # Zatrzymuje WSZYSTKIE usługi
make all-status # Status wszystkich usług
make e2e-test   # Testy E2E całego systemu

# Komendy innych usług
make sync-up    # Uruchamia middleware-sync
make dsl-up     # Uruchamia DSL
```

### Przykładowe uruchomienie i testy

```bash
# 1. Uruchom usługę
make up

# 2. Sprawdź status
make status

# 3. Sprawdź API w przeglądarce
open http://localhost:8180/docs

# 4. Zaloguj się do webmaila
open http://localhost:9080
# Login: testuser / testpass123

# 5. Test IMAP przez shell
python3 -c "
import imaplib
m = imaplib.IMAP4('localhost', 11143)
m.login('testuser', 'testpass123')
m.select('INBOX')
typ, data = m.search(None, 'ALL')
print(f'Wiadomości w INBOX: {len(data[0].split())}')
m.logout()
"

# 6. Uruchom testy jednostkowe
make test

# 7. Uruchom testy E2E całego systemu
make e2e-test
```

### Architektura Docker

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network                            │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │  Simulator  │◄───│   Proxy     │◄───│  Webmail    │      │
│  │  :8180      │    │ IMAP:11143  │    │  :9080      │      │
│  │  /docs      │    │ SMTP:11025  │    │ (Roundcube) │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 🔗 Powiązane usługi

| Usługa | Folder | Porty | Opis |
|--------|--------|-------|------|
| **Proxy IMAP/SMTP** | `edoreczenia-proxy-imap-smtp` | 8180, 11143, 11025, 9080 | Ten projekt |
| **Middleware Sync** | `edoreczenia-middleware-sync` | 8280, 21143, 9180 | Synchronizacja z Dovecot |
| **DSL** | `edoreczenia-dsl` | 8380, 31143, 31025 | Apache Camel + Python Client |

## 📄 Licencja

MIT License - zobacz plik [LICENSE](LICENSE)

## 🤝 Współpraca

Zapraszamy do zgłaszania issues i pull requestów!

1. Fork repozytorium
2. Utwórz branch (`git checkout -b feature/nowa-funkcja`)
3. Commit zmian (`git commit -am 'Dodaj nową funkcję'`)
4. Push (`git push origin feature/nowa-funkcja`)
5. Utwórz Pull Request

## 📚 Zasoby

- [Dokumentacja API e-Doręczeń](https://edoreczenia.poczta-polska.pl/)
- [RFC 3501 - IMAP4rev1](https://tools.ietf.org/html/rfc3501)
- [RFC 5321 - SMTP](https://tools.ietf.org/html/rfc5321)
