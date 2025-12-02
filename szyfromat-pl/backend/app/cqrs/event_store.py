"""
Event Store - Przechowywanie zdarzeń w SQLite
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from collections import defaultdict
import json
import asyncio
import uuid

from sqlalchemy.orm import Session
from ..database import SessionLocal, Event as EventModel
from .events import Event, EventType


class EventStore:
    """
    Event Store - przechowuje wszystkie zdarzenia w SQLite.
    """
    
    def __init__(self):
        self._subscribers: Dict[str, List[callable]] = defaultdict(list)
        self._global_subscribers: List[callable] = []
        self._lock = asyncio.Lock()
    
    def _get_db(self) -> Session:
        """Pobierz sesję bazy danych"""
        return SessionLocal()
    
    def _event_to_model(self, event: Event) -> EventModel:
        """Konwertuj Event na model bazy danych"""
        return EventModel(
            id=event.event_id,
            event_type=event.event_type,
            aggregate_id=event.aggregate_id,
            aggregate_type=event.aggregate_type,
            user_id=event.user_id,
            timestamp=event.timestamp,
            version=event.version,
            correlation_id=event.correlation_id,
            causation_id=event.causation_id,
            payload=event.payload,
            event_metadata=event.metadata
        )
    
    def _model_to_event(self, model: EventModel) -> Event:
        """Konwertuj model bazy danych na Event"""
        return Event(
            event_id=model.id,
            event_type=model.event_type,
            aggregate_id=model.aggregate_id,
            aggregate_type=model.aggregate_type,
            user_id=model.user_id,
            timestamp=model.timestamp,
            version=model.version,
            correlation_id=model.correlation_id,
            causation_id=model.causation_id,
            payload=model.payload or {},
            metadata=model.event_metadata or {}
        )
    
    async def append(self, event: Event) -> None:
        """Dodaj zdarzenie do store"""
        async with self._lock:
            db = self._get_db()
            try:
                # Pobierz najnowszą wersję
                latest = db.query(EventModel).filter(
                    EventModel.aggregate_id == event.aggregate_id
                ).order_by(EventModel.version.desc()).first()
                
                event.version = (latest.version + 1) if latest else 1
                
                # Zapisz do bazy
                db_event = self._event_to_model(event)
                db.add(db_event)
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Error appending event: {e}")
                raise
            finally:
                db.close()
        
        # Powiadom subskrybentów
        await self._notify_subscribers(event)
    
    async def append_batch(self, events: List[Event]) -> None:
        """Dodaj wiele zdarzeń atomowo"""
        async with self._lock:
            db = self._get_db()
            try:
                for event in events:
                    latest = db.query(EventModel).filter(
                        EventModel.aggregate_id == event.aggregate_id
                    ).order_by(EventModel.version.desc()).first()
                    
                    event.version = (latest.version + 1) if latest else 1
                    db_event = self._event_to_model(event)
                    db.add(db_event)
                
                db.commit()
            except Exception as e:
                db.rollback()
                print(f"Error appending batch: {e}")
                raise
            finally:
                db.close()
        
        for event in events:
            await self._notify_subscribers(event)
    
    async def get_events(
        self, 
        aggregate_id: Optional[str] = None,
        event_type: Optional[str] = None,
        from_version: int = 0,
        limit: int = 100
    ) -> List[Event]:
        """Pobierz zdarzenia z filtrami"""
        db = self._get_db()
        try:
            query = db.query(EventModel)
            
            if aggregate_id:
                query = query.filter(EventModel.aggregate_id == aggregate_id)
            if event_type:
                query = query.filter(EventModel.event_type == event_type)
            if from_version > 0:
                query = query.filter(EventModel.version > from_version)
            
            query = query.order_by(EventModel.timestamp.asc()).limit(limit)
            
            return [self._model_to_event(e) for e in query.all()]
        finally:
            db.close()
    
    async def get_aggregate_events(self, aggregate_id: str) -> List[Event]:
        """Pobierz wszystkie zdarzenia dla agregatu"""
        db = self._get_db()
        try:
            events = db.query(EventModel).filter(
                EventModel.aggregate_id == aggregate_id
            ).order_by(EventModel.version.asc()).all()
            
            return [self._model_to_event(e) for e in events]
        finally:
            db.close()
    
    async def get_latest_version(self, aggregate_id: str) -> int:
        """Pobierz najnowszą wersję agregatu"""
        db = self._get_db()
        try:
            latest = db.query(EventModel).filter(
                EventModel.aggregate_id == aggregate_id
            ).order_by(EventModel.version.desc()).first()
            
            return latest.version if latest else 0
        finally:
            db.close()
    
    async def get_all_events(self, from_position: int = 0, limit: int = 100) -> List[Event]:
        """Pobierz wszystkie zdarzenia"""
        db = self._get_db()
        try:
            events = db.query(EventModel).order_by(
                EventModel.timestamp.asc()
            ).offset(from_position).limit(limit).all()
            
            return [self._model_to_event(e) for e in events]
        finally:
            db.close()
    
    async def get_events_by_user(self, user_id: str, limit: int = 100) -> List[Event]:
        """Pobierz zdarzenia użytkownika"""
        db = self._get_db()
        try:
            events = db.query(EventModel).filter(
                EventModel.user_id == user_id
            ).order_by(EventModel.timestamp.desc()).limit(limit).all()
            
            return [self._model_to_event(e) for e in events]
        finally:
            db.close()
    
    async def get_events_since(self, since: datetime, limit: int = 100) -> List[Event]:
        """Pobierz zdarzenia od określonego czasu"""
        db = self._get_db()
        try:
            events = db.query(EventModel).filter(
                EventModel.timestamp >= since
            ).order_by(EventModel.timestamp.asc()).limit(limit).all()
            
            return [self._model_to_event(e) for e in events]
        finally:
            db.close()
    
    # ═══════════════════════════════════════════════════════════════
    # SUBSCRIPTIONS (Event Handlers)
    # ═══════════════════════════════════════════════════════════════
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """Subskrybuj zdarzenia określonego typu"""
        self._subscribers[event_type].append(handler)
    
    def subscribe_all(self, handler: callable) -> None:
        """Subskrybuj wszystkie zdarzenia"""
        self._global_subscribers.append(handler)
    
    async def _notify_subscribers(self, event: Event) -> None:
        """Powiadom subskrybentów o zdarzeniu"""
        for handler in self._subscribers.get(event.event_type, []):
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Error in event handler: {e}")
        
        for handler in self._global_subscribers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                print(f"Error in global event handler: {e}")
    
    # ═══════════════════════════════════════════════════════════════
    # STATISTICS
    # ═══════════════════════════════════════════════════════════════
    
    def get_stats(self) -> Dict[str, Any]:
        """Statystyki Event Store"""
        db = self._get_db()
        try:
            total = db.query(EventModel).count()
            
            # Agregaty
            from sqlalchemy import func
            aggregates = db.query(EventModel.aggregate_id).distinct().count()
            
            # Typy zdarzeń
            event_types = db.query(
                EventModel.event_type, 
                func.count(EventModel.id)
            ).group_by(EventModel.event_type).all()
            
            return {
                "total_events": total,
                "aggregates_count": aggregates,
                "event_types": {et: count for et, count in event_types},
                "storage": "sqlite"
            }
        finally:
            db.close()


# Singleton instance
event_store = EventStore()
