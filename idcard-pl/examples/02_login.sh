#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 02_login.sh - Logowanie do IDCard.pl
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:4000}"

EMAIL="${1:-test@example.com}"
PASSWORD="${2:-testpass123}"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  IDCard.pl - Logowanie                                       ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Email: $EMAIL"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\"
  }")

if echo "$RESPONSE" | grep -q "access_token"; then
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    echo "$TOKEN" > /tmp/idcard_token.txt
    
    echo "✓ Logowanie pomyślne!"
    echo ""
    echo "Token zapisany do: /tmp/idcard_token.txt"
else
    echo "✗ Błąd logowania!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
fi
