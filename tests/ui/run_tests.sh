#!/bin/bash
# ═══════════════════════════════════════════════════════════════
# Uruchomienie testów UI dla ekosystemu Founder.pl
# ═══════════════════════════════════════════════════════════════

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║  Founder.pl - Testy UI (Playwright)                          ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Sprawdź czy usługi działają
echo -e "${YELLOW}Sprawdzanie dostępności usług...${NC}"
echo ""

check_service() {
    local name=$1
    local url=$2
    if curl -s --max-time 3 "$url" > /dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $name"
        return 0
    else
        echo -e "  ${RED}❌${NC} $name"
        return 1
    fi
}

SERVICES_OK=true
check_service "Founder.pl" "http://localhost:5001/health" || SERVICES_OK=false
check_service "IDCard.pl" "http://localhost:4000/health" || SERVICES_OK=false
check_service "Szyfromat.pl" "http://localhost:8500/health" || SERVICES_OK=false
check_service "Detax.pl" "http://localhost:8005/health" || SERVICES_OK=false

echo ""

if [ "$SERVICES_OK" = false ]; then
    echo -e "${RED}Niektóre usługi nie działają. Uruchom: make up${NC}"
    exit 1
fi

# Sprawdź czy node_modules istnieje
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Instalowanie zależności...${NC}"
    npm install
    npx playwright install chromium
fi

# Uruchom testy
echo -e "${YELLOW}Uruchamianie testów...${NC}"
echo ""

if [ "$1" = "--headed" ]; then
    npx playwright test --headed
elif [ "$1" = "--debug" ]; then
    npx playwright test --debug
elif [ "$1" = "--ui" ]; then
    npx playwright test --ui
else
    npx playwright test
fi

EXIT_CODE=$?

echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✅ Wszystkie testy UI przeszły pomyślnie!                   ║${NC}"
    echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"
else
    echo -e "${RED}╔═══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║  ❌ Niektóre testy nie przeszły                               ║${NC}"
    echo -e "${RED}╚═══════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Aby zobaczyć raport: npm run report"
fi

exit $EXIT_CODE
