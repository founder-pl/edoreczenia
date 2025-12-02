"""
Silnik synchronizacji między e-Doręczeniami a lokalną skrzynką IMAP.
"""
import base64
from datetime import datetime
from typing import Optional

import structlog

from .api_client import EDoreczeniaClient, EDoreczeniaMessage
from .config import Settings, SyncDirection as ConfigSyncDirection
from .imap_client import IMAPMailbox
from .models import Database, SyncDirection, SyncRun, SyncStatus

logger = structlog.get_logger(__name__)


class SyncEngine:
    """Silnik synchronizacji e-Doręczeń ↔ IMAP."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.db = Database(settings.database_url)
        self.db.create_tables()

    def run_sync(self) -> SyncRun:
        """
        Wykonuje pełną synchronizację.

        Zwraca obiekt SyncRun z wynikami.
        """
        session = self.db.get_session()
        run = self.db.start_sync_run(session)

        logger.info("Rozpoczęcie synchronizacji", run_id=run.id)

        try:
            with (
                EDoreczeniaClient(self.settings) as api_client,
                IMAPMailbox(self.settings) as imap_client,
            ):
                # Synchronizacja przychodząca
                if self.settings.sync_direction in (
                    ConfigSyncDirection.INCOMING,
                    ConfigSyncDirection.BIDIRECTIONAL,
                ):
                    incoming = self._sync_incoming(session, api_client, imap_client, run)
                    run.messages_incoming = incoming

                # Synchronizacja wychodząca
                if self.settings.sync_direction in (
                    ConfigSyncDirection.OUTGOING,
                    ConfigSyncDirection.BIDIRECTIONAL,
                ):
                    outgoing = self._sync_outgoing(session, api_client, imap_client, run)
                    run.messages_outgoing = outgoing

            self.db.finish_sync_run(session, run, status="completed")
            logger.info(
                "Synchronizacja zakończona",
                run_id=run.id,
                incoming=run.messages_incoming,
                outgoing=run.messages_outgoing,
                failed=run.messages_failed,
                duration=run.duration_seconds,
            )

        except Exception as e:
            logger.error("Błąd synchronizacji", error=str(e), run_id=run.id)
            self.db.finish_sync_run(session, run, status="failed", error_message=str(e))
            raise

        finally:
            session.close()

        return run

    def _sync_incoming(
        self,
        session,
        api_client: EDoreczeniaClient,
        imap_client: IMAPMailbox,
        run: SyncRun,
    ) -> int:
        """
        Synchronizuje wiadomości przychodzące (e-Doręczenia → IMAP).

        Zwraca liczbę zsynchronizowanych wiadomości.
        """
        logger.info("Synchronizacja przychodząca")
        synced_count = 0

        # Pobierz ostatnią datę synchronizacji
        last_run = self.db.get_last_sync_run(session)
        since = last_run.finished_at if last_run and last_run.status == "completed" else None

        # Pobierz wiadomości z e-Doręczeń
        messages = api_client.get_messages(
            folder="inbox",
            limit=self.settings.sync_batch_size,
            since=since,
        )

        for msg in messages:
            try:
                # Sprawdź czy już zsynchronizowano
                if self.db.is_message_synced(session, edoreczenia_id=msg.message_id):
                    logger.debug("Wiadomość już zsynchronizowana", message_id=msg.message_id)
                    run.messages_skipped += 1
                    continue

                # Sprawdź czy już istnieje w IMAP
                if imap_client.message_exists(
                    self.settings.folder_mapping_inbox,
                    msg.message_id,
                ):
                    logger.debug("Wiadomość już w IMAP", message_id=msg.message_id)
                    run.messages_skipped += 1
                    continue

                # Pobierz załączniki
                attachments_data = []
                if msg.attachments:
                    for att in msg.attachments:
                        content, filename, content_type = api_client.get_attachment(
                            msg.message_id,
                            att.get("attachmentId", ""),
                        )
                        attachments_data.append((content, filename, content_type))

                # Dodaj do IMAP
                uid = imap_client.append_message(
                    self.settings.folder_mapping_inbox,
                    msg,
                    attachments_data,
                )

                # Zapisz w bazie
                self.db.add_synced_message(
                    session,
                    edoreczenia_id=msg.message_id,
                    imap_uid=uid,
                    direction=SyncDirection.INCOMING,
                    status=SyncStatus.SYNCED,
                    subject=msg.subject,
                    sender=msg.sender,
                )

                synced_count += 1
                logger.info(
                    "Zsynchronizowano wiadomość przychodzącą",
                    message_id=msg.message_id,
                    subject=msg.subject,
                )

            except Exception as e:
                logger.error(
                    "Błąd synchronizacji wiadomości",
                    message_id=msg.message_id,
                    error=str(e),
                )
                self.db.add_synced_message(
                    session,
                    edoreczenia_id=msg.message_id,
                    imap_uid=None,
                    direction=SyncDirection.INCOMING,
                    status=SyncStatus.FAILED,
                    subject=msg.subject,
                    sender=msg.sender,
                    error_message=str(e),
                )
                run.messages_failed += 1

        return synced_count

    def _sync_outgoing(
        self,
        session,
        api_client: EDoreczeniaClient,
        imap_client: IMAPMailbox,
        run: SyncRun,
    ) -> int:
        """
        Synchronizuje wiadomości wychodzące (IMAP → e-Doręczenia).

        Zwraca liczbę wysłanych wiadomości.
        """
        logger.info("Synchronizacja wychodząca")
        sent_count = 0

        # Pobierz wiadomości z folderu wychodzącego
        outgoing_messages = imap_client.get_outgoing_messages(
            self.settings.folder_mapping_outbox
        )

        for msg_data in outgoing_messages:
            try:
                uid = msg_data["uid"]
                subject = msg_data["subject"]
                recipients = msg_data["recipients"]
                content = msg_data["content"]
                attachments = msg_data.get("attachments", [])

                # Sprawdź czy jest zsynchronizowana
                if self.db.is_message_synced(session, imap_uid=uid):
                    logger.debug("Wiadomość już wysłana", uid=uid)
                    run.messages_skipped += 1
                    continue

                # Przygotuj załączniki dla API
                api_attachments = []
                for att in attachments:
                    api_attachments.append({
                        "filename": att["filename"],
                        "contentType": att["content_type"],
                        "content": base64.b64encode(att["content"]).decode("utf-8"),
                    })

                # Wyślij przez API e-Doręczeń
                result = api_client.send_message(
                    recipients=recipients,
                    subject=subject,
                    content=content,
                    attachments=api_attachments,
                )

                edoreczenia_id = result.get("messageId")

                # Oznacz jako wysłaną w IMAP
                imap_client.mark_as_sent(self.settings.folder_mapping_outbox, uid)

                # Opcjonalnie przenieś do wysłanych
                imap_client.move_to_sent(
                    uid,
                    self.settings.folder_mapping_outbox,
                    self.settings.folder_mapping_sent,
                )

                # Zapisz w bazie
                self.db.add_synced_message(
                    session,
                    edoreczenia_id=edoreczenia_id,
                    imap_uid=uid,
                    direction=SyncDirection.OUTGOING,
                    status=SyncStatus.SYNCED,
                    subject=subject,
                    sender=self.settings.edoreczenia_address,
                )

                sent_count += 1
                logger.info(
                    "Wiadomość wysłana do e-Doręczeń",
                    uid=uid,
                    message_id=edoreczenia_id,
                    subject=subject,
                )

            except Exception as e:
                logger.error(
                    "Błąd wysyłania wiadomości",
                    uid=msg_data.get("uid"),
                    error=str(e),
                )
                self.db.add_synced_message(
                    session,
                    edoreczenia_id=None,
                    imap_uid=msg_data.get("uid"),
                    direction=SyncDirection.OUTGOING,
                    status=SyncStatus.FAILED,
                    subject=msg_data.get("subject"),
                    error_message=str(e),
                )
                run.messages_failed += 1

        return sent_count

    def get_sync_status(self) -> dict:
        """Zwraca status synchronizacji."""
        session = self.db.get_session()

        try:
            last_run = self.db.get_last_sync_run(session)

            if last_run:
                return {
                    "last_sync": last_run.started_at.isoformat(),
                    "status": last_run.status,
                    "incoming": last_run.messages_incoming,
                    "outgoing": last_run.messages_outgoing,
                    "failed": last_run.messages_failed,
                    "duration_seconds": last_run.duration_seconds,
                }
            else:
                return {
                    "last_sync": None,
                    "status": "never",
                    "incoming": 0,
                    "outgoing": 0,
                    "failed": 0,
                }

        finally:
            session.close()
