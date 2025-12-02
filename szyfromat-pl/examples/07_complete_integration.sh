#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 07_complete_integration.sh - Zakończenie integracji
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

# ID integracji
INTEGRATION_ID="${1:-}"

if [ -z "$INTEGRATION_ID" ]; then
    if [ -f /tmp/edoreczenia_integration_id.txt ]; then
        INTEGRATION_ID=$(cat /tmp/edoreczenia_integration_id.txt)
        echo "Używam ID z ostatniej integracji: $INTEGRATION_ID"
    else
        echo "Użycie: ./07_complete_integration.sh <INTEGRATION_ID>"
        exit 1
    fi
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  Zakończenie integracji: $INTEGRATION_ID"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Zakończ integrację
RESPONSE=$(curl -s -X POST "$API_URL/api/address-integrations/$INTEGRATION_ID/complete" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESPONSE" | grep -q '"status"'; then
    echo "✓ Integracja zakończona pomyślnie!"
    echo ""
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data.get(\"status\", \"N/A\")}')
print(f'Adres ADE: {data.get(\"ade_address\", \"N/A\")}')
print(f'Wiadomość: {data.get(\"message\", \"\")}')
"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Pobieranie poświadczeń..."
    echo ""
    
    curl -s "$API_URL/api/address-integrations/$INTEGRATION_ID/credentials" \
      -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'detail' in data:
        print(f'Błąd: {data[\"detail\"]}')
    else:
        print('Poświadczenia:')
        print(f'  OAuth Token: {data.get(\"oauth_token\", \"N/A\")[:20]}...')
        print(f'  Certificate: {data.get(\"certificate_thumbprint\", \"N/A\")[:20]}...')
        print(f'  API Key: {data.get(\"api_key\", \"N/A\")[:20]}...')
        print(f'  Wygasa: {data.get(\"expires_at\", \"N/A\")}')
except:
    print('Nie można pobrać poświadczeń')
"
else
    echo "✗ Błąd zakończenia integracji!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Integracja zakończona! Możesz teraz wysyłać wiadomości."
echo "  ./02_send_message.sh"
echo "═══════════════════════════════════════════════════════════════"
