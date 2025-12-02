#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 02_send_message.sh - Wysyłanie wiadomości e-Doręczeń
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:8500}"

# Pobierz token z pliku lub zmiennej
if [ -z "$TOKEN" ]; then
    if [ -f /tmp/edoreczenia_token.txt ]; then
        TOKEN=$(cat /tmp/edoreczenia_token.txt)
    else
        echo "Brak tokenu! Najpierw uruchom: ./01_login.sh"
        exit 1
    fi
fi

# Parametry wiadomości
RECIPIENT="${1:-AE:PL-URZAD-SKAR-BOWY-01}"
SUBJECT="${2:-Testowa wiadomość}"
CONTENT="${3:-Treść testowej wiadomości wysłanej przez API e-Doręczeń.}"

echo "═══════════════════════════════════════════════════════════════"
echo "  Wysyłanie wiadomości e-Doręczeń"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Odbiorca: $RECIPIENT"
echo "Temat: $SUBJECT"
echo ""

# Wysyłanie wiadomości
RESPONSE=$(curl -s -X POST "$API_URL/api/messages" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"recipient\": \"$RECIPIENT\",
    \"subject\": \"$SUBJECT\",
    \"content\": \"$CONTENT\",
    \"attachments\": []
  }")

# Sprawdź odpowiedź
if echo "$RESPONSE" | grep -q '"id"'; then
    echo "✓ Wiadomość wysłana pomyślnie!"
    echo ""
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'ID wiadomości: {data[\"id\"]}')
print(f'Status: {data[\"status\"]}')
print(f'Wysłano: {data.get(\"sentAt\", \"N/A\")}')
"
else
    echo "✗ Błąd wysyłania!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Użycie:"
echo "  ./02_send_message.sh [ODBIORCA] [TEMAT] [TREŚĆ]"
echo ""
echo "Przykłady:"
echo "  ./02_send_message.sh"
echo "  ./02_send_message.sh 'AE:PL-FIRMA-1234-5678-01' 'Zapytanie' 'Treść'"
echo "═══════════════════════════════════════════════════════════════"
