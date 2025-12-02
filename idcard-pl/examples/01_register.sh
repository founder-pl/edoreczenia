#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 01_register.sh - Rejestracja w IDCard.pl
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:4000}"

EMAIL="${1:-test@example.com}"
PASSWORD="${2:-testpass123}"
NAME="${3:-Jan Kowalski}"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  IDCard.pl - Rejestracja                                     ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""
echo "Email: $EMAIL"
echo "Nazwa: $NAME"
echo ""

RESPONSE=$(curl -s -X POST "$API_URL/api/auth/register" \
  -H "Content-Type: application/json" \
  -d "{
    \"email\": \"$EMAIL\",
    \"password\": \"$PASSWORD\",
    \"name\": \"$NAME\"
  }")

if echo "$RESPONSE" | grep -q "access_token"; then
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    echo "$TOKEN" > /tmp/idcard_token.txt
    
    echo "✓ Rejestracja pomyślna!"
    echo ""
    echo "Token zapisany do: /tmp/idcard_token.txt"
else
    echo "✗ Błąd rejestracji!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
fi
