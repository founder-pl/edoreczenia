#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 20_connect_mailbox.sh - Podłączenie istniejącej skrzynki e-Doręczeń
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

# Parametry
ADE_ADDRESS="${1:-}"
CONNECTION_METHOD="${2:-oauth2}"
MAILBOX_NAME="${3:-Moja skrzynka}"
MAILBOX_TYPE="${4:-person}"

if [ -z "$ADE_ADDRESS" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  Podłączenie istniejącej skrzynki e-Doręczeń do SaaS         ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Użycie:"
    echo "  ./20_connect_mailbox.sh <ADRES_ADE> [METODA] [NAZWA] [TYP]"
    echo ""
    echo "Parametry:"
    echo "  ADRES_ADE  - Twój adres e-Doręczeń (np. AE:PL-12345-67890-ABCDE-01)"
    echo "  METODA     - Metoda połączenia: oauth2, mobywatel, certificate, api_key"
    echo "  NAZWA      - Nazwa skrzynki (opcjonalna)"
    echo "  TYP        - Typ: person, company, public_entity"
    echo ""
    echo "Przykłady:"
    echo "  # Osoba fizyczna przez OAuth2"
    echo "  ./20_connect_mailbox.sh 'AE:PL-12345-67890-ABCDE-01' oauth2 'Jan Kowalski' person"
    echo ""
    echo "  # Firma przez mObywatel"
    echo "  ./20_connect_mailbox.sh 'AE:PL-FIRMA-1234-5678-01' mobywatel 'Firma XYZ' company"
    echo ""
    echo "  # Urząd przez certyfikat"
    echo "  ./20_connect_mailbox.sh 'AE:PL-URZAD-GMINY-0001-01' certificate 'Urząd Gminy' public_entity"
    echo ""
    echo "Dostępne metody połączenia:"
    curl -s "$API_URL/api/mailbox/methods" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for m in data['methods']:
    rec = '⭐' if m['recommended'] else '  '
    print(f'  {rec} {m[\"id\"]:12} - {m[\"name\"]}')
"
    exit 0
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Podłączanie skrzynki e-Doręczeń                             ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Adres:  $ADE_ADDRESS"
echo "Metoda: $CONNECTION_METHOD"
echo "Nazwa:  $MAILBOX_NAME"
echo "Typ:    $MAILBOX_TYPE"
echo ""

# Utwórz połączenie
echo "─────────────────────────────────────────────────────────────"
echo "Krok 1: Tworzenie połączenia..."
echo "─────────────────────────────────────────────────────────────"

RESPONSE=$(curl -s -X POST "$API_URL/api/mailbox/connections" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"ade_address\": \"$ADE_ADDRESS\",
    \"connection_method\": \"$CONNECTION_METHOD\",
    \"mailbox_name\": \"$MAILBOX_NAME\",
    \"mailbox_type\": \"$MAILBOX_TYPE\"
  }")

if echo "$RESPONSE" | grep -q '"id"'; then
    CONNECTION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "$CONNECTION_ID" > /tmp/edoreczenia_connection_id.txt
    
    echo "✓ Połączenie utworzone!"
    echo "  ID: $CONNECTION_ID"
    echo "  Status: $(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])")"
    echo ""
    echo "ID zapisane do: /tmp/edoreczenia_connection_id.txt"
else
    echo "✗ Błąd tworzenia połączenia!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo "─────────────────────────────────────────────────────────────"
echo "Krok 2: Autoryzacja ($CONNECTION_METHOD)"
echo "─────────────────────────────────────────────────────────────"

case "$CONNECTION_METHOD" in
    oauth2)
        echo "Następny krok: ./21_oauth_connect.sh $CONNECTION_ID"
        ;;
    mobywatel)
        echo "Następny krok: ./22_mobywatel_connect.sh $CONNECTION_ID"
        ;;
    certificate)
        echo "Następny krok: ./23_certificate_connect.sh $CONNECTION_ID <plik.p12>"
        ;;
    api_key)
        echo "Następny krok: ./24_apikey_connect.sh $CONNECTION_ID"
        ;;
esac

echo ""
echo "═══════════════════════════════════════════════════════════════"
