# Ekosystem Founder.pl - Usługi Cyfrowe

Kompleksowe rozwiązanie do obsługi usług cyfrowych dla polskich przedsiębiorców.

## 🏗️ Architektura

```
┌─────────────────────────────────────────────────────────────────┐
│                     IDCard.pl (Gateway)                         │
│                Platforma Integracji Usług                       │
│                    localhost:4000/4100                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
        ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ Szyfromat.pl  │   │   Detax.pl    │   │   (Przyszłe)  │
│ e-Doręczenia  │   │  AI Asystent  │   │  ePUAP/KSeF   │
│ :8500/:3500   │   │  :8000/:3000  │   │               │
└───────────────┘   └───────────────┘   └───────────────┘
```

## 📁 Struktura projektu

```
edoreczenia/
├── idcard-pl/                      # Gateway integracji (idcard.pl)
├── szyfromat-pl/                   # e-Doręczenia SaaS (szyfromat.pl)
├── edoreczenia-proxy-imap-smtp/    # Middleware: Proxy IMAP/SMTP
├── edoreczenia-middleware-sync/    # Middleware: Synchronizacja
├── edoreczenia-dsl/                # Middleware: DSL
├── start-all.sh                    # Uruchom wszystko
├── stop-all.sh                     # Zatrzymaj wszystko
├── ECOSYSTEM.md                    # Dokumentacja ekosystemu
└── README.md
```

## 🚀 Szybki start

```bash
# Uruchom wszystkie usługi
./start-all.sh

# Lub pojedynczo:
cd szyfromat-pl && docker-compose up -d
cd idcard-pl && docker-compose up -d
```

## 🌐 Dostęp (środowisko deweloperskie)

| Usługa | API | Frontend | Domena docelowa |
|--------|-----|----------|----------------|
| IDCard.pl | http://localhost:4000 | http://localhost:4100 | idcard.pl |
| Szyfromat.pl | http://localhost:8500 | http://localhost:3500 | szyfromat.pl |
| Detax.pl | http://localhost:8000 | http://localhost:3000 | detax.pl |

## 🎯 Projekty

### 1. [idcard-pl](./idcard-pl/) - Gateway Integracji

**Platforma integracji usług cyfrowych (idcard.pl)**

- 🔗 Zunifikowany dostęp do wszystkich usług
- 👤 Wspólna autentykacja
- 📬 Zunifikowana skrzynka odbiorcza
- 🔔 Centralne powiadomienia

**Porty:** 4000 (API), 4100 (Frontend)

---

### 2. [szyfromat-pl](./szyfromat-pl/) - e-Doręczenia SaaS

**Pełna obsługa e-Doręczeń (szyfromat.pl)**

- 📧 Wysyłanie/odbieranie wiadomości urzędowych
- ✅ Potwierdzenia odbioru (UPO/UPD)
- 🔄 CQRS + Event Sourcing
- 💾 SQLite persistence

**Porty:** 8500 (API), 3500 (Frontend)

---

### 3. [edoreczenia-proxy-imap-smtp](./edoreczenia-proxy-imap-smtp/) - Middleware

**Most między protokołami IMAP/SMTP a REST API e-Doręczeń.**

Emuluje serwery IMAP i SMTP, tłumacząc komendy na wywołania REST API. Pozwala korzystać z e-Doręczeń przez standardowe klienty poczty (Thunderbird, Outlook, Apple Mail).

**Funkcjonalności:**
- Serwer IMAP4rev1 - emulacja protokołu IMAP
- Serwer SMTP - przyjmowanie i wysyłanie wiadomości
- OAuth2 - automatyczna obsługa tokenów
- Mapowanie folderów IMAP ↔ e-Doręczenia
- Synchronizacja flag (przeczytane, odpowiedziane)

**Uruchomienie:**
```bash
cd edoreczenia-proxy-imap-smtp
make up
```

**Porty:**
- IMAP: `1143`
- SMTP: `1025`
- Symulator API: `8080`
- Webmail: `9000`

---

### 4. [edoreczenia-middleware-sync](./edoreczenia-middleware-sync/)

**Middleware synchronizujący e-Doręczenia z istniejącą skrzynką IMAP.**

Cyklicznie pobiera wiadomości z e-Doręczeń i importuje je do lokalnego serwera IMAP (np. Dovecot, Exchange). Obsługuje synchronizację dwukierunkową.

**Funkcjonalności:**
- Synchronizacja e-Doręczenia → IMAP (pobieranie)
- Synchronizacja IMAP → e-Doręczenia (wysyłanie)
- Baza danych stanu synchronizacji (SQLite)
- Konfigurowalny interwał synchronizacji
- Mapowanie folderów

**Uruchomienie:**
```bash
cd edoreczenia-middleware-sync
make up
```

**Porty:**
- Dovecot IMAP: `1143`
- Symulator API: `8080`
- Webmail: `9000`

---

## 🔄 Porównanie projektów

| Cecha | Proxy IMAP/SMTP | Middleware Sync |
|-------|-----------------|-----------------|
| **Podejście** | Emulacja protokołów | Synchronizacja danych |
| **Serwer IMAP** | Wbudowany (emulowany) | Zewnętrzny (Dovecot, Exchange) |
| **Czas rzeczywisty** | Tak | Cyklicznie (konfigurowalny) |
| **Przechowywanie** | Brak (proxy) | Lokalny IMAP + SQLite |
| **Przypadek użycia** | Bezpośredni dostęp | Integracja z istniejącą infrastrukturą |

## 🧪 Symulator API e-Doręczeń

Oba projekty zawierają identyczny symulator REST API e-Doręczeń:

- **OAuth2** - `/oauth/token`
- **Wiadomości** - `GET/POST /ua/v5/{address}/messages`
- **Załączniki** - `GET /ua/v5/{address}/messages/{id}/attachments/{att_id}`
- **EPO** - `GET /ua/v5/{address}/messages/{id}/epo`
- **Swagger UI** - `http://localhost:8080/docs`

**Dane testowe:**
```
Client ID: test_client_id
Client Secret: test_client_secret
Test Address: AE:PL-12345-67890-ABCDE-12
```

## 🐳 Docker

Każdy projekt ma własny `docker-compose.yml` z pełną infrastrukturą:

```bash
# Proxy IMAP/SMTP
cd edoreczenia-proxy-imap-smtp && make up

# Middleware Sync
cd edoreczenia-middleware-sync && make up
```

## 📖 Dokumentacja

- [founder-pl/docs/ECOSYSTEM.md](https://github.com/founder-pl/founder-pl/blob/main/docs/ECOSYSTEM.md) - Dokumentacja ekosystemu
- [founder-pl/docs/ARCHITECTURE.md](https://github.com/founder-pl/founder-pl/blob/main/docs/ARCHITECTURE.md) - Architektura techniczna
- [docs/](docs/) - Dokumentacja techniczna tego repozytorium

## 🔗 Powiązane repozytoria

- [founder-pl/founder-pl](https://github.com/founder-pl/founder-pl) - Dokumentacja ekosystemu + strona www
- [founder-pl/detax](https://github.com/founder-pl/detax) - Detax.pl - AI Asystent

## 📄 Licencja

Apache 2.0 - zobacz plik [LICENSE](LICENSE)

## 📚 Zasoby

- [Dokumentacja API e-Doręczeń](https://edoreczenia.poczta-polska.pl/)
- [RFC 3501 - IMAP4rev1](https://tools.ietf.org/html/rfc3501)
- [RFC 5321 - SMTP](https://tools.ietf.org/html/rfc5321)
