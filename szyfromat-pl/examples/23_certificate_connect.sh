#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 23_certificate_connect.sh - Połączenie przez certyfikat kwalifikowany
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:8500}"

# Pobierz token
if [ -z "$TOKEN" ]; then
    if [ -f /tmp/edoreczenia_token.txt ]; then
        TOKEN=$(cat /tmp/edoreczenia_token.txt)
    else
        echo "Brak tokenu! Najpierw uruchom: ./01_login.sh"
        exit 1
    fi
fi

# ID połączenia
CONNECTION_ID="${1:-}"
CERT_FILE="${2:-}"

if [ -z "$CONNECTION_ID" ]; then
    if [ -f /tmp/edoreczenia_connection_id.txt ]; then
        CONNECTION_ID=$(cat /tmp/edoreczenia_connection_id.txt)
        echo "Używam ID z ostatniego połączenia: $CONNECTION_ID"
    else
        echo "Użycie: ./23_certificate_connect.sh <CONNECTION_ID> <CERT_FILE.p12>"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Połączenie przez certyfikat kwalifikowany                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

if [ -z "$CERT_FILE" ]; then
    echo "Obsługiwane formaty certyfikatów:"
    echo "  - .p12 / .pfx (PKCS#12)"
    echo "  - .pem (PEM encoded)"
    echo ""
    echo "Dostawcy certyfikatów kwalifikowanych:"
    echo "  - Certum (certyfikat.pl)"
    echo "  - KIR (Krajowa Izba Rozliczeniowa)"
    echo "  - PWPW (Polska Wytwórnia Papierów Wartościowych)"
    echo "  - Asseco"
    echo "  - CenCert"
    echo ""
    read -p "Podaj ścieżkę do pliku certyfikatu: " CERT_FILE
fi

if [ ! -f "$CERT_FILE" ]; then
    echo "✗ Plik certyfikatu nie istnieje: $CERT_FILE"
    exit 1
fi

echo "Plik certyfikatu: $CERT_FILE"
echo ""

# Hasło do certyfikatu
read -s -p "Podaj hasło do certyfikatu: " CERT_PASSWORD
echo ""

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "Przesyłanie certyfikatu..."
echo "─────────────────────────────────────────────────────────────"

# Konwertuj certyfikat do Base64
CERT_BASE64=$(base64 -w 0 "$CERT_FILE")

RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/certificate" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"certificate_data\": \"$CERT_BASE64\",
    \"certificate_password\": \"$CERT_PASSWORD\"
  }")

if echo "$RESPONSE" | grep -q '"connected"' || echo "$RESPONSE" | grep -q '"certificate_thumbprint"'; then
    echo ""
    echo "✓ Połączenie przez certyfikat zakończone pomyślnie!"
    echo ""
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data.get(\"status\", \"N/A\")}')
print(f'Thumbprint: {data.get(\"certificate_thumbprint\", \"N/A\")}')
print(f'Wygasa: {data.get(\"expires_at\", \"N/A\")}')
"
    echo ""
    echo "Następny krok: ./25_sync_mailbox.sh $CONNECTION_ID"
else
    echo "✗ Błąd połączenia przez certyfikat!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
