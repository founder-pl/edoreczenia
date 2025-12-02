#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 21_oauth_connect.sh - Połączenie przez OAuth2 (oficjalne API)
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:8500}"
REDIRECT_URI="${REDIRECT_URI:-http://localhost:3500/callback}"

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
        echo "Użycie: ./21_oauth_connect.sh <CONNECTION_ID>"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Połączenie przez OAuth2 (Oficjalne API e-Doręczeń)          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Pobierz URL autoryzacji
echo "Krok 1: Pobieranie URL autoryzacji..."
echo "─────────────────────────────────────────────────────────────"

RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/oauth/authorize?redirect_uri=$REDIRECT_URI" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESPONSE" | grep -q '"authorization_url"'; then
    AUTH_URL=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['authorization_url'])")
    STATE=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['state'])")
    
    echo "✓ URL autoryzacji wygenerowany"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Krok 2: Autoryzacja w przeglądarce"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "Otwórz poniższy URL w przeglądarce:"
    echo ""
    echo "  $AUTH_URL"
    echo ""
    echo "Instrukcje:"
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for i, step in enumerate(data['instructions'], 1):
    print(f'  {i}. {step}')
"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Krok 3: Wprowadź kod autoryzacji"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "Po zalogowaniu i wyrażeniu zgody, zostaniesz przekierowany"
    echo "na adres z parametrem 'code'. Skopiuj ten kod."
    echo ""
    read -p "Wprowadź kod autoryzacji: " AUTH_CODE
    
    if [ -n "$AUTH_CODE" ]; then
        echo ""
        echo "Wymieniam kod na tokeny..."
        
        CALLBACK_RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/oauth/callback?code=$AUTH_CODE" \
          -H "Authorization: Bearer $TOKEN")
        
        if echo "$CALLBACK_RESPONSE" | grep -q '"connected"'; then
            echo ""
            echo "✓ Połączenie OAuth2 zakończone pomyślnie!"
            echo ""
            echo "$CALLBACK_RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
conn = data.get('connection', {})
print(f'Status: {conn.get(\"status\", \"N/A\")}')
print(f'Połączono: {conn.get(\"connected_at\", \"N/A\")}')
"
            echo ""
            echo "Następny krok: ./25_sync_mailbox.sh $CONNECTION_ID"
        else
            echo "✗ Błąd autoryzacji!"
            echo "$CALLBACK_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CALLBACK_RESPONSE"
        fi
    fi
else
    echo "✗ Błąd pobierania URL autoryzacji!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
