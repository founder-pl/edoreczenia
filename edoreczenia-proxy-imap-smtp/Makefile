.PHONY: build up down logs test clean help simulator-logs proxy-logs status restart
.PHONY: all-up all-down all-status sync-up sync-down dsl-up dsl-down e2e-test

# Domyślny cel
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia Proxy IMAP/SMTP"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Komendy lokalne (ten projekt):"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia kontenery proxy"
	@echo "  make down       - Zatrzymuje kontenery proxy"
	@echo "  make logs       - Logi wszystkich kontenerów"
	@echo "  make test       - Uruchamia testy jednostkowe"
	@echo "  make status     - Status kontenerów"
	@echo "  make clean      - Czyści zasoby Docker"
	@echo ""
	@echo "Komendy wszystkich usług:"
	@echo "  make all-up     - Uruchamia WSZYSTKIE usługi (proxy + sync + dsl)"
	@echo "  make all-down   - Zatrzymuje WSZYSTKIE usługi"
	@echo "  make all-status - Status wszystkich usług"
	@echo "  make e2e-test   - Testy E2E całego systemu"
	@echo ""
	@echo "Komendy innych usług:"
	@echo "  make sync-up    - Uruchamia middleware-sync"
	@echo "  make sync-down  - Zatrzymuje middleware-sync"
	@echo "  make dsl-up     - Uruchamia DSL"
	@echo "  make dsl-down   - Zatrzymuje DSL"
	@echo ""
	@echo "Logi poszczególnych serwisów:"
	@echo "  make simulator-logs  - Logi symulatora API"
	@echo "  make proxy-logs      - Logi proxy IMAP/SMTP"
	@echo ""
	@echo "Dane dostępowe (Proxy):"
	@echo "  Webmail:     http://localhost:9080"
	@echo "  API Docs:    http://localhost:8180/docs"
	@echo "  IMAP:        localhost:11143"
	@echo "  SMTP:        localhost:11025"
	@echo "  User/Pass:   testuser / testpass123"

# Budowanie obrazów
build:
	docker-compose build

# Uruchomienie
up:
	docker-compose up --build
	@echo ""
	@echo "=== Serwisy uruchomione ==="
	@echo "Webmail:     http://localhost:9080"
	@echo "API Docs:    http://localhost:8180/docs"
	@echo "IMAP:        localhost:11143"
	@echo "SMTP:        localhost:11025"
	@echo "User/Pass:   testuser / testpass123"

# Zatrzymanie
down:
	docker-compose down

# Logi wszystkich serwisów
logs:
	docker-compose logs -f

# Logi symulatora
simulator-logs:
	docker-compose logs -f edoreczenia-simulator

# Logi proxy
proxy-logs:
	docker-compose logs -f edoreczenia-proxy

# Uruchomienie testów
test:
	docker-compose --profile test up --build --abort-on-container-exit tests

# Czyszczenie
clean:
	docker-compose down -v --rmi local
	docker system prune -f

# Restart
restart: down up

# Status
status:
	docker-compose ps

# ═══════════════════════════════════════════════════════════════
# KOMENDY WSZYSTKICH USŁUG
# ═══════════════════════════════════════════════════════════════

# Uruchom wszystkie usługi
all-up:
	@echo "🚀 Uruchamianie wszystkich usług e-Doręczeń..."
	docker-compose up -d --build
	@$(MAKE) -C ../edoreczenia-middleware-sync up-detached
	@$(MAKE) -C ../edoreczenia-dsl up-detached
	@echo ""
	@echo "✅ Wszystkie usługi uruchomione!"
	@$(MAKE) all-status

# Zatrzymaj wszystkie usługi
all-down:
	@echo "🛑 Zatrzymywanie wszystkich usług e-Doręczeń..."
	docker-compose down
	@$(MAKE) -C ../edoreczenia-middleware-sync down
	@$(MAKE) -C ../edoreczenia-dsl down
	@echo "✅ Wszystkie usługi zatrzymane"

# Status wszystkich usług
all-status:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  STATUS WSZYSTKICH USŁUG e-Doręczeń"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "📦 PROXY IMAP/SMTP (localhost:8180, :11143, :11025, :9080):"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 MIDDLEWARE SYNC (localhost:8280, :21143, :9180):"
	@docker-compose -f ../edoreczenia-middleware-sync/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 DSL (localhost:8380, :31143, :31025):"
	@docker-compose -f ../edoreczenia-dsl/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"

# Testy E2E całego systemu
e2e-test:
	@echo "🧪 Uruchamianie testów E2E..."
	@python3 ../test_e2e.py

# ═══════════════════════════════════════════════════════════════
# KOMENDY INNYCH USŁUG
# ═══════════════════════════════════════════════════════════════

# Middleware Sync
sync-up:
	@$(MAKE) -C ../edoreczenia-middleware-sync up

sync-down:
	@$(MAKE) -C ../edoreczenia-middleware-sync down

sync-logs:
	@$(MAKE) -C ../edoreczenia-middleware-sync logs

sync-status:
	@$(MAKE) -C ../edoreczenia-middleware-sync status

# DSL
dsl-up:
	@$(MAKE) -C ../edoreczenia-dsl up

dsl-down:
	@$(MAKE) -C ../edoreczenia-dsl down

dsl-logs:
	@$(MAKE) -C ../edoreczenia-dsl logs

dsl-test:
	@$(MAKE) -C ../edoreczenia-dsl test

dsl-status:
	@$(MAKE) -C ../edoreczenia-dsl status

# Uruchomienie w tle (dla all-up)
up-detached:
	docker-compose up -d --build
