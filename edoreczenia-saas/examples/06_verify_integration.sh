#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 06_verify_integration.sh - Weryfikacja integracji
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
        echo "Użycie: ./06_verify_integration.sh <INTEGRATION_ID>"
        exit 1
    fi
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  Weryfikacja integracji: $INTEGRATION_ID"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# 1. Pobierz kroki weryfikacji
echo "Kroki weryfikacji:"
echo "─────────────────────────────────────────────────────────────"
curl -s "$API_URL/api/address-integrations/$INTEGRATION_ID/steps" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json

steps = json.load(sys.stdin)
for step in steps:
    status_icon = {
        'completed': '✓',
        'in_progress': '⏳',
        'pending': '○',
        'failed': '✗'
    }.get(step['status'], '?')
    
    print(f'{status_icon} Krok {step[\"step\"]}: {step[\"name\"]}')
    print(f'   Status: {step[\"status\"]}')
    print(f'   {step[\"description\"]}')
    if step.get('required_action'):
        print(f'   ⚠ Wymagana akcja: {step[\"required_action\"]}')
    print('')
"

# 2. Rozpocznij weryfikację
echo "─────────────────────────────────────────────────────────────"
echo "Rozpoczynam weryfikację..."
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/address-integrations/$INTEGRATION_ID/verify" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(f'Status: {data.get(\"status\", \"N/A\")}')
print(f'Wiadomość: {data.get(\"message\", \"\")}')
"

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo "Następny krok:"
echo "  ./07_complete_integration.sh $INTEGRATION_ID"
echo "═══════════════════════════════════════════════════════════════"
