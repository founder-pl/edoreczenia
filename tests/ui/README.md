# Testy UI - Founder.pl Ecosystem

Testy interfejsu użytkownika dla ekosystemu Founder.pl używające Playwright.

## Wymagania

- Node.js 18+
- Docker (usługi muszą być uruchomione)
- Playwright

## Instalacja

```bash
cd tests/ui
npm install
npx playwright install chromium
```

## Uruchomienie testów

```bash
# Wszystkie testy
npm test

# Z widoczną przeglądarką
npm run test:headed

# Tryb debug
npm run test:debug

# Interaktywny UI
npm run test:ui

# Raport HTML
npm run report
```

## Struktura testów

| Test | Opis | Odpowiednik shell |
|------|------|-------------------|
| 01_ecosystem_status | Status usług | examples/02_check_status.sh |
| 02_idcard_registration | Rejestracja/logowanie | examples/03_register_idcard.sh |
| 03_services_connection | Połączenie z usługami | examples/04_connect_szyfromat.sh |
| 04_szyfromat_sso | Single Sign-On | - |
| 05_full_user_journey | Pełna ścieżka użytkownika | examples/07_full_demo.sh |
| 06_founder_website | Strona główna | - |

## Przed uruchomieniem

Upewnij się że wszystkie usługi działają:

```bash
cd /home/tom/github/founder-pl
make status
```

Wymagane usługi:
- Founder.pl: http://localhost:5000 (API: 5001)
- IDCard.pl: http://localhost:4100 (API: 4000)
- Szyfromat.pl: http://localhost:3500 (API: 8500)
- Detax.pl: http://localhost:3005 (API: 8005)
