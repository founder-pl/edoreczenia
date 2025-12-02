"""
SQLite Database Configuration
Centralna konfiguracja bazy danych dla wszystkich usług
"""

import os
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text, Boolean, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./edoreczenia.db")

# Create engine
engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=False
)

# Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class
Base = declarative_base()


# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class User(Base):
    """Użytkownik systemu"""
    __tablename__ = "users"
    
    id = Column(String(50), primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), nullable=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=True)
    ade_address = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("Message", back_populates="user", foreign_keys="Message.user_id")
    integrations = relationship("AddressIntegration", back_populates="user")
    events = relationship("Event", back_populates="user")


class Message(Base):
    """Wiadomość e-Doręczeń"""
    __tablename__ = "messages"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    folder = Column(String(50), default="inbox", index=True)
    subject = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    status = Column(String(50), default="DRAFT", index=True)
    
    # Sender/Recipient as JSON
    sender_address = Column(String(100), nullable=True)
    sender_name = Column(String(255), nullable=True)
    recipient_address = Column(String(100), nullable=True)
    recipient_name = Column(String(255), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    received_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    archived_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)
    
    # Metadata
    attachments = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)  # renamed from metadata (reserved)
    version = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User", back_populates="messages", foreign_keys=[user_id])


class Event(Base):
    """Event Sourcing - zdarzenia"""
    __tablename__ = "events"
    
    id = Column(String(50), primary_key=True)
    event_type = Column(String(100), nullable=False, index=True)
    aggregate_id = Column(String(50), nullable=False, index=True)
    aggregate_type = Column(String(50), nullable=False)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=True, index=True)
    
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    version = Column(Integer, default=1)
    
    correlation_id = Column(String(50), nullable=True)
    causation_id = Column(String(50), nullable=True)
    
    payload = Column(JSON, default=dict)
    event_metadata = Column(JSON, default=dict)  # renamed from metadata (reserved)
    
    # Relationships
    user = relationship("User", back_populates="events")


class AddressIntegration(Base):
    """Integracja adresu e-Doręczeń"""
    __tablename__ = "address_integrations"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    ade_address = Column(String(100), nullable=False, index=True)
    
    status = Column(String(50), default="pending")  # pending, verifying, active, failed
    provider = Column(String(50), default="certum")
    auth_method = Column(String(50), nullable=True)
    entity_type = Column(String(50), default="person")
    
    # Identification data
    nip = Column(String(20), nullable=True)
    pesel = Column(String(20), nullable=True)
    krs = Column(String(20), nullable=True)
    regon = Column(String(20), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    verified_at = Column(DateTime, nullable=True)
    
    # Credentials (encrypted in production)
    oauth_token = Column(Text, nullable=True)
    certificate_thumbprint = Column(String(100), nullable=True)
    api_key = Column(String(100), nullable=True)
    credentials_expire_at = Column(DateTime, nullable=True)
    
    message = Column(String(500), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="integrations")


class Folder(Base):
    """Folder wiadomości"""
    __tablename__ = "folders"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    label = Column(String(50), nullable=True)
    parent_id = Column(String(50), nullable=True)
    is_system = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Attachment(Base):
    """Załącznik do wiadomości"""
    __tablename__ = "attachments"
    
    id = Column(String(50), primary_key=True)
    message_id = Column(String(50), ForeignKey("messages.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=True)
    size = Column(Integer, default=0)
    storage_path = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class MailboxConnection(Base):
    """Połączenie ze skrzynką e-Doręczeń"""
    __tablename__ = "mailbox_connections"
    
    id = Column(String(50), primary_key=True)
    user_id = Column(String(50), ForeignKey("users.id"), nullable=False, index=True)
    
    # Dane skrzynki
    ade_address = Column(String(100), nullable=False, unique=True, index=True)
    mailbox_name = Column(String(255), nullable=True)
    mailbox_type = Column(String(50), default="person")
    
    # Metoda i status
    connection_method = Column(String(50), default="oauth2")
    status = Column(String(50), default="pending")
    
    # OAuth2 tokens
    oauth_access_token = Column(Text, nullable=True)
    oauth_refresh_token = Column(Text, nullable=True)
    oauth_expires_at = Column(DateTime, nullable=True)
    
    # Certificate
    certificate_thumbprint = Column(String(100), nullable=True)
    certificate_subject = Column(String(255), nullable=True)
    certificate_expires_at = Column(DateTime, nullable=True)
    
    # API Key
    api_key = Column(String(100), nullable=True)
    api_secret_hash = Column(String(255), nullable=True)
    
    # Sync config
    sync_enabled = Column(Boolean, default=True)
    sync_interval_minutes = Column(Integer, default=5)
    last_sync_at = Column(DateTime, nullable=True)
    next_sync_at = Column(DateTime, nullable=True)
    
    # Stats
    messages_synced = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    connected_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Extra
    extra_config = Column(JSON, default=dict)


# ═══════════════════════════════════════════════════════════════
# DATABASE INITIALIZATION
# ═══════════════════════════════════════════════════════════════

def init_db():
    """Inicjalizacja bazy danych - tworzenie tabel"""
    Base.metadata.create_all(bind=engine)
    
    # Dodaj domyślnego użytkownika testowego
    db = SessionLocal()
    try:
        existing_user = db.query(User).filter(User.username == "testuser").first()
        if not existing_user:
            import hashlib
            password_hash = hashlib.sha256("testpass123".encode()).hexdigest()
            
            test_user = User(
                id="user-testuser",
                username="testuser",
                email="test@example.com",
                password_hash=password_hash,
                name="Użytkownik Testowy",
                ade_address="AE:PL-12345-67890-ABCDE-12"
            )
            db.add(test_user)
            
            # Dodaj domyślne foldery
            default_folders = [
                ("inbox", "Odebrane", "INBOX"),
                ("sent", "Wysłane", "SENT"),
                ("drafts", "Robocze", "DRAFTS"),
                ("trash", "Kosz", "TRASH"),
                ("archive", "Archiwum", "ARCHIVE"),
            ]
            for folder_id, name, label in default_folders:
                folder = Folder(
                    id=f"{folder_id}-{test_user.id}",
                    user_id=test_user.id,
                    name=name,
                    label=label,
                    is_system=True
                )
                db.add(folder)
            
            db.commit()
            print("✓ Created test user and default folders")
    except Exception as e:
        print(f"Error initializing database: {e}")
        db.rollback()
    finally:
        db.close()


def get_db():
    """Dependency do pobierania sesji bazy danych"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Initialize on import
init_db()
