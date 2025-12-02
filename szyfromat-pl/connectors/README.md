# Szyfromat.pl - Connectors

Moduły integracji Szyfromat.pl z zewnętrznymi usługami.

## Dostępne connectory

| Connector | Opis | Status |
|-----------|------|--------|
| **ADE** | Adresy e-Doręczeń (gov.pl) | ✅ Aktywny |
| **IMAP/SMTP** | Dostęp przez protokoły email | ✅ Aktywny |
| **Nextcloud** | Przechowywanie załączników | ✅ Aktywny |
| **IDCard.pl** | Gateway integracji | ✅ Aktywny |

## Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                      Szyfromat.pl                               │
│                   (e-Doręczenia SaaS)                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ ADE         │  │ IMAP/SMTP   │  │ Nextcloud   │             │
│  │ Connector   │  │ Connector   │  │ Connector   │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│  ┌──────┴────────────────┴────────────────┴──────┐             │
│  │              Unified Message Store             │             │
│  └───────────────────────┬───────────────────────┘             │
│                          │                                      │
└──────────────────────────┼──────────────────────────────────────┘
                           │
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
   ┌───────────┐    ┌───────────┐    ┌───────────┐
   │ e-Doręcz. │    │  Email    │    │ Nextcloud │
   │  gov.pl   │    │  Server   │    │  Cloud    │
   └───────────┘    └───────────┘    └───────────┘
```

## Konfiguracja (.env)

```env
# ADE Connector
ADE_API_URL=https://edoreczenia.gov.pl/api
ADE_CLIENT_ID=your_client_id
ADE_CLIENT_SECRET=your_client_secret

# IMAP/SMTP Connector
IMAP_HOST=imap.szyfromat.pl
IMAP_PORT=993
SMTP_HOST=smtp.szyfromat.pl
SMTP_PORT=587

# Nextcloud Connector
NEXTCLOUD_URL=http://localhost:8080
NEXTCLOUD_USER=admin
NEXTCLOUD_PASSWORD=admin
NEXTCLOUD_FOLDER=/e-Doreczenia

# IDCard.pl Gateway
IDCARD_API_URL=http://localhost:4000
```

## Użycie

### ADE Connector
```python
from connectors.ade import ADEConnector

ade = ADEConnector()
ade.connect("AE:PL-JAN-KOWAL-1234-01")
messages = ade.fetch_messages()
```

### IMAP/SMTP Connector
```python
from connectors.imap import IMAPConnector

imap = IMAPConnector()
imap.connect("user@szyfromat.pl", "password")
messages = imap.fetch_inbox()
```

### Nextcloud Connector
```python
from connectors.nextcloud import NextcloudConnector

nc = NextcloudConnector()
nc.upload_attachment(message_id, file_path)
nc.download_attachment(message_id, attachment_id)
```
