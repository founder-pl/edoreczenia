#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 10_event_log.sh - Log zdarzeń (Event Sourcing)
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

LIMIT="${1:-20}"

echo "═══════════════════════════════════════════════════════════════"
echo "  Log zdarzeń (Event Sourcing) - ostatnie $LIMIT"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Pobierz zdarzenia
RESPONSE=$(curl -s "$API_URL/api/cqrs/events?limit=$LIMIT" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | python3 -c "
import sys, json
from datetime import datetime

data = json.load(sys.stdin)
events = data.get('events', [])

print(f'Znaleziono: {len(events)} zdarzeń')
print('')

if not events:
    print('  (brak zdarzeń)')
else:
    for event in events:
        event_type = event.get('event_type', 'unknown')
        
        # Ikona dla typu zdarzenia
        icon = {
            'message.created': '📝',
            'message.sent': '📤',
            'message.received': '📥',
            'message.read': '👁️',
            'message.archived': '📦',
            'message.deleted': '🗑️',
            'message.moved': '📁',
            'user.logged_in': '🔑',
            'sync.started': '🔄',
            'sync.completed': '✅'
        }.get(event_type, '📌')
        
        timestamp = event.get('timestamp', '')
        if timestamp:
            try:
                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                timestamp = dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                pass
        
        print(f'{icon} {event_type}')
        print(f'   ID: {event.get(\"event_id\", \"N/A\")[:20]}...')
        print(f'   Aggregate: {event.get(\"aggregate_id\", \"N/A\")}')
        print(f'   Time: {timestamp}')
        print(f'   Version: {event.get(\"version\", 0)}')
        
        payload = event.get('payload', {})
        if payload:
            print(f'   Payload: {json.dumps(payload)[:60]}...')
        print('')
"

echo "═══════════════════════════════════════════════════════════════"
echo "Użycie:"
echo "  ./10_event_log.sh [LIMIT]"
echo ""
echo "Przykłady:"
echo "  ./10_event_log.sh 50"
echo "  ./10_event_log.sh 10"
echo "═══════════════════════════════════════════════════════════════"
