#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 03_list_messages.sh - Pobieranie listy wiadomości
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
FOLDER="${1:-inbox}"
LIMIT="${2:-10}"

echo "═══════════════════════════════════════════════════════════════"
echo "  Lista wiadomości - folder: $FOLDER"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Pobierz wiadomości
RESPONSE=$(curl -s "$API_URL/api/messages?folder=$FOLDER&limit=$LIMIT" \
  -H "Authorization: Bearer $TOKEN")

# Wyświetl wyniki
echo "$RESPONSE" | python3 -c "
import sys, json
from datetime import datetime

messages = json.load(sys.stdin)
print(f'Znaleziono: {len(messages)} wiadomości')
print('')

if not messages:
    print('  (brak wiadomości)')
else:
    for i, msg in enumerate(messages, 1):
        status_icon = {
            'RECEIVED': '📥',
            'READ': '📖',
            'SENT': '📤',
            'DRAFT': '📝',
            'ARCHIVED': '📦'
        }.get(msg.get('status', ''), '📧')
        
        sender = msg.get('sender', {})
        sender_name = sender.get('name', sender.get('address', 'Nieznany')) if sender else 'Nieznany'
        
        print(f'{i}. {status_icon} {msg[\"subject\"]}')
        print(f'   ID: {msg[\"id\"]}')
        print(f'   Od: {sender_name}')
        print(f'   Status: {msg.get(\"status\", \"N/A\")}')
        print('')
"

echo "═══════════════════════════════════════════════════════════════"
echo "Użycie:"
echo "  ./03_list_messages.sh [FOLDER] [LIMIT]"
echo ""
echo "Foldery: inbox, sent, drafts, trash, archive"
echo ""
echo "Przykłady:"
echo "  ./03_list_messages.sh inbox 20"
echo "  ./03_list_messages.sh sent"
echo "  ./03_list_messages.sh archive 5"
echo "═══════════════════════════════════════════════════════════════"
