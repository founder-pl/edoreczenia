#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# 01_login.sh - Logowanie do systemu e-Doręczeń
# ═══════════════════════════════════════════════════════════════

API_URL="${API_URL:-http://localhost:8500}"
USERNAME="${USERNAME:-testuser}"
PASSWORD="${PASSWORD:-testpass123}"

echo "═══════════════════════════════════════════════════════════════"
echo "  Logowanie do e-Doręczeń SaaS"
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "API URL: $API_URL"
echo "Username: $USERNAME"
echo ""

# Logowanie
RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"$USERNAME\",\"password\":\"$PASSWORD\"}")

# Sprawdź czy logowanie się powiodło
if echo "$RESPONSE" | grep -q "access_token"; then
    TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
    
    echo "✓ Logowanie pomyślne!"
    echo ""
    echo "Token JWT:"
    echo "$TOKEN"
    echo ""
    echo "Zapisz token do zmiennej środowiskowej:"
    echo "  export TOKEN=\"$TOKEN\""
    echo ""
    
    # Zapisz token do pliku tymczasowego
    echo "$TOKEN" > /tmp/edoreczenia_token.txt
    echo "Token zapisany do: /tmp/edoreczenia_token.txt"
else
    echo "✗ Błąd logowania!"
    echo "$RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$RESPONSE"
    exit 1
fi
