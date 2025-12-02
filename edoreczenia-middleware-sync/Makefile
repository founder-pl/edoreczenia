.PHONY: build up down logs test clean help simulator-logs sync-logs dovecot-logs status restart
.PHONY: all-up all-down all-status proxy-up proxy-down dsl-up dsl-down e2e-test up-detached

# Domyślny cel
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia Middleware Sync"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Komendy lokalne (ten projekt):"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia kontenery sync"
	@echo "  make down       - Zatrzymuje kontenery sync"
	@echo "  make logs       - Logi wszystkich kontenerów"
	@echo "  make test       - Uruchamia testy jednostkowe"
	@echo "  make status     - Status kontenerów"
	@echo "  make clean      - Czyści zasoby Docker"
	@echo "  make sync-once  - Jednorazowa synchronizacja"
	@echo ""
	@echo "Komendy wszystkich usług:"
	@echo "  make all-up     - Uruchamia WSZYSTKIE usługi (proxy + sync + dsl)"
	@echo "  make all-down   - Zatrzymuje WSZYSTKIE usługi"
	@echo "  make all-status - Status wszystkich usług"
	@echo "  make e2e-test   - Testy E2E całego systemu"
	@echo ""
	@echo "Komendy innych usług:"
	@echo "  make proxy-up   - Uruchamia proxy IMAP/SMTP"
	@echo "  make proxy-down - Zatrzymuje proxy IMAP/SMTP"
	@echo "  make dsl-up     - Uruchamia DSL"
	@echo "  make dsl-down   - Zatrzymuje DSL"
	@echo ""
	@echo "Logi poszczególnych serwisów:"
	@echo "  make simulator-logs  - Logi symulatora API"
	@echo "  make sync-logs       - Logi middleware sync"
	@echo "  make dovecot-logs    - Logi serwera IMAP"
	@echo ""
	@echo "Dane dostępowe (Sync):"
	@echo "  Webmail:     http://localhost:9180"
	@echo "  API Docs:    http://localhost:8280/docs"
	@echo "  IMAP:        localhost:21143"
	@echo "  User/Pass:   mailuser / mailpass123"

# Budowanie obrazów
build:
	docker-compose build

# Uruchomienie
up:
	docker-compose up --build
	@echo ""
	@echo "=== Serwisy uruchomione ==="
	@echo "Webmail:     http://localhost:9180"
	@echo "API Docs:    http://localhost:8280/docs"
	@echo "IMAP:        localhost:21143"
	@echo "User/Pass:   mailuser / mailpass123"
	@echo ""
	@echo "Synchronizacja uruchomi się automatycznie co minutę."

# Zatrzymanie
down:
	docker-compose down

# Logi wszystkich serwisów
logs:
	docker-compose logs -f

# Logi symulatora
simulator-logs:
	docker-compose logs -f edoreczenia-simulator

# Logi sync
sync-logs:
	docker-compose logs -f edoreczenia-sync

# Logi Dovecot
dovecot-logs:
	docker-compose logs -f dovecot

# Jednorazowa synchronizacja
sync-once:
	docker-compose exec edoreczenia-sync python -m edoreczenia_sync.main --once

# Status synchronizacji
sync-status:
	docker-compose exec edoreczenia-sync python -m edoreczenia_sync.main --status

# Uruchomienie testów
test:
	docker-compose --profile test up --build --abort-on-container-exit tests

# Debug mode z adminerem
debug:
	docker-compose --profile debug up -d
	@echo "Adminer dostępny: http://localhost:9001"

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
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp up-detached
	docker-compose up -d --build
	@$(MAKE) -C ../edoreczenia-dsl up-detached
	@echo ""
	@echo "✅ Wszystkie usługi uruchomione!"
	@$(MAKE) all-status

# Zatrzymaj wszystkie usługi
all-down:
	@echo "🛑 Zatrzymywanie wszystkich usług e-Doręczeń..."
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp down
	docker-compose down
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
	@docker-compose -f ../edoreczenia-proxy-imap-smtp/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 MIDDLEWARE SYNC (localhost:8280, :21143, :9180):"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"
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

# Proxy IMAP/SMTP
proxy-up:
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp up

proxy-down:
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp down

proxy-logs:
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp logs

proxy-status:
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp status

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
