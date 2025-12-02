#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 24_apikey_connect.sh - Generowanie klucza API (dla systemów)
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
        echo "Użycie: ./24_apikey_connect.sh <CONNECTION_ID>"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Generowanie klucza API dla systemów zewnętrznych            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "⚠️  UWAGA: Klucz API jest przeznaczony dla systemów zewnętrznych"
echo "   (ERP, CRM, własne aplikacje) które potrzebują dostępu do"
echo "   skrzynki e-Doręczeń bez interakcji użytkownika."
echo ""
echo "─────────────────────────────────────────────────────────────"

read -p "Czy chcesz wygenerować klucz API? (t/n): " CONFIRM

if [ "$CONFIRM" != "t" ] && [ "$CONFIRM" != "T" ]; then
    echo "Anulowano."
    exit 0
fi

echo ""
echo "Generowanie klucza API..."
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/api-key" \
  -H "Authorization: Bearer $TOKEN")

if echo "$RESPONSE" | grep -q '"api_key"'; then
    API_KEY=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_key'])")
    API_SECRET=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['api_secret'])")
    
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  ⚠️  ZAPISZ TE DANE - NIE BĘDZIE MOŻNA ICH ODZYSKAĆ!         ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "API Key:    $API_KEY"
    echo "API Secret: $API_SECRET"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    echo "Użycie w systemach zewnętrznych:"
    echo "─────────────────────────────────────────────────────────────"
    echo ""
    echo "Header HTTP:"
    echo "  Authorization: Bearer $API_KEY:$API_SECRET"
    echo ""
    echo "Przykład curl:"
    echo "  curl -H \"Authorization: Bearer $API_KEY:$API_SECRET\" \\"
    echo "       $API_URL/api/messages"
    echo ""
    echo "Przykład Python:"
    echo "  import requests"
    echo "  headers = {'Authorization': f'Bearer $API_KEY:$API_SECRET'}"
    echo "  response = requests.get('$API_URL/api/messages', headers=headers)"
    echo ""
    echo "─────────────────────────────────────────────────────────────"
    
    # Zapisz do pliku (opcjonalnie)
    read -p "Zapisać dane do pliku? (t/n): " SAVE
    if [ "$SAVE" == "t" ] || [ "$SAVE" == "T" ]; then
        CREDS_FILE="/tmp/edoreczenia_api_credentials_$CONNECTION_ID.txt"
        echo "API_KEY=$API_KEY" > "$CREDS_FILE"
        echo "API_SECRET=$API_SECRET" >> "$CREDS_FILE"
        chmod 600 "$CREDS_FILE"
        echo "Zapisano do: $CREDS_FILE"
    fi
    
    echo ""
    echo "Następny krok: ./25_sync_mailbox.sh $CONNECTION_ID"
else
    echo "✗ Błąd generowania klucza API!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
