# e-Doręczenia SaaS

Panel webowy SaaS do zarządzania korespondencją elektroniczną w ramach systemu e-Doręczeń.

## 🎯 Funkcjonalności

- **Panel wiadomości** - przeglądanie, wysyłanie i odbieranie korespondencji
- **Integracja z Proxy IMAP/SMTP** - dostęp przez standardowe protokoły pocztowe
- **Integracja z Middleware Sync** - synchronizacja z lokalnym serwerem IMAP
- **Integracja z DSL** - automatyzacja przepływów wiadomości
- **Nowoczesny UI** - React + TailwindCSS, wzorowany na stylu Poczty Polskiej

## 🖼️ Zrzuty ekranu

### Strona logowania
![Login](docs/login.png)

### Skrzynka odbiorcza
![Inbox](docs/inbox.png)

### Podgląd wiadomości
![Message](docs/message.png)

## 🚀 Szybki start

### Docker (zalecane)

```bash
# Uruchom SaaS
make up

# Panel:      http://localhost:3500
# Przewodnik: http://localhost:3500/guide
# API Docs:   http://localhost:8500/docs
```

### Tryb developerski

```bash
# 1. Zainstaluj zależności
make install

# 2. Uruchom w trybie dev
make dev
```

### Wszystkie usługi

```bash
# Uruchom wszystkie usługi e-Doręczeń
make all-up

# Status
make all-status
```

## 🔐 Dane logowania

| Użytkownik | Hasło | Opis |
|------------|-------|------|
| `testuser` | `testpass123` | Użytkownik Proxy |
| `mailuser` | `mailpass123` | Użytkownik Sync |
| `admin` | `admin123` | Administrator |

## 🌐 Dostępne usługi

| Usługa | URL | Opis |
|--------|-----|------|
| **SaaS Panel** | http://localhost:3500 | Panel webowy |
| **Przewodnik** | http://localhost:3500/guide | Jak założyć skrzynkę |
| **SaaS API** | http://localhost:8500/docs | Swagger API |
| **Proxy API** | http://localhost:8180/docs | Proxy IMAP/SMTP |
| **Sync API** | http://localhost:8280/docs | Middleware Sync |
| **DSL API** | http://localhost:8380/docs | DSL |

## 📁 Struktura projektu

```
edoreczenia-saas/
├── backend/                 # FastAPI Backend
│   ├── app/
│   │   └── main.py         # Główna aplikacja
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React Frontend
│   ├── src/
│   │   ├── components/     # Komponenty UI
│   │   ├── pages/          # Strony
│   │   ├── hooks/          # React hooks
│   │   ├── services/       # API services
│   │   └── styles/         # CSS/Tailwind
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── Makefile
└── README.md
```

## 🛠️ Komendy Make

```bash
# Developerskie
make install        # Instaluje zależności
make dev            # Uruchamia w trybie dev
make dev-backend    # Tylko backend
make dev-frontend   # Tylko frontend

# Docker
make build          # Buduje obrazy
make up             # Uruchamia kontenery
make down           # Zatrzymuje kontenery
make logs           # Pokazuje logi
make status         # Status kontenerów
make clean          # Czyści zasoby

# Wszystkie usługi
make all-up         # Uruchamia wszystko
make all-down       # Zatrzymuje wszystko
make all-status     # Status wszystkiego
```

## 🔗 Integracje

### Proxy IMAP/SMTP
Panel automatycznie łączy się z Proxy IMAP/SMTP na porcie 8180.
Umożliwia dostęp do e-Doręczeń przez standardowe klienty poczty.

### Middleware Sync
Integracja z Middleware Sync na porcie 8280.
Synchronizuje wiadomości z lokalnym serwerem IMAP (Dovecot).

### DSL
Połączenie z DSL na porcie 8380.
Umożliwia automatyzację przepływów i scenariusze testowe.

## 🎨 Technologie

### Backend
- **FastAPI** - nowoczesny framework Python
- **Pydantic** - walidacja danych
- **JWT** - autoryzacja
- **httpx** - klient HTTP async

### Frontend
- **React 18** - biblioteka UI
- **Vite** - bundler
- **TailwindCSS** - stylowanie
- **Lucide React** - ikony
- **React Router** - routing
- **Axios** - klient HTTP

## 📱 Responsywność

Panel jest w pełni responsywny i działa na:
- 💻 Desktop
- 📱 Tablet
- 📱 Mobile

## 🔒 Bezpieczeństwo

- JWT tokeny z czasem wygaśnięcia
- CORS skonfigurowany dla bezpieczeństwa
- Hasła nie są przechowywane w plain text
- Automatyczne wylogowanie przy wygaśnięciu sesji

## 📄 Licencja

MIT
