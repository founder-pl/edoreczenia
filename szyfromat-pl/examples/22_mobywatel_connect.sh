#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 22_mobywatel_connect.sh - Połączenie przez mObywatel
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
        echo "Użycie: ./22_mobywatel_connect.sh <CONNECTION_ID>"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Połączenie przez mObywatel                                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Rozpocznij uwierzytelnienie
echo "Krok 1: Inicjalizacja uwierzytelnienia mObywatel..."
echo "─────────────────────────────────────────────────────────────"

RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/mobywatel/initiate" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESPONSE" | grep -q '"auth_code"'; then
    AUTH_CODE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['auth_code'])")
    QR_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['qr_code_url'])")
    DEEP_LINK=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['deep_link'])")
    EXPIRES=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['expires_in_seconds'])")
    
    echo "✓ Sesja uwierzytelnienia utworzona"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Krok 2: Uwierzytelnienie w aplikacji mObywatel"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "╭─────────────────────────────────────────────────────────────╮"
    echo "│                                                             │"
    echo "│   KOD WERYFIKACYJNY:  $AUTH_CODE                          │"
    echo "│                                                             │"
    echo "│   Ważny przez: $EXPIRES sekund                              │"
    echo "│                                                             │"
    echo "╰─────────────────────────────────────────────────────────────╯"
    echo ""
    echo "Instrukcje:"
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, step in enumerate(data['instructions'], 1):
    print(f'  {i}. {step}')
"
    echo ""
    echo "Alternatywnie:"
    echo "  - Zeskanuj kod QR: $QR_URL"
    echo "  - Lub otwórz deep link: $DEEP_LINK"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Krok 3: Potwierdzenie"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    read -p "Naciśnij ENTER po potwierdzeniu w mObywatel (lub wpisz kod weryfikacyjny): " VERIFICATION_CODE
    
    if [ -z "$VERIFICATION_CODE" ]; then
        VERIFICATION_CODE="confirmed"
    fi
    
    echo ""
    echo "Weryfikuję..."
    
    VERIFY_RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/mobywatel/verify?verification_code=$VERIFICATION_CODE" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$VERIFY_RESPONSE" | grep -q '"connected"'; then
        echo ""
        echo "✓ Połączenie przez mObywatel zakończone pomyślnie!"
        echo ""
        echo "$VERIFY_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
conn = data.get('connection', {})
print(f'Status: {conn.get(\"status\", \"N/A\")}')
print(f'Połączono: {conn.get(\"connected_at\", \"N/A\")}')
"
        echo ""
        echo "Następny krok: ./25_sync_mailbox.sh $CONNECTION_ID"
    else
        echo "✗ Błąd weryfikacji!"
        echo "$VERIFY_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$VERIFY_RESPONSE"
    fi
else
    echo "✗ Błąd inicjalizacji mObywatel!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
