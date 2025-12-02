#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 05_create_integration.sh - Tworzenie integracji adresu e-Doręczeń
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

# Parametry integracji
ADE_ADDRESS="${1:-AE:PL-FIRMA-1234-5678-01}"
PROVIDER="${2:-certum}"
AUTH_METHOD="${3:-mobywatel}"
ENTITY_TYPE="${4:-person}"
PESEL="${5:-12345678901}"

echo "═══════════════════════════════════════════════════════════════"
echo "  Tworzenie integracji adresu e-Doręczeń"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Adres ADE:    $ADE_ADDRESS"
echo "Dostawca:     $PROVIDER"
echo "Metoda auth:  $AUTH_METHOD"
echo "Typ podmiotu: $ENTITY_TYPE"
echo ""

# Przygotuj dane
if [ "$ENTITY_TYPE" == "person" ]; then
    DATA="{
        \"ade_address\": \"$ADE_ADDRESS\",
        \"provider\": \"$PROVIDER\",
        \"auth_method\": \"$AUTH_METHOD\",
        \"entity_type\": \"$ENTITY_TYPE\",
        \"pesel\": \"$PESEL\"
    }"
else
    NIP="${6:-1234567890}"
    DATA="{
        \"ade_address\": \"$ADE_ADDRESS\",
        \"provider\": \"$PROVIDER\",
        \"auth_method\": \"$AUTH_METHOD\",
        \"entity_type\": \"$ENTITY_TYPE\",
        \"nip\": \"$NIP\"
    }"
fi

# Utwórz integrację
RESPONSE=$(curl -s -X POST "$API_URL/api/address-integrations" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "$DATA")

# Sprawdź odpowiedź
if echo "$RESPONSE" | grep -q '"id"'; then
    echo "✓ Integracja utworzona!"
    echo ""
    
    INTEGRATION_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "$INTEGRATION_ID" > /tmp/edoreczenia_integration_id.txt
    
    echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'ID integracji: {data[\"id\"]}')
print(f'Status: {data[\"status\"]}')
print(f'Wiadomość: {data.get(\"message\", \"\")}')
"
    echo ""
    echo "ID zapisane do: /tmp/edoreczenia_integration_id.txt"
    echo ""
    echo "Następne kroki:"
    echo "  1. ./06_verify_integration.sh $INTEGRATION_ID"
    echo "  2. ./07_complete_integration.sh $INTEGRATION_ID"
else
    echo "✗ Błąd tworzenia integracji!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Użycie:"
echo "  ./05_create_integration.sh [ADE_ADDRESS] [PROVIDER] [AUTH_METHOD] [ENTITY_TYPE] [PESEL/NIP]"
echo ""
echo "Przykłady:"
echo "  # Osoba fizyczna"
echo "  ./05_create_integration.sh 'AE:PL-OSOBA-1234-5678-01' certum mobywatel person 12345678901"
echo ""
echo "  # Firma"
echo "  ./05_create_integration.sh 'AE:PL-FIRMA-1234-5678-01' poczta_polska podpis_kwalifikowany company 1234567890"
echo "═══════════════════════════════════════════════════════════════"
