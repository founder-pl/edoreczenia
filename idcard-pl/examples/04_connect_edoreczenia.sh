#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 04_connect_edoreczenia.sh - Połączenie z e-Doręczenia (szyfromat.pl)
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:4000}"

# Pobierz token
if [ -z "$TOKEN" ]; then
    if [ -f /tmp/idcard_token.txt ]; then
        TOKEN=$(cat /tmp/idcard_token.txt)
    else
        echo "Brak tokenu! Najpierw uruchom: ./01_register.sh lub ./02_login.sh"
        exit 1
    fi
fi

ADE_ADDRESS="${1:-}"
AUTH_METHOD="${2:-oauth2}"

if [ -z "$ADE_ADDRESS" ]; then
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║  IDCard.pl - Połączenie z e-Doręczenia                       ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Użycie:"
    echo "  ./04_connect_edoreczenia.sh <ADRES_ADE> [METODA]"
    echo ""
    echo "Parametry:"
    echo "  ADRES_ADE - Twój adres e-Doręczeń (np. AE:PL-12345-67890-ABCDE-01)"
    echo "  METODA    - Metoda autoryzacji: oauth2, mobywatel, certificate"
    echo ""
    echo "Przykłady:"
    echo "  ./04_connect_edoreczenia.sh 'AE:PL-JAN-KOWALSKI-1234-01' oauth2"
    echo "  ./04_connect_edoreczenia.sh 'AE:PL-FIRMA-XYZ-5678-01' mobywatel"
    exit 0
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  IDCard.pl - Połączenie z e-Doręczenia (szyfromat.pl)            ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Adres e-Doręczeń: $ADE_ADDRESS"
echo "Metoda autoryzacji: $AUTH_METHOD"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/services/connect" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"service_type\": \"edoreczenia\",
    \"credentials\": {
      \"ade_address\": \"$ADE_ADDRESS\"
    },
    \"config\": {
      \"auth_method\": \"$AUTH_METHOD\",
      \"name\": \"IDCard Integration\"
    }
  }")

if echo "$RESPONSE" | grep -q "connection_id"; then
    echo "✓ Połączenie utworzone!"
    echo ""
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Connection ID: {data[\"connection_id\"]}')
print(f'External ID: {data.get(\"external_id\", \"N/A\")}')
print(f'Status: {data[\"status\"]}')
print('')
print('Następny krok:')
next_step = data.get('next_step', {})
print(f'  Akcja: {next_step.get(\"action\", \"N/A\")}')
print(f'  Metoda: {next_step.get(\"method\", \"N/A\")}')
print('')
print('Instrukcje:')
for i, instr in enumerate(next_step.get('instructions', []), 1):
    print(f'  {i}. {instr}')
"
    
    CONNECTION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['connection_id'])")
    echo "$CONNECTION_ID" > /tmp/idcard_connection_id.txt
    echo ""
    echo "Connection ID zapisane do: /tmp/idcard_connection_id.txt"
else
    echo "✗ Błąd połączenia!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
fi
