# e-Doręczenia Middleware Sync

Middleware synchronizujący e-Doręczenia z lokalną skrzynką IMAP. Cyklicznie pobiera wiadomości z e-Doręczeń i importuje je do istniejącego serwera IMAP (np. Dovecot), oraz wysyła wiadomości z dedykowanego folderu IMAP do e-Doręczeń.

## 🎯 Funkcjonalności

- **Synchronizacja przychodząca** - pobiera wiadomości z e-Doręczeń do IMAP
- **Synchronizacja wychodząca** - wysyła wiadomości z IMAP do e-Doręczeń
- **Śledzenie stanu** - baza SQLite zapobiega duplikacjom
- **Załączniki** - pełna obsługa załączników w obu kierunkach
- **Scheduler** - cykliczne uruchamianie synchronizacji
- **EPO** - zachowuje informacje o Elektronicznym Poświadczeniu Odbioru

## 📦 Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/softreck/edoreczenia-middleware-sync.git
cd edoreczenia-middleware-sync

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

# Docelowy serwer IMAP
TARGET_IMAP_HOST=mail.example.com
TARGET_IMAP_PORT=993
TARGET_IMAP_SSL=true
TARGET_IMAP_USERNAME=edoreczenia@example.com
TARGET_IMAP_PASSWORD=haslo_imap

# Konfiguracja synchronizacji
SYNC_INTERVAL_MINUTES=5
SYNC_DIRECTION=bidirectional
```

## 🚀 Uruchomienie

### Tryb daemon (ciągła synchronizacja)
```bash
edoreczenia-sync
# lub
edoreczenia-sync --daemon
```

### Jednorazowa synchronizacja
```bash
edoreczenia-sync --once
```

### Sprawdzenie statusu
```bash
edoreczenia-sync --status
```

## 📂 Struktura folderów IMAP

Po uruchomieniu synchronizacji, w skrzynce IMAP zostaną utworzone foldery:

```
INBOX/
├── e-Doreczenia/          # Wiadomości przychodzące z e-Doręczeń
Sent/
├── e-Doreczenia/          # Wysłane wiadomości do e-Doręczeń
Drafts/
├── e-Doreczenia-Wyslij/   # Wiadomości do wysłania przez e-Doręczenia
```

### Jak wysłać wiadomość przez e-Doręczenia?

1. Utwórz nową wiadomość w kliencie poczty
2. W polu "Do" wpisz adres e-Doręczeń odbiorcy (np. `AE:PL-XXXXX-XXXXX-XXXXX-XX`)
3. Zapisz wiadomość do folderu `Drafts/e-Doreczenia-Wyslij`
4. Middleware automatycznie wyśle wiadomość przy następnej synchronizacji

## 🏗️ Architektura

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────┐
│  Klient poczty  │────▶│  Lokalny serwer      │◀───▶│  Middleware     │
│  (Thunderbird)  │◀────│  IMAP (Dovecot)      │     │  Sync           │
└─────────────────┘     └──────────────────────┘     └────────┬────────┘
       IMAP                     IMAP                          │
                                                              │ REST API
                                                              ▼
                                                    ┌─────────────────┐
                                                    │  API e-Doręczeń │
                                                    └─────────────────┘
```

## 🔄 Kierunki synchronizacji

| Tryb          | Przychodzące | Wychodzące |
|---------------|:------------:|:----------:|
| incoming      | ✅           | ❌         |
| outgoing      | ❌           | ✅         |
| bidirectional | ✅           | ✅         |

## 📊 Baza danych

Middleware używa SQLite do śledzenia stanu synchronizacji:

```bash
# Lokalizacja bazy
./sync_state.db

# Struktura
- synced_messages  # Zsynchronizowane wiadomości
- sync_runs        # Historia uruchomień synchronizacji
```

### Sprawdzenie historii synchronizacji

```bash
sqlite3 sync_state.db "SELECT * FROM sync_runs ORDER BY started_at DESC LIMIT 10;"
```

## 🧪 Testy

```bash
# Uruchomienie testów
pytest

# Z pokryciem kodu
pytest --cov=edoreczenia_sync

# Tylko szybkie testy
pytest -m "not slow"
```

## 🔒 Bezpieczeństwo

⚠️ **Ważne uwagi bezpieczeństwa:**

1. Plik `.env` zawiera poświadczenia - nie commituj go do repozytorium
2. Baza SQLite może zawierać metadane wiadomości - zabezpiecz ją
3. Używaj SSL/TLS dla połączeń IMAP i SMTP
4. Regularnie rotuj tokeny OAuth2

## 📋 Porównanie z Proxy IMAP/SMTP

| Cecha                   | Middleware Sync     | Proxy IMAP/SMTP    |
|-------------------------|--------------------|--------------------|
| Złożoność               | Niska-średnia      | Wysoka             |
| Opóźnienie              | Cykliczne (minuty) | Minimalne          |
| Istniejąca infrastruktura| Wymaga serwera IMAP| Nie wymaga         |
| Kompatybilność          | Każdy klient IMAP  | Każdy klient IMAP  |
| Praca offline           | Tak (lokalny IMAP) | Nie                |
| Łatwość wdrożenia       | Łatwa              | Trudna             |

## 🐳 Docker

### Szybki start

```bash
# Uruchomienie wszystkich serwisów
make up

# Lub ręcznie
docker-compose up -d
```

### Dostępne serwisy

| Serwis | URL | Opis |
|--------|-----|------|
| Symulator API | http://localhost:8080 | Symulator REST API e-Doręczeń |
| API Docs | http://localhost:8080/docs | Dokumentacja Swagger |
| Dovecot IMAP | localhost:1143 | Lokalny serwer IMAP |
| Webmail | http://localhost:9000 | Roundcube |
| Adminer | http://localhost:9001 | Przeglądarka bazy (debug) |

### Dane testowe

```
IMAP User: mailuser
IMAP Pass: mailpass123

API Client ID: test_client_id
API Client Secret: test_client_secret
Test Address: AE:PL-12345-67890-ABCDE-12
```

### Komendy Make

```bash
make build       # Buduje obrazy
make up          # Uruchamia kontenery
make down        # Zatrzymuje kontenery
make logs        # Pokazuje logi
make test        # Uruchamia testy
make sync-once   # Jednorazowa synchronizacja
make sync-status # Status synchronizacji
make debug       # Tryb debug z adminerem
make clean       # Czyści zasoby
```

### Architektura Docker

```
┌────────────────────────────────────────────────────────────────┐
│                      Docker Network                             │
│                                                                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Simulator  │◄───│  Middleware │───▶│  Dovecot    │        │
│  │  :8080      │    │    Sync     │    │   :143      │        │
│  └─────────────┘    └──────┬──────┘    └──────┬──────┘        │
│                            │                   │               │
│                     ┌──────▼──────┐    ┌──────▼──────┐        │
│                     │  SQLite DB  │    │  Webmail    │        │
│                     │  (volume)   │    │   :9000     │        │
│                     └─────────────┘    └─────────────┘        │
└────────────────────────────────────────────────────────────────┘
```

### Przykładowe wiadomości

Po uruchomieniu, symulator zawiera 3 przykładowe wiadomości:
1. **Decyzja administracyjna** - z załącznikiem PDF
2. **Zawiadomienie o terminie rozprawy** - z EPO
3. **Wezwanie do uzupełnienia dokumentów** - z wieloma załącznikami

Wiadomości zostaną automatycznie zsynchronizowane do folderu `INBOX.e-Doreczenia` w Dovecot.

## 📄 Licencja

MIT License - zobacz plik [LICENSE](LICENSE)

## 🤝 Współpraca

Zapraszamy do zgłaszania issues i pull requestów!

## 📚 Zasoby

- [Dokumentacja API e-Doręczeń](https://edoreczenia.poczta-polska.pl/)
- [Dovecot - serwer IMAP](https://www.dovecot.org/)
- [IMAPClient dokumentacja](https://imapclient.readthedocs.io/)
