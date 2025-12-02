#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 08_list_integrations.sh - Lista integracji adresów
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

echo "═══════════════════════════════════════════════════════════════"
echo "  Lista integracji adresów e-Doręczeń"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Pobierz integracje
RESPONSE=$(curl -s "$API_URL/api/address-integrations" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | python3 -c "
import sys, json

integrations = json.load(sys.stdin)
print(f'Znaleziono: {len(integrations)} integracji')
print('')

if not integrations:
    print('  (brak integracji)')
    print('')
    print('Utwórz nową integrację:')
    print('  ./05_create_integration.sh')
else:
    for i, integ in enumerate(integrations, 1):
        status_icon = {
            'active': '✓',
            'pending': '○',
            'verifying': '⏳',
            'failed': '✗'
        }.get(integ.get('status', ''), '?')
        
        status_color = {
            'active': '🟢',
            'pending': '🟡',
            'verifying': '🔵',
            'failed': '🔴'
        }.get(integ.get('status', ''), '⚪')
        
        print(f'{i}. {status_color} {integ[\"ade_address\"]}')
        print(f'   ID: {integ[\"id\"]}')
        print(f'   Status: {status_icon} {integ.get(\"status\", \"N/A\")}')
        print(f'   Dostawca: {integ.get(\"provider\", \"N/A\")}')
        print(f'   Utworzono: {integ.get(\"created_at\", \"N/A\")}')
        if integ.get('verified_at'):
            print(f'   Zweryfikowano: {integ[\"verified_at\"]}')
        print('')
"
