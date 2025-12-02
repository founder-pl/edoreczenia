#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 05_dashboard.sh - Dashboard użytkownika
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:4000}"

# Pobierz token
if [ -z "$TOKEN" ]; then
    if [ -f /tmp/idcard_token.txt ]; then
        TOKEN=$(cat /tmp/idcard_token.txt)
    else
        echo "Brak tokenu! Najpierw uruchom: ./02_login.sh"
        exit 1
    fi
fi

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  IDCard.pl - Dashboard                                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

curl -s "$API_URL/api/dashboard" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json

data = json.load(sys.stdin)
stats = data.get('stats', {})
user = data.get('user', {})

print('UŻYTKOWNIK')
print('─' * 60)
print(f'  Nazwa: {user.get(\"name\", \"N/A\")}')
print(f'  Email: {user.get(\"email\", \"N/A\")}')
print('')

print('STATYSTYKI')
print('─' * 60)
print(f'  Połączenia ogółem: {stats.get(\"total_connections\", 0)}')
print(f'  Aktywne połączenia: {stats.get(\"active_connections\", 0)}')
print('')

services = stats.get('services', {})
if services:
    print('POŁĄCZONE USŁUGI')
    print('─' * 60)
    for name, info in services.items():
        status_icon = '🟢' if info.get('status') == 'active' else '🟡'
        print(f'  {status_icon} {name}')
        print(f'     Adres: {info.get(\"address\", \"N/A\")}')
        print(f'     Nieprzeczytane: {info.get(\"unread_messages\", 0)}')
        print('')

activity = data.get('recent_activity', [])
if activity:
    print('OSTATNIA AKTYWNOŚĆ')
    print('─' * 60)
    for a in activity[:5]:
        print(f'  • {a.get(\"title\", \"\")}')
        print(f'    [{a.get(\"service\", \"\")}] {a.get(\"time\", \"\")}')
        print('')
"
