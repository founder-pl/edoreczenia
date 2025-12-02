#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 09_cqrs_stats.sh - Statystyki CQRS i Event Store
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
echo "  Statystyki CQRS i Event Store"
echo "═══════════════════════════════════════════════════════════════"
echo ""

# Pobierz statystyki
RESPONSE=$(curl -s "$API_URL/api/cqrs/stats" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | python3 -c "
import sys, json

data = json.load(sys.stdin)

print('EVENT STORE')
print('─────────────────────────────────────────────────────────────')
es = data.get('event_store', {})
print(f'  Storage:         {es.get(\"storage\", \"N/A\")}')
print(f'  Total events:    {es.get(\"total_events\", 0)}')
print(f'  Aggregates:      {es.get(\"aggregates_count\", 0)}')
print('')

event_types = es.get('event_types', {})
if event_types:
    print('  Event types:')
    for et, count in event_types.items():
        print(f'    - {et}: {count}')
print('')

print('PROJECTIONS')
print('─────────────────────────────────────────────────────────────')
proj = data.get('projections', {})
msg_proj = proj.get('messages', {})
print(f'  Messages total:  {msg_proj.get(\"total\", 0)}')
print('')
print('  By folder:')
by_folder = msg_proj.get('by_folder', {})
for folder, count in by_folder.items():
    icon = {
        'inbox': '📥',
        'sent': '📤',
        'drafts': '📝',
        'trash': '🗑️',
        'archive': '📦'
    }.get(folder, '📁')
    print(f'    {icon} {folder}: {count}')
print('')

folder_proj = proj.get('folders', {})
print(f'  Folders total:   {folder_proj.get(\"total\", 0)}')
"
