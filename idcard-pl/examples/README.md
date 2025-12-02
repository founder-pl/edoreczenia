# IDCard.pl - Przykłady użycia API

## Szybki start

```bash
# 1. Nadaj uprawnienia
chmod +x *.sh

# 2. Zarejestruj się
./01_register.sh test@example.com testpass123 "Jan Kowalski"

# 3. Zobacz dostępne usługi
./03_list_services.sh

# 4. Połącz z e-Doręczenia (szyfromat.pl)
./04_connect_edoreczenia.sh "AE:PL-TWOJ-ADRES-1234-01" oauth2

# 5. Zobacz dashboard
./05_dashboard.sh

# 6. Zunifikowana skrzynka
./06_unified_inbox.sh
```

## Lista skryptów

| Skrypt | Opis |
|--------|------|
| `01_register.sh` | Rejestracja nowego użytkownika |
| `02_login.sh` | Logowanie |
| `03_list_services.sh` | Lista dostępnych usług |
| `04_connect_edoreczenia.sh` | Połączenie z e-Doręczenia |
| `05_dashboard.sh` | Dashboard użytkownika |
| `06_unified_inbox.sh` | Zunifikowana skrzynka odbiorcza |

## Architektura

```
┌─────────────────────────────────────────────────────────────┐
│                      IDCard.pl                              │
│                   (idcard.pl:4000)                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Integration Gateway                     │   │
│  │                                                      │   │
│  │  • Zunifikowana autentykacja                        │   │
│  │  • Agregacja wiadomości                             │   │
│  │  • Centralne powiadomienia                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│         ┌────────────────┼────────────────┐                │
│         │                │                │                │
│         ▼                ▼                ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │ e-Doręczenia│  │   ePUAP     │  │    KSeF     │        │
│  │szyfromat.pl │  │   gov.pl    │  │  mf.gov.pl  │        │
│  │   :8500     │  │  (wkrótce)  │  │  (wkrótce)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Domeny docelowe

| Usługa | Domena | Port (dev) |
|--------|--------|------------|
| IDCard.pl Gateway | idcard.pl | 4000 |
| IDCard.pl Frontend | idcard.pl | 4100 |
| Szyfromat.pl (e-Doręczenia) | szyfromat.pl | 8500 |
