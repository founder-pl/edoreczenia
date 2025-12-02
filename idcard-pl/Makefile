.PHONY: build up down logs test clean help status dev install

# ═══════════════════════════════════════════════════════════════
# POMOC
# ═══════════════════════════════════════════════════════════════

help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  IDCard.pl - Gateway Integracji Usług Cyfrowych"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Komendy developerskie:"
	@echo "  make install      - Instaluje zależności"
	@echo "  make dev          - Uruchamia w trybie developerskim"
	@echo "  make dev-backend  - Uruchamia tylko backend"
	@echo "  make dev-frontend - Uruchamia tylko frontend"
	@echo ""
	@echo "Komendy Docker:"
	@echo "  make build        - Buduje obrazy Docker"
	@echo "  make up           - Uruchamia kontenery"
	@echo "  make down         - Zatrzymuje kontenery"
	@echo "  make logs         - Pokazuje logi"
	@echo "  make status       - Status kontenerów"
	@echo "  make clean        - Czyści zasoby Docker"
	@echo ""
	@echo "Testy:"
	@echo "  make test         - Uruchamia testy"
	@echo "  make test-api     - Testuje API"
	@echo ""
	@echo "CLI:"
	@echo "  make cli-login    - Zaloguj się"
	@echo "  make cli-register - Zarejestruj użytkownika"
	@echo "  make cli-connect  - Połącz usługę"
	@echo "  make cli-inbox    - Pokaż skrzynkę"
	@echo ""
	@echo "Dostęp:"
	@echo "  Frontend:  http://localhost:4100"
	@echo "  API:       http://localhost:4000"
	@echo "  API Docs:  http://localhost:4000/docs"
	@echo ""
	@echo "Demo konto:"
	@echo "  Email:    demo@idcard.pl"
	@echo "  Hasło:    demo123"

# ═══════════════════════════════════════════════════════════════
# INSTALACJA
# ═══════════════════════════════════════════════════════════════

install:
	@echo "📦 Instalacja zależności..."
	cd frontend && npm install
	cd backend && pip install -r requirements.txt
	@echo "✅ Zależności zainstalowane"

# ═══════════════════════════════════════════════════════════════
# DEVELOPMENT
# ═══════════════════════════════════════════════════════════════

dev:
	@echo "🚀 Uruchamianie w trybie developerskim..."
	@echo "Backend: http://localhost:4000"
	@echo "Frontend: http://localhost:4100"
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 4000

dev-frontend:
	cd frontend && npm run dev -- --port 4100

# ═══════════════════════════════════════════════════════════════
# DOCKER
# ═══════════════════════════════════════════════════════════════

build:
	docker-compose build

up:
	docker-compose up --build -d
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  IDCard.pl uruchomiony!"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Frontend:  http://localhost:4100"
	@echo "  API:       http://localhost:4000"
	@echo "  API Docs:  http://localhost:4000/docs"
	@echo ""
	@echo "  Demo:      demo@idcard.pl / demo123"
	@echo ""

down:
	docker-compose down

logs:
	docker-compose logs -f

status:
	@echo "Status kontenerów IDCard.pl:"
	@docker-compose ps

clean:
	docker-compose down -v --rmi local
	@echo "✅ Zasoby Docker wyczyszczone"

# ═══════════════════════════════════════════════════════════════
# TESTY
# ═══════════════════════════════════════════════════════════════

test:
	@echo "🧪 Uruchamianie testów..."
	cd backend && python -m pytest tests/ -v

test-api:
	@echo "🧪 Testowanie API..."
	@echo ""
	@echo "1. Health check:"
	@curl -s http://localhost:4000/health | python3 -m json.tool
	@echo ""
	@echo "2. Login (demo):"
	@curl -s -X POST http://localhost:4000/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"email":"demo@idcard.pl","password":"demo123"}' | python3 -m json.tool
	@echo ""

# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

cli-login:
	@./cli/idcard login -u demo@idcard.pl -p demo123

cli-register:
	@./cli/idcard register

cli-connect:
	@./cli/idcard connect

cli-inbox:
	@./cli/idcard inbox

cli-status:
	@./cli/idcard status
