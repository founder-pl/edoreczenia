# e-Doręczenia DSL

DSL (Domain Specific Language) oparty na **Apache Camel** i **Groovy** do obsługi wysyłki i odbioru dokumentów e-Doręczeń.

## Architektura

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        e-Doręczenia DSL                                  │
│                    (Apache Camel + Groovy)                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐               │
│  │   REST API   │    │  File Watch  │    │    Timer     │               │
│  │  :8090       │    │   /outbox    │    │  Auto-Sync   │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
│         └───────────────────┼───────────────────┘                        │
│                             │                                            │
│                    ┌────────▼────────┐                                   │
│                    │  Camel Routes   │                                   │
│                    │  (Groovy DSL)   │                                   │
│                    └────────┬────────┘                                   │
│                             │                                            │
│         ┌───────────────────┼───────────────────┐                        │
│         │                   │                   │                        │
│  ┌──────▼───────┐    ┌──────▼───────┐    ┌──────▼───────┐               │
│  │  API Client  │    │ IMAP Client  │    │ SMTP Client  │               │
│  │  (HTTP)      │    │ (Dovecot)    │    │ (Proxy)      │               │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘               │
│         │                   │                   │                        │
└─────────┼───────────────────┼───────────────────┼────────────────────────┘
          │                   │                   │
          ▼                   ▼                   ▼
   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
   │  Symulator   │    │   Dovecot    │    │ SMTP Proxy   │
   │  API :8180   │    │   :21143     │    │   :11025     │
   └──────────────┘    └──────────────┘    └──────────────┘
```

## Szybki start

### 1. Uruchomienie z Docker

```bash
# Budowanie i uruchomienie
make up

# Sprawdzenie statusu
make status

# Logi
make logs
```

### 2. Wysyłanie wiadomości

#### Przez REST API:
```bash
curl -X POST http://localhost:8090/api/v1/messages \
  -H 'Content-Type: application/json' \
  -d '{
    "subject": "Ważny dokument",
    "recipient": "AE:PL-ODBIORCA-00001",
    "content": "Treść wiadomości",
    "attachments": []
  }'
```

#### Przez Groovy DSL:
```bash
groovy routes/send-document.groovy \
  -f dokument.pdf \
  -r AE:PL-ODBIORCA-00001 \
  -s "Przesyłam dokument"
```

#### Przez Makefile:
```bash
make send
```

### 3. Odbieranie wiadomości

#### Przez REST API:
```bash
curl http://localhost:8090/api/v1/messages
```

#### Przez Groovy DSL:
```bash
groovy routes/receive-messages.groovy -f inbox -l 10
```

#### Przez Makefile:
```bash
make receive
```

### 4. Synchronizacja API → IMAP

```bash
# Przez REST API
curl -X POST http://localhost:8090/api/v1/sync/to-imap

# Przez Makefile
make sync
```

## Dostępne Routes

| Route | Opis |
|-------|------|
| `direct:send-message` | Wysyłanie wiadomości przez API |
| `direct:receive-messages` | Odbieranie wiadomości z API |
| `direct:get-message` | Pobieranie szczegółów wiadomości |
| `direct:get-attachment` | Pobieranie załącznika |
| `direct:sync-to-imap` | Synchronizacja API → Dovecot |
| `direct:sync-from-imap` | Synchronizacja Dovecot → API |
| `direct:send-via-smtp` | Wysyłanie przez SMTP Proxy |
| `direct:receive-via-imap` | Odbieranie przez IMAP Proxy |

## REST API Endpoints

| Metoda | Endpoint | Opis |
|--------|----------|------|
| POST | `/api/v1/messages` | Wysyłanie wiadomości |
| GET | `/api/v1/messages` | Lista wiadomości |
| GET | `/api/v1/messages/{id}` | Szczegóły wiadomości |
| POST | `/api/v1/sync/to-imap` | Synchronizacja do IMAP |
| POST | `/api/v1/sync/from-imap` | Synchronizacja z IMAP |

## Konfiguracja

### Zmienne środowiskowe

| Zmienna | Domyślna wartość | Opis |
|---------|------------------|------|
| `EDORECZENIA_API_URL` | `http://localhost:8180` | URL API e-Doręczeń |
| `EDORECZENIA_ADDRESS` | `AE:PL-12345-67890-ABCDE-12` | Adres nadawcy |
| `EDORECZENIA_CLIENT_ID` | `test_client_id` | Client ID OAuth2 |
| `EDORECZENIA_CLIENT_SECRET` | `test_client_secret` | Client Secret |
| `IMAP_HOST` | `localhost` | Host IMAP (Dovecot) |
| `IMAP_PORT` | `21143` | Port IMAP |
| `IMAP_USER` | `mailuser` | Użytkownik IMAP |
| `IMAP_PASSWORD` | `mailpass123` | Hasło IMAP |
| `SMTP_HOST` | `localhost` | Host SMTP Proxy |
| `SMTP_PORT` | `11025` | Port SMTP |
| `AUTO_SYNC` | `false` | Automatyczna synchronizacja |
| `FILE_WATCH` | `false` | Obserwowanie katalogu /outbox |

## Funkcje automatyczne

### Auto-Sync (synchronizacja co minutę)
```bash
AUTO_SYNC=true docker-compose up -d
```

### File Watch (wysyłanie plików z /outbox)
```bash
FILE_WATCH=true docker-compose up -d

# Wrzuć plik do wysłania
cp dokument.pdf outbox/
```

## Przykłady Groovy DSL

### Wysyłanie z załącznikiem
```groovy
def token = getToken(config)
def attachment = prepareAttachment(new File('dokument.pdf'))

sendMessage(config, token, 
    'AE:PL-ODBIORCA-00001',
    'Ważny dokument',
    'W załączeniu przesyłam dokument.',
    [attachment]
)
```

### Odbieranie i przetwarzanie
```groovy
def token = getToken(config)
def messages = getMessages(config, token, 'inbox', 50)

messages.each { msg ->
    println "📧 ${msg.subject} od ${msg.sender?.address}"
    
    msg.attachments?.each { att ->
        println "   📎 ${att.filename}"
    }
}
```

## Struktura projektu

```
edoreczenia-dsl/
├── build.gradle              # Konfiguracja Gradle
├── docker-compose.yml        # Docker Compose
├── Dockerfile                # Obraz Docker
├── Makefile                  # Komendy make
├── .env                      # Zmienne środowiskowe
├── README.md                 # Dokumentacja
├── routes/                   # Skrypty Groovy DSL
│   ├── edoreczenia.groovy    # Główne route'y
│   ├── send-document.groovy  # Wysyłanie dokumentów
│   └── receive-messages.groovy # Odbieranie wiadomości
└── src/
    └── main/
        ├── groovy/
        │   └── pl/edoreczenia/dsl/
        │       ├── EDoreczeniaApp.groovy    # Aplikacja główna
        │       └── EDoreczeniaRoutes.groovy # Route'y Camel
        └── resources/
            └── logback.xml   # Konfiguracja logowania
```

## Licencja

MIT
