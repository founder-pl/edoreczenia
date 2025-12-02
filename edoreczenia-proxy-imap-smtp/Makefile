.PHONY: build up down logs test clean help simulator-logs proxy-logs

# Domyślny cel
help:
	@echo "=== e-Doręczenia Proxy IMAP/SMTP ==="
	@echo ""
	@echo "Dostępne komendy:"
	@echo "  make build      - Buduje obrazy Docker"
	@echo "  make up         - Uruchamia wszystkie kontenery"
	@echo "  make down       - Zatrzymuje wszystkie kontenery"
	@echo "  make logs       - Pokazuje logi wszystkich kontenerów"
	@echo "  make test       - Uruchamia testy"
	@echo "  make clean      - Czyści zasoby Docker"
	@echo ""
	@echo "Logi poszczególnych serwisów:"
	@echo "  make simulator-logs  - Logi symulatora API"
	@echo "  make proxy-logs      - Logi proxy IMAP/SMTP"
	@echo ""
	@echo "Dane dostępowe:"
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
