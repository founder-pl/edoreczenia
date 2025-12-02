.PHONY: build up down logs test clean help simulator-logs sync-logs dovecot-logs

# Domyślny cel
help:
	@echo "=== e-Doręczenia Middleware Sync ==="
	@echo ""
	@echo "Dostępne komendy:"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia wszystkie kontenery"
	@echo "  make down       - Zatrzymuje wszystkie kontenery"
	@echo "  make logs       - Pokazuje logi wszystkich kontenerów"
	@echo "  make test       - Uruchamia testy"
	@echo "  make clean      - Czyści zasoby Docker"
	@echo "  make sync-once  - Uruchamia jednorazową synchronizację"
	@echo "  make sync-status - Pokazuje status synchronizacji"
	@echo ""
	@echo "Logi poszczególnych serwisów:"
	@echo "  make simulator-logs  - Logi symulatora API"
	@echo "  make sync-logs       - Logi middleware sync"
	@echo "  make dovecot-logs    - Logi serwera IMAP"
	@echo ""
	@echo "Dane dostępowe:"
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
