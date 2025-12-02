#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Ekosystem Founder.pl - Stop wszystkich usług
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Ekosystem Founder.pl - Zatrzymywanie usług                  ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 1. IDCard.pl
echo "[1/3] Zatrzymywanie IDCard.pl..."
cd "$SCRIPT_DIR/idcard-pl" && docker-compose down 2>/dev/null || true

# 2. Szyfromat.pl
echo "[2/3] Zatrzymywanie Szyfromat.pl..."
cd "$SCRIPT_DIR/szyfromat-pl" && docker-compose down 2>/dev/null || true

# 3. Detax.pl
DETAX_DIR="/home/tom/github/founder-pl/detax"
if [ -d "$DETAX_DIR" ]; then
    echo "[3/3] Zatrzymywanie Detax.pl..."
    cd "$DETAX_DIR" && docker-compose down 2>/dev/null || true
fi

echo ""
echo "✓ Wszystkie usługi zatrzymane"
