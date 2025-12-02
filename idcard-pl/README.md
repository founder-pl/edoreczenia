# IDCard.pl - Platforma Integracji Usług Cyfrowych

Platforma do integracji zewnętrznych usług cyfrowych dla firm i osób fizycznych.

## Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                        idcard.pl                                │
│              Platforma Integracji Usług Cyfrowych               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ e-Doręczenia│  │   ePUAP     │  │    KSeF     │             │
│  │(szyfromat.pl│  │             │  │  (faktury)  │             │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘             │
│         │                │                │                     │
│  ┌──────┴────────────────┴────────────────┴──────┐             │
│  │           Integration Gateway API             │             │
│  └───────────────────────┬───────────────────────┘             │
│                          │                                      │
│  ┌───────────────────────┴───────────────────────┐             │
│  │              Unified Dashboard                │             │
│  │    - Wszystkie usługi w jednym miejscu       │             │
│  │    - Wspólna autentykacja                    │             │
│  │    - Centralne powiadomienia                 │             │
│  └───────────────────────────────────────────────┘             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Integrowane usługi

| Usługa | Domena SaaS | Status | Opis |
|--------|-------------|--------|------|
| **e-Doręczenia** | szyfromat.pl | ✅ Aktywna | Elektroniczna korespondencja urzędowa |
| **ePUAP** | - | 🔄 Planowana | Elektroniczna Platforma Usług Administracji Publicznej |
| **KSeF** | - | 🔄 Planowana | Krajowy System e-Faktur |
| **mObywatel** | - | 🔄 Planowana | Cyfrowa tożsamość |
| **CEPiK** | - | 🔄 Planowana | Centralna Ewidencja Pojazdów i Kierowców |
| **CEIDG** | - | 🔄 Planowana | Centralna Ewidencja Działalności Gospodarczej |

## Szybki start

```bash
# 1. Najpierw uruchom Szyfromat.pl (e-Doręczenia SaaS)
cd ../szyfromat-pl
docker-compose up -d

# 2. Uruchom IDCard.pl
cd ../idcard-pl
docker-compose up -d

# 3. Otwórz dashboard
open http://localhost:4100
```

## Struktura projektu

```
idcard-pl/
├── backend/           # API Gateway (FastAPI)
├── frontend/          # Dashboard (React)
├── integrations/      # Moduły integracji
│   ├── edoreczenia/   # Integracja z szyfromat.pl
│   ├── epuap/         # Integracja z ePUAP
│   └── ksef/          # Integracja z KSeF
├── docker-compose.yml
├── .env               # Konfiguracja lokalna
└── README.md
```

## Demo konto (development)

```
Email:    demo@idcard.pl
Hasło:    demo123
```

Konfiguracja demo konta w `.env`:
```env
DEMO_USER_EMAIL=demo@idcard.pl
DEMO_USER_PASSWORD=demo123
DEMO_USER_NAME=Demo User
DEMO_USER_COMPANY=Demo Company Sp. z o.o.
```

## Konfiguracja (.env)

```env
# IDCard.pl
IDCARD_DOMAIN=idcard.pl
BACKEND_PORT=4000
FRONTEND_PORT=4100

# Demo użytkownik
DEMO_USER_EMAIL=demo@idcard.pl
DEMO_USER_PASSWORD=demo123

# Szyfromat.pl (e-Doręczenia SaaS)
SZYFROMAT_API_URL=http://localhost:8500
SZYFROMAT_CLIENT_ID=idcard_client
SZYFROMAT_CLIENT_SECRET=idcard_secret
```

## Domeny docelowe

| Usługa | Domena | Port (dev) |
|--------|--------|------------|
| IDCard.pl Gateway | idcard.pl | 4000 |
| IDCard.pl Frontend | idcard.pl | 4100 |
| Szyfromat.pl Backend | szyfromat.pl | 8500 |
| Szyfromat.pl Frontend | szyfromat.pl | 3500 |
