.PHONY: build up down logs test clean help send receive sync

# Domyślny cel
help:
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "  e-Doręczenia DSL - Apache Camel + Groovy"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Komendy Docker:"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia wszystkie kontenery"
	@echo "  make down       - Zatrzymuje wszystkie kontenery"
	@echo "  make logs       - Pokazuje logi wszystkich kontenerów"
	@echo "  make clean      - Czyści zasoby Docker"
	@echo ""
	@echo "Komendy DSL (Groovy):"
	@echo "  make send       - Wysyła testową wiadomość"
	@echo "  make receive    - Odbiera wiadomości"
	@echo "  make sync       - Synchronizuje API → IMAP"
	@echo ""
	@echo "Przykłady skryptów Groovy:"
	@echo "  groovy routes/send-document.groovy -f plik.pdf -r AE:PL-..."
	@echo "  groovy routes/receive-messages.groovy -f inbox -l 10"
	@echo ""
	@echo "Endpointy REST API (po uruchomieniu):"
	@echo "  POST http://localhost:8090/api/v1/messages      - Wyślij"
	@echo "  GET  http://localhost:8090/api/v1/messages      - Odbierz"
	@echo "  POST http://localhost:8090/api/v1/sync/to-imap  - Sync"
	@echo ""
	@echo "Dane dostępowe:"
	@echo "  DSL API:     http://localhost:8090"
	@echo "  Symulator:   http://localhost:8180/docs"
	@echo "  IMAP:        localhost:21143 (mailuser/mailpass123)"
	@echo "  SMTP Proxy:  localhost:11025 (testuser/testpass123)"

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
# KOMENDY DSL
# ═══════════════════════════════════════════════════════════════

# Wysyłanie testowej wiadomości
send:
	@echo "📤 Wysyłanie testowej wiadomości..."
	@curl -s -X POST http://localhost:8090/api/v1/messages \
		-H 'Content-Type: application/json' \
		-d '{"subject":"Test DSL","recipient":"AE:PL-ODBIORCA-TEST-00001","content":"Wiadomość testowa z DSL"}' | python3 -m json.tool || echo "Błąd - czy DSL jest uruchomiony?"

# Odbieranie wiadomości
receive:
	@echo "📥 Odbieranie wiadomości..."
	@curl -s http://localhost:8090/api/v1/messages | python3 -m json.tool || echo "Błąd - czy DSL jest uruchomiony?"

# Synchronizacja
sync:
	@echo "🔄 Synchronizacja API → IMAP..."
	@curl -s -X POST http://localhost:8090/api/v1/sync/to-imap | python3 -m json.tool || echo "Błąd - czy DSL jest uruchomiony?"

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
	@echo "🧪 Test połączenia z API..."
	@curl -s http://localhost:8180/health | python3 -m json.tool
	@echo ""
	@echo "🧪 Test DSL..."
	@python3 routes/test-dsl.py

# Status
status:
	docker-compose ps
