#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 04_get_message.sh - Pobieranie szczegółów wiadomości
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

MESSAGE_ID="${1:-}"

if [ -z "$MESSAGE_ID" ]; then
    echo "Użycie: ./04_get_message.sh <MESSAGE_ID>"
    echo ""
    echo "Przykład: ./04_get_message.sh msg-abc12345"
    exit 1
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  Szczegóły wiadomości: $MESSAGE_ID"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Pobierz wiadomość
RESPONSE=$(curl -s "$API_URL/api/messages/$MESSAGE_ID" \
  -H "Authorization: Bearer $TOKEN")

# Wyświetl szczegóły
echo "$RESPONSE" | python3 -c "
import sys, json

try:
    msg = json.load(sys.stdin)
    
    if 'detail' in msg:
        print(f'Błąd: {msg[\"detail\"]}')
        sys.exit(1)
    
    sender = msg.get('sender', {})
    recipient = msg.get('recipient', {})
    
    print(f'ID:        {msg.get(\"id\", \"N/A\")}')
    print(f'Temat:     {msg.get(\"subject\", \"N/A\")}')
    print(f'Status:    {msg.get(\"status\", \"N/A\")}')
    print('')
    print(f'Nadawca:   {sender.get(\"name\", \"\")} <{sender.get(\"address\", \"\")}>')
    print(f'Odbiorca:  {recipient.get(\"name\", \"\")} <{recipient.get(\"address\", \"\")}>')
    print('')
    print(f'Otrzymano: {msg.get(\"receivedAt\", \"N/A\")}')
    print(f'Wysłano:   {msg.get(\"sentAt\", \"N/A\")}')
    print('')
    print('─' * 60)
    print('TREŚĆ:')
    print('─' * 60)
    print(msg.get('content', '(brak treści)'))
    print('─' * 60)
    
    attachments = msg.get('attachments', [])
    if attachments:
        print('')
        print(f'ZAŁĄCZNIKI ({len(attachments)}):')
        for att in attachments:
            print(f'  - {att.get(\"filename\", \"\")} ({att.get(\"size\", 0)} bytes)')
except json.JSONDecodeError:
    print('Błąd parsowania odpowiedzi')
"
