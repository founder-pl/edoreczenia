# e-Doręczenia SaaS - Przykłady użycia API

Ten folder zawiera przykładowe skrypty bash do interakcji z API e-Doręczeń.

## Wymagania

- `curl` - do wykonywania zapytań HTTP
- `python3` - do parsowania JSON
- Uruchomiony backend na `http://localhost:8500`

## Szybki start

```bash
# 1. Nadaj uprawnienia do wykonywania
chmod +x *.sh

# 2. Uruchom pełną demonstrację
./11_full_demo.sh

# Lub krok po kroku:
./01_login.sh
./02_send_message.sh
./03_list_messages.sh sent
```

## Lista skryptów

| Skrypt | Opis |
|--------|------|
| `01_login.sh` | Logowanie do systemu |
| `02_send_message.sh` | Wysyłanie wiadomości |
| `03_list_messages.sh` | Lista wiadomości w folderze |
| `04_get_message.sh` | Szczegóły wiadomości |
| `05_create_integration.sh` | Tworzenie integracji adresu |
| `06_verify_integration.sh` | Weryfikacja integracji |
| `07_complete_integration.sh` | Zakończenie integracji |
| `08_list_integrations.sh` | Lista integracji |
| `09_cqrs_stats.sh` | Statystyki CQRS/Event Store |
| `10_event_log.sh` | Log zdarzeń |
| `11_full_demo.sh` | Pełna demonstracja |

## Konfiguracja

Możesz zmienić domyślne ustawienia przez zmienne środowiskowe:

```bash
# Zmień URL API
export API_URL="http://localhost:8500"

# Zmień dane logowania
export USERNAME="testuser"
export PASSWORD="testpass123"

# Lub przy wywołaniu
API_URL="http://api.example.com" ./01_login.sh
```

## Przykłady użycia

### 1. Logowanie

```bash
./01_login.sh
# Token zostanie zapisany do /tmp/edoreczenia_token.txt
```

### 2. Wysyłanie wiadomości

```bash
# Domyślna wiadomość
./02_send_message.sh

# Z parametrami
./02_send_message.sh "AE:PL-FIRMA-1234-5678-01" "Temat wiadomości" "Treść wiadomości"
```

### 3. Przeglądanie wiadomości

```bash
# Skrzynka odbiorcza
./03_list_messages.sh inbox

# Wysłane
./03_list_messages.sh sent

# Archiwum (5 ostatnich)
./03_list_messages.sh archive 5
```

### 4. Szczegóły wiadomości

```bash
./04_get_message.sh msg-abc12345
```

### 5. Integracja adresu e-Doręczeń

```bash
# Utwórz integrację (osoba fizyczna)
./05_create_integration.sh "AE:PL-OSOBA-1234-5678-01" certum mobywatel person 12345678901

# Utwórz integrację (firma)
./05_create_integration.sh "AE:PL-FIRMA-1234-5678-01" poczta_polska podpis_kwalifikowany company 1234567890

# Weryfikuj
./06_verify_integration.sh int-abc12345

# Zakończ
./07_complete_integration.sh int-abc12345
```

### 6. CQRS i Event Sourcing

```bash
# Statystyki
./09_cqrs_stats.sh

# Log zdarzeń
./10_event_log.sh 50
```

## Struktura odpowiedzi

### Wiadomość

```json
{
  "id": "msg-abc12345",
  "subject": "Temat wiadomości",
  "sender": {
    "address": "AE:PL-1234-5678-ABCD-01",
    "name": "Jan Kowalski"
  },
  "recipient": {
    "address": "AE:PL-URZAD-SKAR-BOWY-01"
  },
  "status": "SENT",
  "sentAt": "2024-01-15T10:30:00",
  "content": "Treść wiadomości..."
}
```

### Integracja

```json
{
  "id": "int-abc12345",
  "ade_address": "AE:PL-1234-5678-ABCD-01",
  "status": "active",
  "provider": "certum",
  "entity_type": "person",
  "created_at": "2024-01-15T10:00:00",
  "verified_at": "2024-01-15T10:05:00"
}
```

## Statusy

### Wiadomości

| Status | Opis |
|--------|------|
| `DRAFT` | Wersja robocza |
| `SENT` | Wysłana |
| `RECEIVED` | Odebrana |
| `READ` | Przeczytana |
| `ARCHIVED` | Zarchiwizowana |

### Integracje

| Status | Opis |
|--------|------|
| `pending` | Oczekuje na weryfikację |
| `verifying` | W trakcie weryfikacji |
| `active` | Aktywna |
| `failed` | Nieudana |

## Troubleshooting

### Błąd "Brak tokenu"

```bash
# Zaloguj się ponownie
./01_login.sh
```

### Błąd połączenia

```bash
# Sprawdź czy backend działa
curl http://localhost:8500/health

# Sprawdź logi
docker-compose logs backend
```

### Błąd autoryzacji (401)

```bash
# Token wygasł, zaloguj się ponownie
./01_login.sh
```
