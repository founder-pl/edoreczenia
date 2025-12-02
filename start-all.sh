#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Ekosystem Founder.pl - Start wszystkich usług
# ═══════════════════════════════════════════════════════════════

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Ekosystem Founder.pl - Uruchamianie usług                   ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Kolory
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Szyfromat.pl (e-Doręczenia SaaS)
echo -e "${YELLOW}[1/3] Uruchamianie Szyfromat.pl (e-Doręczenia)...${NC}"
cd "$SCRIPT_DIR/szyfromat-pl"
docker-compose up -d --build 2>&1 | tail -3
echo -e "${GREEN}✓ Szyfromat.pl uruchomiony${NC}"
echo ""

# 2. IDCard.pl (Gateway)
echo -e "${YELLOW}[2/3] Uruchamianie IDCard.pl (Gateway)...${NC}"
cd "$SCRIPT_DIR/idcard-pl"
docker-compose up -d --build 2>&1 | tail -3
echo -e "${GREEN}✓ IDCard.pl uruchomiony${NC}"
echo ""

# 3. Detax.pl (AI Asystent) - opcjonalnie
DETAX_DIR="/home/tom/github/founder-pl/detax"
if [ -d "$DETAX_DIR" ]; then
    echo -e "${YELLOW}[3/3] Uruchamianie Detax.pl (AI Asystent)...${NC}"
    cd "$DETAX_DIR"
    if [ -f "docker-compose.yml" ]; then
        docker-compose up -d 2>&1 | tail -3
        echo -e "${GREEN}✓ Detax.pl uruchomiony${NC}"
    else
        echo "  (brak docker-compose.yml)"
    fi
else
    echo -e "${YELLOW}[3/3] Detax.pl - pominięto (katalog nie istnieje)${NC}"
fi

echo ""
echo "═══════════════════════════════════════════════════════════════"
echo ""
echo "Usługi uruchomione:"
echo ""
echo "  Szyfromat.pl (e-Doręczenia SaaS):"
echo "    API:      http://localhost:8500"
echo "    Frontend: http://localhost:3500"
echo ""
echo "  IDCard.pl (Integration Gateway):"
echo "    API:      http://localhost:4000"
echo "    Frontend: http://localhost:4100"
echo ""
echo "  Detax.pl (AI Asystent):"
echo "    API:      http://localhost:8000"
echo "    Frontend: http://localhost:3000"
echo ""
echo "═══════════════════════════════════════════════════════════════"
