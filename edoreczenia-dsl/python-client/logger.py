"""
e-Doręczenia DSL - Markdown Logger

Logger generujący raporty w formacie Markdown.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class LogEntry:
    """Pojedynczy wpis logu"""
    timestamp: datetime
    level: str
    category: str
    message: str
    details: Optional[Dict[str, Any]] = None
    success: Optional[bool] = None


@dataclass
class ScenarioResult:
    """Wynik scenariusza testowego"""
    name: str
    description: str
    steps: List[Dict[str, Any]] = field(default_factory=list)
    success: bool = True
    duration_ms: float = 0
    error: Optional[str] = None


class MarkdownLogger:
    """Logger generujący raporty Markdown"""
    
    def __init__(self, log_dir: str = './logs', scenario_name: str = 'test'):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.scenario_name = scenario_name
        self.start_time = datetime.now()
        self.entries: List[LogEntry] = []
        self.scenarios: List[ScenarioResult] = []
        self.current_scenario: Optional[ScenarioResult] = None
    
    def _timestamp(self) -> str:
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    def log(self, level: str, category: str, message: str, 
            details: Optional[Dict] = None, success: Optional[bool] = None):
        """Dodaje wpis do logu"""
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            category=category,
            message=message,
            details=details,
            success=success
        )
        self.entries.append(entry)
        
        # Wyświetl na konsoli
        icon = '✓' if success is True else '✗' if success is False else '→'
        print(f"[{self._timestamp()}] {icon} [{category}] {message}")
        
        # Dodaj do bieżącego scenariusza
        if self.current_scenario:
            self.current_scenario.steps.append({
                'timestamp': entry.timestamp.isoformat(),
                'level': level,
                'message': message,
                'details': details,
                'success': success
            })
    
    def info(self, category: str, message: str, details: Optional[Dict] = None):
        self.log('INFO', category, message, details)
    
    def success(self, category: str, message: str, details: Optional[Dict] = None):
        self.log('INFO', category, message, details, success=True)
    
    def error(self, category: str, message: str, details: Optional[Dict] = None):
        self.log('ERROR', category, message, details, success=False)
        if self.current_scenario:
            self.current_scenario.success = False
    
    def debug(self, category: str, message: str, details: Optional[Dict] = None):
        self.log('DEBUG', category, message, details)
    
    def start_scenario(self, name: str, description: str = ''):
        """Rozpoczyna nowy scenariusz"""
        self.current_scenario = ScenarioResult(
            name=name,
            description=description
        )
        self.info('SCENARIO', f'Rozpoczęcie: {name}')
    
    def end_scenario(self, success: bool = True, error: Optional[str] = None):
        """Kończy bieżący scenariusz"""
        if self.current_scenario:
            self.current_scenario.success = success and self.current_scenario.success
            self.current_scenario.error = error
            self.current_scenario.duration_ms = (
                datetime.now() - self.start_time
            ).total_seconds() * 1000
            
            self.scenarios.append(self.current_scenario)
            
            status = '✅ PASS' if self.current_scenario.success else '❌ FAIL'
            self.info('SCENARIO', f'Zakończenie: {self.current_scenario.name} - {status}')
            self.current_scenario = None
    
    def generate_markdown(self) -> str:
        """Generuje raport Markdown"""
        md = []
        
        # Nagłówek
        md.append(f"# 📋 Raport DSL e-Doręczeń")
        md.append(f"\n**Data:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        md.append(f"\n**Scenariusz:** {self.scenario_name}")
        
        # Podsumowanie
        total = len(self.scenarios)
        passed = sum(1 for s in self.scenarios if s.success)
        
        md.append(f"\n## 📊 Podsumowanie\n")
        md.append(f"| Metryka | Wartość |")
        md.append(f"|---------|---------|")
        md.append(f"| Scenariusze | {total} |")
        md.append(f"| Sukces | {passed} |")
        md.append(f"| Błędy | {total - passed} |")
        md.append(f"| Procent | {100*passed//total if total else 0}% |")
        
        # Wyniki scenariuszy
        md.append(f"\n## 🧪 Scenariusze testowe\n")
        
        for scenario in self.scenarios:
            status = '✅' if scenario.success else '❌'
            md.append(f"### {status} {scenario.name}\n")
            
            if scenario.description:
                md.append(f"_{scenario.description}_\n")
            
            md.append(f"\n| Krok | Status | Opis |")
            md.append(f"|------|--------|------|")
            
            for i, step in enumerate(scenario.steps, 1):
                icon = '✓' if step.get('success') is True else '✗' if step.get('success') is False else '→'
                msg = step['message'][:60] + '...' if len(step['message']) > 60 else step['message']
                md.append(f"| {i} | {icon} | {msg} |")
            
            if scenario.error:
                md.append(f"\n**Błąd:** `{scenario.error}`\n")
        
        # Szczegółowe logi
        md.append(f"\n## 📝 Szczegółowe logi\n")
        md.append(f"```")
        
        for entry in self.entries:
            ts = entry.timestamp.strftime('%H:%M:%S.%f')[:-3]
            icon = '✓' if entry.success is True else '✗' if entry.success is False else ' '
            md.append(f"[{ts}] [{entry.level:5}] {icon} [{entry.category}] {entry.message}")
            
            if entry.details:
                for k, v in entry.details.items():
                    val = str(v)[:50] + '...' if len(str(v)) > 50 else v
                    md.append(f"           └─ {k}: {val}")
        
        md.append(f"```")
        
        # Stopka
        md.append(f"\n---")
        md.append(f"_Wygenerowano przez e-Doręczenia DSL Python Client v1.0.0_")
        
        return '\n'.join(md)
    
    def save(self, filename: Optional[str] = None) -> str:
        """Zapisuje raport do pliku Markdown"""
        if filename is None:
            timestamp = self.start_time.strftime('%Y%m%d_%H%M%S')
            filename = f"{self.scenario_name}_{timestamp}.md"
        
        filepath = self.log_dir / filename
        content = self.generate_markdown()
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"\n📄 Raport zapisany: {filepath}")
        return str(filepath)
