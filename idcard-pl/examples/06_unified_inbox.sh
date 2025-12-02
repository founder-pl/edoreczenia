#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 06_unified_inbox.sh - Zunifikowana skrzynka odbiorcza
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

LIMIT="${1:-20}"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  IDCard.pl - Zunifikowana skrzynka odbiorcza                 ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Wiadomości ze wszystkich połączonych usług:"
echo ""

curl -s "$API_URL/api/dashboard/unified-inbox?limit=$LIMIT" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json

data = json.load(sys.stdin)
messages = data.get('messages', [])

print(f'Znaleziono: {len(messages)} wiadomości')
print('')

if not messages:
    print('  (brak wiadomości)')
    print('')
    print('Połącz usługi aby zobaczyć wiadomości:')
    print('  ./04_connect_edoreczenia.sh <ADRES_ADE>')
else:
    for msg in messages:
        status_icon = '🔵' if msg.get('status') == 'unread' else '⚪'
        source_icon = msg.get('source_icon', '📧')
        
        print(f'{status_icon} {source_icon} {msg.get(\"subject\", \"(brak tematu)\")}')
        print(f'   Źródło: {msg.get(\"source\", \"N/A\")}')
        print(f'   Od: {msg.get(\"sender\", \"N/A\")}')
        print(f'   Data: {msg.get(\"received_at\", \"N/A\")}')
        if msg.get('preview'):
            print(f'   {msg[\"preview\"][:60]}...')
        print('')
"

echo "─────────────────────────────────────────────────────────────"
echo "Użycie: ./06_unified_inbox.sh [LIMIT]"
echo "─────────────────────────────────────────────────────────────"
