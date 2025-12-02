#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 03_list_services.sh - Lista dostępnych usług
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:4000}"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  IDCard.pl - Dostępne usługi                                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

curl -s "$API_URL/api/services" | python3 -c "
import sys, json

data = json.load(sys.stdin)
services = data.get('services', [])

for s in services:
    status_icon = {
        'available': '🟢',
        'coming_soon': '🟡'
    }.get(s.get('status', ''), '⚪')
    
    print(f'{status_icon} {s[\"name\"]}')
    print(f'   Typ: {s[\"type\"]}')
    print(f'   Provider: {s[\"provider\"]}')
    print(f'   Status: {s[\"status\"]}')
    print(f'   {s[\"description\"]}')
    print('')
    print('   Funkcje:')
    for f in s.get('features', []):
        print(f'     ✓ {f}')
    print('')
    print('   Metody autoryzacji:', ', '.join(s.get('auth_methods', [])))
    print('')
    print('─' * 60)
    print('')
"
