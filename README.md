# e-Doręczenia - Integracja z protokołami pocztowymi

Monorepo zawierające dwa projekty do integracji systemu e-Doręczeń z protokołami pocztowymi IMAP/SMTP.

## 📁 Struktura projektu

```
edoreczenia/
├── edoreczenia-proxy-imap-smtp/    # Proxy IMAP/SMTP
├── edoreczenia-middleware-sync/     # Middleware synchronizujący
├── LICENSE
└── README.md
```

## 🎯 Projekty

### 1. [edoreczenia-proxy-imap-smtp](./edoreczenia-proxy-imap-smtp/)

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

### 2. [edoreczenia-middleware-sync](./edoreczenia-middleware-sync/)

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

## 📄 Licencja

MIT License - zobacz plik [LICENSE](LICENSE)

## 📚 Zasoby

- [Dokumentacja API e-Doręczeń](https://edoreczenia.poczta-polska.pl/)
- [RFC 3501 - IMAP4rev1](https://tools.ietf.org/html/rfc3501)
- [RFC 5321 - SMTP](https://tools.ietf.org/html/rfc5321)
