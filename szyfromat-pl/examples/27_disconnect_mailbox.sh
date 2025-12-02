#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 27_disconnect_mailbox.sh - Rozłączenie/usunięcie skrzynki
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
ACTION="${2:-disconnect}"

if [ -z "$CONNECTION_ID" ]; then
    if [ -f /tmp/edoreczenia_connection_id.txt ]; then
        CONNECTION_ID=$(cat /tmp/edoreczenia_connection_id.txt)
        echo "Używam ID z ostatniego połączenia: $CONNECTION_ID"
    else
        echo "Użycie: ./27_disconnect_mailbox.sh <CONNECTION_ID> [disconnect|delete]"
        echo ""
        echo "Akcje:"
        echo "  disconnect - Rozłącz (zachowaj dane, można ponownie połączyć)"
        echo "  delete     - Usuń całkowicie (usuwa wszystkie dane)"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Rozłączanie skrzynki e-Doręczeń                             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Pobierz informacje o połączeniu
CONNECTION=$(curl -s "$API_URL/api/mailbox/connections/$CONNECTION_ID" \
  -H "Authorization: Bearer $TOKEN")

if echo "$CONNECTION" | grep -q '"ade_address"'; then
    ADE_ADDRESS=$(echo "$CONNECTION" | python3 -c "import sys,json; print(json.load(sys.stdin)['ade_address'])")
    MAILBOX_NAME=$(echo "$CONNECTION" | python3 -c "import sys,json; print(json.load(sys.stdin).get('mailbox_name', 'N/A'))")
    
    echo "Skrzynka: $MAILBOX_NAME"
    echo "Adres:    $ADE_ADDRESS"
    echo ""
else
    echo "✗ Połączenie nie znalezione"
    exit 1
fi

if [ "$ACTION" == "delete" ]; then
    echo "⚠️  UWAGA: Usunięcie jest nieodwracalne!"
    echo "   Wszystkie dane połączenia zostaną usunięte."
    echo ""
    read -p "Czy na pewno chcesz USUNĄĆ połączenie? (wpisz 'TAK'): " CONFIRM
    
    if [ "$CONFIRM" != "TAK" ]; then
        echo "Anulowano."
        exit 0
    fi
    
    RESPONSE=$(curl -s -X DELETE "$API_URL/api/mailbox/connections/$CONNECTION_ID" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$RESPONSE" | grep -q '"deleted"'; then
        echo ""
        echo "✓ Połączenie zostało usunięte"
        rm -f /tmp/edoreczenia_connection_id.txt
    else
        echo "✗ Błąd usuwania!"
        echo "$RESPONSE"
    fi
else
    echo "Rozłączanie zachowuje dane - możesz ponownie połączyć skrzynkę."
    echo ""
    read -p "Czy chcesz rozłączyć skrzynkę? (t/n): " CONFIRM
    
    if [ "$CONFIRM" != "t" ] && [ "$CONFIRM" != "T" ]; then
        echo "Anulowano."
        exit 0
    fi
    
    RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections/$CONNECTION_ID/disconnect" \
      -H "Authorization: Bearer $TOKEN")
    
    if echo "$RESPONSE" | grep -q '"disconnected"'; then
        echo ""
        echo "✓ Skrzynka została rozłączona"
        echo ""
        echo "Aby ponownie połączyć, użyj odpowiedniej metody autoryzacji:"
        echo "  ./21_oauth_connect.sh $CONNECTION_ID"
        echo "  ./22_mobywatel_connect.sh $CONNECTION_ID"
    else
        echo "✗ Błąd rozłączania!"
        echo "$RESPONSE"
    fi
fi
