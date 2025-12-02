"""
Główny moduł aplikacji e-Doręczenia Middleware Sync.
"""
import signal
import sys
import time
from typing import Optional

import schedule
import structlog

from .config import Settings, get_settings
from .sync_engine import SyncEngine

logger = structlog.get_logger(__name__)


def configure_logging(settings: Settings) -> None:
    """Konfiguruje logowanie."""
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.log_format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(__import__("logging"), settings.log_level.upper(), 20)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


class Application:
    """Główna aplikacja middleware."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.sync_engine = SyncEngine(settings)
        self._running = False

    def sync_job(self) -> None:
        """Zadanie synchronizacji uruchamiane cyklicznie."""
        logger.info("Uruchamianie zaplanowanej synchronizacji")

        try:
            run = self.sync_engine.run_sync()

            if self.settings.notify_on_success and self.settings.notify_email:
                self._send_notification(
                    subject="e-Doręczenia Sync - Sukces",
                    body=f"Synchronizacja zakończona pomyślnie.\n"
                    f"Przychodzące: {run.messages_incoming}\n"
                    f"Wychodzące: {run.messages_outgoing}\n"
                    f"Błędy: {run.messages_failed}",
                )

        except Exception as e:
            logger.error("Błąd synchronizacji", error=str(e))

            if self.settings.notify_on_error and self.settings.notify_email:
                self._send_notification(
                    subject="e-Doręczenia Sync - Błąd",
                    body=f"Wystąpił błąd podczas synchronizacji:\n{e}",
                )

    def run_once(self) -> None:
        """Uruchamia pojedynczą synchronizację."""
        logger.info("Uruchamianie jednorazowej synchronizacji")
        self.sync_engine.run_sync()

    def run_daemon(self) -> None:
        """Uruchamia synchronizację jako daemon."""
        logger.info(
            "Uruchamianie daemon synchronizacji",
            interval_minutes=self.settings.sync_interval_minutes,
        )

        self._running = True

        # Rejestracja obsługi sygnałów
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # Pierwsza synchronizacja
        self.sync_job()

        # Planowanie kolejnych
        schedule.every(self.settings.sync_interval_minutes).minutes.do(self.sync_job)

        # Główna pętla
        while self._running:
            schedule.run_pending()
            time.sleep(1)

        logger.info("Daemon zatrzymany")

    def stop(self) -> None:
        """Zatrzymuje daemon."""
        self._running = False

    def _handle_signal(self, signum, frame) -> None:
        """Obsługuje sygnały systemowe."""
        logger.info("Otrzymano sygnał", signal=signum)
        self.stop()

    def _send_notification(self, subject: str, body: str) -> None:
        """Wysyła powiadomienie email (placeholder)."""
        # TODO: Implementacja wysyłania powiadomień
        logger.info("Powiadomienie", subject=subject, body=body)

    def get_status(self) -> dict:
        """Zwraca status aplikacji."""
        sync_status = self.sync_engine.get_sync_status()

        return {
            "running": self._running,
            "sync_interval_minutes": self.settings.sync_interval_minutes,
            "sync_direction": self.settings.sync_direction.value,
            "edoreczenia_address": self.settings.edoreczenia_address,
            "target_imap_host": self.settings.target_imap_host,
            **sync_status,
        }


def main() -> None:
    """Punkt wejścia aplikacji."""
    import argparse

    parser = argparse.ArgumentParser(
        description="e-Doręczenia Middleware Sync - synchronizacja z lokalną skrzynką IMAP"
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Uruchom jednorazową synchronizację i zakończ",
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Wyświetl status synchronizacji",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Uruchom jako daemon (domyślne)",
    )

    args = parser.parse_args()

    try:
        settings = get_settings()
        configure_logging(settings)

        app = Application(settings)

        if args.status:
            status = app.get_status()
            print("\n=== Status e-Doręczenia Sync ===")
            for key, value in status.items():
                print(f"{key}: {value}")
            print()

        elif args.once:
            app.run_once()

        else:
            # Domyślnie daemon
            app.run_daemon()

    except KeyboardInterrupt:
        logger.info("Przerwano przez użytkownika")
        sys.exit(0)

    except Exception as e:
        logger.error("Błąd krytyczny", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
