.PHONY: build up down logs test test-scenarios test-client clean help send receive sync show-report list-reports status restart
.PHONY: all-up all-down all-status proxy-up proxy-down sync-up sync-down e2e-test up-detached

# Domyślny cel
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia DSL - Apache Camel + Groovy + Python"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Komendy lokalne (ten projekt):"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia kontenery DSL"
	@echo "  make down       - Zatrzymuje kontenery DSL"
	@echo "  make logs       - Logi wszystkich kontenerów"
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
	@echo "  make proxy-up   - Uruchamia proxy IMAP/SMTP"
	@echo "  make proxy-down - Zatrzymuje proxy IMAP/SMTP"
	@echo "  make sync-up    - Uruchamia middleware-sync"
	@echo "  make sync-down  - Zatrzymuje middleware-sync"
	@echo ""
	@echo "Komendy testowe DSL:"
	@echo "  make test           - Szybki test DSL"
	@echo "  make test-scenarios - Pełne testy scenariuszowe (raporty MD)"
	@echo "  make send           - Wysyła testową wiadomość"
	@echo "  make receive        - Odbiera wiadomości"
	@echo ""
	@echo "Raporty Markdown:"
	@echo "  make show-report    - Wyświetl ostatni raport"
	@echo "  make list-reports   - Lista wszystkich raportów"
	@echo ""
	@echo "Dane dostępowe (DSL - unikalne porty):"
	@echo "  Symulator:   http://localhost:8380/docs"
	@echo "  IMAP:        localhost:31143 (mailuser/mailpass123)"
	@echo "  SMTP Proxy:  localhost:31025 (testuser/testpass123)"
	@echo "  Raporty:     ./logs/*.md"

# Budowanie
build:
	docker-compose build

# Uruchomienie
up:
	docker-compose up --build
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia DSL uruchomiony"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "  DSL API:     http://localhost:8090"
	@echo "  Symulator:   http://localhost:8180/docs"
	@echo ""
	@echo "  Przykład wysyłania:"
	@echo "    curl -X POST http://localhost:8090/api/v1/messages \\"
	@echo "      -H 'Content-Type: application/json' \\"
	@echo "      -d '{\"subject\":\"Test\",\"recipient\":\"AE:PL-...\",\"content\":\"Treść\"}'"

# Zatrzymanie
down:
	docker-compose down

# Logi
logs:
	docker-compose logs -f

# Logi DSL
dsl-logs:
	docker-compose logs -f edoreczenia-dsl

# Czyszczenie
clean:
	docker-compose down -v --rmi local
	rm -rf build/

# ═══════════════════════════════════════════════════════════════
# KOMENDY DSL (używają Python Client)
# ═══════════════════════════════════════════════════════════════

# Wysyłanie testowej wiadomości
send:
	@echo "📤 Wysyłanie testowej wiadomości..."
	@python3 -c "from python_client.client import EDoreczeniaClient; from python_client.logger import MarkdownLogger; \
		c = EDoreczeniaClient(logger=MarkdownLogger(scenario_name='send')); \
		c.authenticate(); \
		r = c.send_message('AE:PL-ODBIORCA-TEST-00001', 'Test DSL', 'Wiadomość testowa z DSL'); \
		print(f'✅ Wysłano: {r.get(\"messageId\")} [{r.get(\"status\")}]')"

# Odbieranie wiadomości
receive:
	@echo "📥 Odbieranie wiadomości..."
	@python3 -c "from python_client.client import EDoreczeniaClient; from python_client.logger import MarkdownLogger; \
		c = EDoreczeniaClient(logger=MarkdownLogger(scenario_name='receive')); \
		c.authenticate(); \
		msgs = c.get_messages('inbox', 10); \
		print(f'📧 Pobrano {len(msgs)} wiadomości:'); \
		[print(f'   • {m.get(\"subject\", \"(brak)\")} [{m.get(\"status\")}]') for m in msgs[:5]]"

# Synchronizacja (info)
sync:
	@echo "🔄 Synchronizacja API → IMAP..."
	@echo "Użyj: make test-scenarios dla pełnej synchronizacji z logami"

# ═══════════════════════════════════════════════════════════════
# SKRYPTY GROOVY (lokalne)
# ═══════════════════════════════════════════════════════════════

# Wysyłanie dokumentu (Groovy)
send-doc:
	@echo "Użycie: groovy routes/send-document.groovy -f PLIK -r ODBIORCA"
	@echo "Przykład: groovy routes/send-document.groovy -f dokument.pdf -r AE:PL-ODBIORCA-00001"

# Odbieranie (Groovy)
receive-groovy:
	groovy routes/receive-messages.groovy -f inbox -l 10

# Test połączenia
test:
	@echo "🧪 Test połączenia z API (port 8380)..."
	@curl -s http://localhost:8380/health | python3 -m json.tool || echo "❌ Symulator DSL nie jest uruchomiony. Użyj: make up"
	@echo ""
	@echo "🧪 Test DSL..."
	@python3 routes/test-dsl.py

# Pełne testy scenariuszowe z logami Markdown
test-scenarios:
	@echo "🧪 Uruchamianie scenariuszy testowych..."
	@python3 python_client/run_tests.py

# Szybki test Python Client
test-client:
	@python3 -c "from python_client.client import EDoreczeniaClient; c = EDoreczeniaClient(); print('✓ Client OK'); c.health_check()"

# Wyświetl ostatni raport
show-report:
	@echo "📄 Ostatni raport:"
	@ls -t logs/*.md 2>/dev/null | head -1 | xargs cat || echo "Brak raportów w logs/"

# Lista raportów
list-reports:
	@echo "📋 Raporty w logs/:"
	@ls -la logs/*.md 2>/dev/null || echo "Brak raportów"

# Status
status:
	docker-compose ps

# Restart
restart: down up

# ═══════════════════════════════════════════════════════════════
# KOMENDY WSZYSTKICH USŁUG
# ═══════════════════════════════════════════════════════════════

# Uruchom wszystkie usługi
all-up:
	@echo "🚀 Uruchamianie wszystkich usług e-Doręczeń..."
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp up-detached
	@$(MAKE) -C ../edoreczenia-middleware-sync up-detached
	docker-compose up -d --build
	@echo ""
	@echo "✅ Wszystkie usługi uruchomione!"
	@$(MAKE) all-status

# Zatrzymaj wszystkie usługi
all-down:
	@echo "🛑 Zatrzymywanie wszystkich usług e-Doręczeń..."
	@$(MAKE) -C ../edoreczenia-proxy-imap-smtp down
	@$(MAKE) -C ../edoreczenia-middleware-sync down
	docker-compose down
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
	@docker-compose -f ../edoreczenia-middleware-sync/docker-compose.yml ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"
	@echo ""
	@echo "📦 DSL (localhost:8380, :31143, :31025):"
	@docker-compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || echo "  (nie uruchomiony)"

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

# Middleware Sync
sync-up:
	@$(MAKE) -C ../edoreczenia-middleware-sync up

sync-down:
	@$(MAKE) -C ../edoreczenia-middleware-sync down

sync-logs:
	@$(MAKE) -C ../edoreczenia-middleware-sync logs

sync-status:
	@$(MAKE) -C ../edoreczenia-middleware-sync status

# Uruchomienie w tle (dla all-up)
up-detached:
	docker-compose up -d --build
