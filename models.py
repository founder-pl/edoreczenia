"""
Modele bazy danych do śledzenia stanu synchronizacji.
"""
from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SQLEnum,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Bazowa klasa dla modeli."""

    pass


class SyncDirection(str, Enum):
    """Kierunek synchronizacji wiadomości."""

    INCOMING = "incoming"  # Z e-Doręczeń do IMAP
    OUTGOING = "outgoing"  # Z IMAP do e-Doręczeń


class SyncStatus(str, Enum):
    """Status synchronizacji."""

    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    SKIPPED = "skipped"


class SyncedMessage(Base):
    """Model zsynchronizowanej wiadomości."""

    __tablename__ = "synced_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Identyfikatory
    edoreczenia_id = Column(String(255), unique=True, nullable=True, index=True)
    imap_uid = Column(Integer, nullable=True, index=True)
    imap_message_id = Column(String(500), nullable=True)

    # Kierunek i status
    direction = Column(SQLEnum(SyncDirection), nullable=False)
    status = Column(SQLEnum(SyncStatus), default=SyncStatus.PENDING)

    # Metadane wiadomości
    subject = Column(String(500), nullable=True)
    sender = Column(String(255), nullable=True)
    recipients = Column(Text, nullable=True)  # JSON array
    folder = Column(String(255), nullable=True)

    # Daty
    message_date = Column(DateTime, nullable=True)
    synced_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Błędy
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)

    # Flagi
    has_attachments = Column(Boolean, default=False)
    is_read = Column(Boolean, default=False)

    def __repr__(self) -> str:
        return (
            f"<SyncedMessage(id={self.id}, "
            f"edoreczenia_id={self.edoreczenia_id}, "
            f"direction={self.direction}, "
            f"status={self.status})>"
        )


class SyncRun(Base):
    """Model pojedynczego uruchomienia synchronizacji."""

    __tablename__ = "sync_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Czas
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at = Column(DateTime, nullable=True)

    # Statystyki
    messages_incoming = Column(Integer, default=0)
    messages_outgoing = Column(Integer, default=0)
    messages_failed = Column(Integer, default=0)
    messages_skipped = Column(Integer, default=0)

    # Status
    status = Column(String(50), default="running")
    error_message = Column(Text, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<SyncRun(id={self.id}, "
            f"started_at={self.started_at}, "
            f"status={self.status})>"
        )

    @property
    def total_processed(self) -> int:
        """Zwraca całkowitą liczbę przetworzonych wiadomości."""
        return (
            self.messages_incoming
            + self.messages_outgoing
            + self.messages_failed
            + self.messages_skipped
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Zwraca czas trwania w sekundach."""
        if self.finished_at and self.started_at:
            return (self.finished_at - self.started_at).total_seconds()
        return None


class Database:
    """Wrapper dla operacji bazodanowych."""

    def __init__(self, database_url: str):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def create_tables(self) -> None:
        """Tworzy tabele w bazie danych."""
        Base.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """Zwraca nową sesję."""
        return self.SessionLocal()

    def is_message_synced(
        self,
        session: Session,
        edoreczenia_id: Optional[str] = None,
        imap_uid: Optional[int] = None,
    ) -> bool:
        """Sprawdza czy wiadomość została już zsynchronizowana."""
        query = session.query(SyncedMessage)

        if edoreczenia_id:
            query = query.filter(SyncedMessage.edoreczenia_id == edoreczenia_id)
        elif imap_uid:
            query = query.filter(SyncedMessage.imap_uid == imap_uid)
        else:
            return False

        result = query.filter(SyncedMessage.status == SyncStatus.SYNCED).first()
        return result is not None

    def add_synced_message(
        self,
        session: Session,
        edoreczenia_id: Optional[str],
        imap_uid: Optional[int],
        direction: SyncDirection,
        status: SyncStatus,
        subject: Optional[str] = None,
        sender: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> SyncedMessage:
        """Dodaje rekord zsynchronizowanej wiadomości."""
        message = SyncedMessage(
            edoreczenia_id=edoreczenia_id,
            imap_uid=imap_uid,
            direction=direction,
            status=status,
            subject=subject,
            sender=sender,
            error_message=error_message,
        )
        session.add(message)
        session.commit()
        return message

    def start_sync_run(self, session: Session) -> SyncRun:
        """Rozpoczyna nowe uruchomienie synchronizacji."""
        run = SyncRun(status="running")
        session.add(run)
        session.commit()
        return run

    def finish_sync_run(
        self,
        session: Session,
        run: SyncRun,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> None:
        """Kończy uruchomienie synchronizacji."""
        run.finished_at = datetime.utcnow()
        run.status = status
        run.error_message = error_message
        session.commit()

    def get_last_sync_run(self, session: Session) -> Optional[SyncRun]:
        """Zwraca ostatnie uruchomienie synchronizacji."""
        return (
            session.query(SyncRun)
            .order_by(SyncRun.started_at.desc())
            .first()
        )

    def get_pending_outgoing(self, session: Session, limit: int = 50) -> list[SyncedMessage]:
        """Zwraca wiadomości oczekujące na wysłanie."""
        return (
            session.query(SyncedMessage)
            .filter(SyncedMessage.direction == SyncDirection.OUTGOING)
            .filter(SyncedMessage.status == SyncStatus.PENDING)
            .limit(limit)
            .all()
        )
