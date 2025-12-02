.PHONY: build up down logs test clean help status dev install

# Załaduj zmienne z .env
include .env
export

# Domyślne wartości (jeśli nie ma w .env)
BACKEND_PORT ?= 4000
FRONTEND_PORT ?= 4100
IDCARD_DOMAIN ?= localhost
DEMO_USER_EMAIL ?= demo@idcard.pl
DEMO_USER_PASSWORD ?= demo123

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
	@echo "  Frontend:  http://$(IDCARD_DOMAIN):$(FRONTEND_PORT)"
	@echo "  API:       http://$(IDCARD_DOMAIN):$(BACKEND_PORT)"
	@echo "  API Docs:  http://$(IDCARD_DOMAIN):$(BACKEND_PORT)/docs"
	@echo ""
	@echo "Demo konto:"
	@echo "  Email:    $(DEMO_USER_EMAIL)"
	@echo "  Hasło:    $(DEMO_USER_PASSWORD)"

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
	@echo "Backend: http://$(IDCARD_DOMAIN):$(BACKEND_PORT)"
	@echo "Frontend: http://$(IDCARD_DOMAIN):$(FRONTEND_PORT)"
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port $(BACKEND_PORT)

dev-frontend:
	cd frontend && npm run dev -- --port $(FRONTEND_PORT)

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
	@echo "  Frontend:  http://$(IDCARD_DOMAIN):$(FRONTEND_PORT)"
	@echo "  API:       http://$(IDCARD_DOMAIN):$(BACKEND_PORT)"
	@echo "  API Docs:  http://$(IDCARD_DOMAIN):$(BACKEND_PORT)/docs"
	@echo ""
	@echo "  Demo:      $(DEMO_USER_EMAIL) / $(DEMO_USER_PASSWORD)"
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
	@curl -s http://$(IDCARD_DOMAIN):$(BACKEND_PORT)/health | python3 -m json.tool
	@echo ""
	@echo "2. Login (demo):"
	@curl -s -X POST http://$(IDCARD_DOMAIN):$(BACKEND_PORT)/api/auth/login \
		-H "Content-Type: application/json" \
		-d '{"email":"$(DEMO_USER_EMAIL)","password":"$(DEMO_USER_PASSWORD)"}' | python3 -m json.tool
	@echo ""

# ═══════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════

cli-login:
	@./cli/idcard login -u $(DEMO_USER_EMAIL) -p $(DEMO_USER_PASSWORD)

cli-register:
	@./cli/idcard register

cli-connect:
	@./cli/idcard connect

cli-inbox:
	@./cli/idcard inbox

cli-status:
	@./cli/idcard status
