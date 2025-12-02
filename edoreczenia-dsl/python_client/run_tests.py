#!/usr/bin/env python3
"""
e-Doręczenia DSL - Uruchomienie testów

Uruchamia wszystkie scenariusze testowe i generuje raporty Markdown.

Użycie:
    python3 -m python-client.run_tests
    python3 python-client/run_tests.py
"""

import sys
import os

# Dodaj ścieżkę do modułu
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from python_client.scenarios import run_all_scenarios
    from python_client.config import config
except ImportError:
    from scenarios import run_all_scenarios
    from config import config


def main():
    print("""
╔══════════════════════════════════════════════════════════════╗
║           e-Doręczenia DSL - Python Client                   ║
║                    Testy scenariuszowe                       ║
╠══════════════════════════════════════════════════════════════╣
║  Konfiguracja:                                               ║
║  • API URL:     {api_url:<42} ║
║  • Address:     {address:<42} ║
║  • Log Dir:     {log_dir:<42} ║
╚══════════════════════════════════════════════════════════════╝
""".format(
        api_url=config.api_url,
        address=config.address,
        log_dir=config.log_dir
    ))
    
    # Uruchom scenariusze
    result = run_all_scenarios(log_dir=config.log_dir)
    
    # Zwróć kod wyjścia
    return 0 if result['passed'] == result['total'] else 1


if __name__ == '__main__':
    sys.exit(main())
