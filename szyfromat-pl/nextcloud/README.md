# Nextcloud Integration for Szyfromat.pl

Integracja Nextcloud z Szyfromat.pl do przechowywania załączników e-Doręczeń w chmurze.

## Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                      Szyfromat.pl                               │
│                   (e-Doręczenia SaaS)                           │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  Nextcloud Connector                     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Nextcloud                                 │
│                    (Cloud Storage)                              │
│                                                                 │
│  /e-Doreczenia/                                                │
│  ├── INBOX/                                                    │
│  │   ├── 2024-01/                                              │
│  │   │   ├── msg-abc123/                                       │
│  │   │   │   ├── dokument.pdf                                  │
│  │   │   │   └── zalacznik.docx                                │
│  │   │   └── msg-def456/                                       │
│  │   └── 2024-02/                                              │
│  ├── SENT/                                                     │
│  ├── DRAFTS/                                                   │
│  ├── ARCHIVE/                                                  │
│  └── TRASH/                                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Szybki start

```bash
# 1. Uruchom Nextcloud
docker-compose up -d

# 2. Otwórz Nextcloud
open http://localhost:8080

# 3. Zaloguj się
#    User: admin
#    Password: admin
```

## Konfiguracja

### .env

```env
# Nextcloud
NEXTCLOUD_PORT=8080
NEXTCLOUD_ADMIN_USER=admin
NEXTCLOUD_ADMIN_PASSWORD=admin

# Szyfromat.pl Integration
SZYFROMAT_API_URL=http://host.docker.internal:8500
SZYFROMAT_BASE_FOLDER=/e-Doreczenia

# Sync
SYNC_INTERVAL=300
```

## Struktura folderów

| Folder | Opis |
|--------|------|
| `/e-Doreczenia/INBOX` | Odebrane wiadomości |
| `/e-Doreczenia/SENT` | Wysłane wiadomości |
| `/e-Doreczenia/DRAFTS` | Wersje robocze |
| `/e-Doreczenia/ARCHIVE` | Archiwum |
| `/e-Doreczenia/TRASH` | Kosz |

## Sync Service

Usługa synchronizacji automatycznie:
- Pobiera załączniki z Szyfromat.pl
- Przesyła je do Nextcloud
- Organizuje w folderach według daty i ID wiadomości

```bash
# Logi sync service
docker-compose logs -f szyfromat-sync
```

## API

### Upload załącznika

```python
from connectors.nextcloud import NextcloudConnector

nc = NextcloudConnector()
nc.connect()

nc.upload_attachment(
    message_id="msg-abc123",
    filename="dokument.pdf",
    content=pdf_bytes,
    content_type="application/pdf"
)
```

### Download załącznika

```python
content = nc.download_attachment(
    message_id="msg-abc123",
    filename="dokument.pdf"
)
```

### Udostępnianie

```python
share_url = nc.create_share_link(
    message_id="msg-abc123",
    filename="dokument.pdf",
    expire_days=7
)
print(f"Link: {share_url}")
```

## CLI

```bash
# Szyfromat CLI z Nextcloud
szyfromat cloud status
szyfromat cloud upload msg-abc123 dokument.pdf
szyfromat cloud download msg-abc123 dokument.pdf
szyfromat cloud share msg-abc123 dokument.pdf
szyfromat cloud list msg-abc123
```

## Porty

| Usługa | Port |
|--------|------|
| Nextcloud | 8080 |
| Szyfromat.pl API | 8500 |
| Szyfromat.pl Frontend | 3500 |

## Demo

```
Nextcloud URL: http://localhost:8080
User: admin
Password: admin
```
