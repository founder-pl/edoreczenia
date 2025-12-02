#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 26_list_mailboxes.sh - Lista połączonych skrzynek
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

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Lista połączonych skrzynek e-Doręczeń                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

RESPONSE=$(curl -s "$API_URL/api/mailbox/connections" \
  -H "Authorization: Bearer $TOKEN")

echo "$RESPONSE" | python3 -c "
import sys, json

connections = json.load(sys.stdin)
print(f'Znaleziono: {len(connections)} połączonych skrzynek')
print('')

if not connections:
    print('  (brak połączonych skrzynek)')
    print('')
    print('Aby podłączyć skrzynkę:')
    print('  ./20_connect_mailbox.sh <ADRES_ADE>')
else:
    for i, conn in enumerate(connections, 1):
        status_icon = {
            'connected': '🟢',
            'active': '🟢',
            'syncing': '🔵',
            'pending': '🟡',
            'connecting': '🟡',
            'error': '🔴',
            'disconnected': '⚪'
        }.get(conn.get('status', ''), '❓')
        
        method_icon = {
            'oauth2': '🔐',
            'mobywatel': '📱',
            'certificate': '📜',
            'api_key': '🔑'
        }.get(conn.get('connection_method', ''), '❓')
        
        print(f'{i}. {status_icon} {conn.get(\"mailbox_name\", \"Bez nazwy\")}')
        print(f'   ID: {conn[\"id\"]}')
        print(f'   Adres: {conn[\"ade_address\"]}')
        print(f'   Metoda: {method_icon} {conn.get(\"connection_method\", \"N/A\")}')
        print(f'   Status: {conn.get(\"status\", \"N/A\")}')
        print(f'   Typ: {conn.get(\"mailbox_type\", \"N/A\")}')
        
        if conn.get('messages_synced'):
            print(f'   Zsynchronizowano: {conn[\"messages_synced\"]} wiadomości')
        if conn.get('last_sync_at'):
            print(f'   Ostatnia sync: {conn[\"last_sync_at\"]}')
        if conn.get('last_error'):
            print(f'   ⚠️ Błąd: {conn[\"last_error\"]}')
        print('')
"

echo "─────────────────────────────────────────────────────────────"
echo "Akcje:"
echo "  ./25_sync_mailbox.sh <ID>     - Synchronizuj"
echo "  ./27_disconnect_mailbox.sh <ID> - Rozłącz"
echo "─────────────────────────────────────────────────────────────"
