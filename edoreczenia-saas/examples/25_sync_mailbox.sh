#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 25_sync_mailbox.sh - Synchronizacja skrzynki e-Doręczeń
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

if [ -z "$CONNECTION_ID" ]; then
    if [ -f /tmp/edoreczenia_connection_id.txt ]; then
        CONNECTION_ID=$(cat /tmp/edoreczenia_connection_id.txt)
        echo "Używam ID z ostatniego połączenia: $CONNECTION_ID"
    else
        echo "Użycie: ./25_sync_mailbox.sh <CONNECTION_ID>"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Synchronizacja skrzynki e-Doręczeń                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Sprawdź status połączenia
echo "Sprawdzanie statusu połączenia..."
CONNECTION=$(curl -s "$API_URL/api/mailbox/connections/$CONNECTION_ID" \
  -H "Authorization: Bearer $TOKEN")

if echo "$CONNECTION" | grep -q '"status"'; then
    STATUS=$(echo "$CONNECTION" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")
    ADE_ADDRESS=$(echo "$CONNECTION" | python3 -c "import sys,json; print(json.load(sys.stdin)['ade_address'])")
    MAILBOX_NAME=$(echo "$CONNECTION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mailbox_name', 'N/A'))")
    
    echo ""
    echo "Skrzynka: $MAILBOX_NAME"
    echo "Adres:    $ADE_ADDRESS"
    echo "Status:   $STATUS"
    echo ""
    
    if [ "$STATUS" != "connected" ] && [ "$STATUS" != "active" ]; then
        echo "⚠️  Skrzynka nie jest połączona. Najpierw wykonaj autoryzację."
        exit 1
    fi
else
    echo "✗ Nie można pobrać informacji o połączeniu"
    exit 1
fi

echo "─────────────────────────────────────────────────────────────"
echo "Rozpoczynanie synchronizacji..."
echo "─────────────────────────────────────────────────────────────"

RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/sync" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESPONSE" | grep -q '"syncing"' || echo "$RESPONSE" | grep -q '"status"'; then
    echo ""
    echo "✓ Synchronizacja rozpoczęta!"
    echo ""
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data.get(\"status\", \"N/A\")}')
print(f'Rozpoczęto: {data.get(\"started_at\", \"N/A\")}')
print(f'Wiadomość: {data.get(\"message\", \"\")}')
"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Synchronizacja pobiera:"
    echo "  📥 Nowe wiadomości odebrane"
    echo "  📤 Status wysłanych wiadomości"
    echo "  📎 Załączniki"
    echo "  ✅ Potwierdzenia odbioru (UPO/UPD)"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "Po zakończeniu synchronizacji możesz:"
    echo "  ./03_list_messages.sh inbox    - Zobacz odebrane"
    echo "  ./03_list_messages.sh sent     - Zobacz wysłane"
else
    echo "✗ Błąd synchronizacji!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
