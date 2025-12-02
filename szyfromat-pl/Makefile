.PHONY: build up down logs test clean help status dev install
.PHONY: all-up all-down all-status proxy-up sync-up dsl-up
.PHONY: cli-login cli-inbox cli-send cli-read cli-folders cli-status

# Domyślny cel
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia SaaS - Panel Webowy"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Komendy developerskie:"
	@echo "  make install    - Instaluje zależności (npm + pip)"
	@echo "  make dev        - Uruchamia w trybie developerskim"
	@echo "  make dev-backend  - Uruchamia tylko backend"
	@echo "  make dev-frontend - Uruchamia tylko frontend"
	@echo ""
	@echo "Komendy Docker:"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia kontenery"
	@echo "  make down       - Zatrzymuje kontenery"
	@echo "  make logs       - Pokazuje logi"
	@echo "  make status     - Status kontenerów"
	@echo "  make clean      - Czyści zasoby Docker"
	@echo ""
	@echo "Komendy wszystkich usług:"
	@echo "  make all-up     - Uruchamia WSZYSTKIE usługi"
	@echo "  make all-down   - Zatrzymuje WSZYSTKIE usługi"
	@echo "  make all-status - Status wszystkich usług"
	@echo ""
	@echo "CLI (Shell DSL):"
	@echo "  make cli-login  - Zaloguj się"
	@echo "  make cli-inbox  - Pokaż wiadomości"
	@echo "  make cli-send   - Wyślij wiadomość"
	@echo "  make cli-read   - Przeczytaj wiadomość"
	@echo "  make cli-folders - Pokaż foldery"
	@echo "  make cli-status - Status integracji"
	@echo ""
	@echo "Dane dostępowe:"
	@echo "  Panel SaaS:    http://localhost:3500"
	@echo "  Przewodnik:    http://localhost:3500/guide"
	@echo "  Backend API:   http://localhost:8500/docs"
	@echo "  Login:         testuser / testpass123"
	@echo "                 mailuser / mailpass123"

# Instalacja zależności
install:
	@echo "📦 Instalacja zależności..."
	cd frontend && npm install
	cd backend && pip install -r requirements.txt
	@echo "✅ Zależności zainstalowane"

# Tryb developerski
dev:
	@echo "🚀 Uruchamianie w trybie developerskim..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:3000"
	@make -j2 dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend:
	cd frontend && npm run dev

# Docker
build:
	docker-compose build

up:
	docker-compose up --build -d
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia SaaS uruchomiony!"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  Panel:      http://localhost:3500"
	@echo "  Przewodnik: http://localhost:3500/guide"
	@echo "  API Docs:   http://localhost:8500/docs"
	@echo ""
	@echo "  Login:      testuser / testpass123"
	@echo "              mailuser / mailpass123"
	@echo ""

down:
	docker-compose down

logs:
	docker-compose logs -f

status:
	docker-compose ps

clean:
	docker-compose down -v --rmi local
	rm -rf frontend/node_modules frontend/dist
	rm -rf backend/__pycache__

# ═══════════════════════════════════════════════════════════════
# KOMENDY WSZYSTKICH USŁUG
# ═══════════════════════════════════════════════════════════════

all-up:
	@echo "🚀 Uruchamianie wszystkich usług e-Doręczeń..."
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp up-detached
	@$(MAKE) -C ../edoreczenia-middleware-sync up-detached
	@$(MAKE) -C ../edoreczenia-dsl up-detached
	docker-compose up -d --build
	@echo ""
	@echo "✅ Wszystkie usługi uruchomione!"
	@$(MAKE) all-status

all-down:
	@echo "🛑 Zatrzymywanie wszystkich usług..."
	docker-compose down
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp down
	@$(MAKE) -C ../edoreczenia-middleware-sync down
	@$(MAKE) -C ../edoreczenia-dsl down
	@echo "✅ Wszystkie usługi zatrzymane"

all-status:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  STATUS WSZYSTKICH USŁUG e-Doręczeń"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 SaaS Panel (localhost:3000, :8000):"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 PROXY IMAP/SMTP (localhost:8180, :11143, :11025):"
	@docker-compose -f ../edoreczenia-proxy-imap-smtp/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 MIDDLEWARE SYNC (localhost:8280, :21143):"
	@docker-compose -f ../edoreczenia-middleware-sync/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 DSL (localhost:8380, :31143):"
	@docker-compose -f ../edoreczenia-dsl/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || echo "  (nie uruchomiony)"

# Komendy innych usług
proxy-up:
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp up

sync-up:
	@$(MAKE) -C ../edoreczenia-middleware-sync up

dsl-up:
	@$(MAKE) -C ../edoreczenia-dsl up

# Uruchomienie w tle
up-detached:
	docker-compose up -d --build

# ═══════════════════════════════════════════════════════════════
# CLI (Shell DSL)
# ═══════════════════════════════════════════════════════════════

cli-login:
	@python3 cli/edoreczenia-cli.py login -u testuser -p testpass123

cli-inbox:
	@python3 cli/edoreczenia-cli.py inbox

cli-sent:
	@python3 cli/edoreczenia-cli.py inbox -f sent

cli-send:
	@python3 cli/edoreczenia-cli.py send

cli-read:
	@echo "Użycie: python3 cli/edoreczenia-cli.py read <message_id>"
	@python3 cli/edoreczenia-cli.py inbox

cli-folders:
	@python3 cli/edoreczenia-cli.py folders

cli-status:
	@python3 cli/edoreczenia-cli.py status

cli-whoami:
	@python3 cli/edoreczenia-cli.py whoami

cli-health:
	@python3 cli/edoreczenia-cli.py health
