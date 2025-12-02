"""
e-Doręczenia DSL - Scenariusze testowe

Zestaw scenariuszy testowych z logowaniem do Markdown.
"""

import time
from datetime import datetime
from typing import List, Dict, Any

from .config import config
from .client import EDoreczeniaClient
from .logger import MarkdownLogger


def scenario_health_check(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Sprawdzenie dostępności API"""
    logger.start_scenario('Health Check', 'Sprawdzenie dostępności i statusu API e-Doręczeń')
    
    try:
        result = client.health_check()
        
        logger.success('HEALTH', f'API dostępne', {
            'service': result.get('service'),
            'version': result.get('version')
        })
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('HEALTH', f'API niedostępne: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def scenario_authentication(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Autoryzacja OAuth2"""
    logger.start_scenario('OAuth2 Authentication', 'Pobieranie tokenu dostępu OAuth2')
    
    try:
        logger.info('AUTH', f'Client ID: {client.client_id}')
        logger.info('AUTH', f'Token URL: {client.api_url}/oauth/token')
        
        token = client.authenticate()
        
        logger.success('AUTH', 'Token pobrany pomyślnie', {
            'token_preview': token[:30] + '...'
        })
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('AUTH', f'Błąd autoryzacji: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def scenario_list_messages(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Pobieranie listy wiadomości"""
    logger.start_scenario('List Messages', 'Pobieranie wiadomości z różnych folderów')
    
    try:
        # Pobierz z inbox
        logger.info('API', 'Pobieranie wiadomości z INBOX')
        inbox = client.get_messages(folder='inbox', limit=10)
        
        for msg in inbox[:3]:
            logger.debug('MSG', f"📧 {msg.get('subject', '(brak)')[:50]}", {
                'id': msg.get('messageId'),
                'status': msg.get('status'),
                'sender': msg.get('sender', {}).get('address')
            })
        
        # Pobierz z sent
        logger.info('API', 'Pobieranie wiadomości z SENT')
        sent = client.get_messages(folder='sent', limit=5)
        
        logger.success('API', f'Pobrano wiadomości', {
            'inbox': len(inbox),
            'sent': len(sent)
        })
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('API', f'Błąd pobierania: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def scenario_send_message(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Wysyłanie wiadomości"""
    logger.start_scenario('Send Message', 'Wysyłanie nowej wiadomości e-Doręczenia')
    
    try:
        test_subject = f"Test DSL {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        recipient = config.default_recipient
        
        logger.info('SEND', f'Przygotowanie wiadomości', {
            'subject': test_subject,
            'recipient': recipient
        })
        
        result = client.send_message(
            recipient=recipient,
            subject=test_subject,
            content='To jest wiadomość testowa wysłana przez e-Doręczenia DSL Python Client.'
        )
        
        logger.success('SEND', 'Wiadomość wysłana', {
            'messageId': result.get('messageId'),
            'status': result.get('status')
        })
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('SEND', f'Błąd wysyłania: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def scenario_get_message_details(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Pobieranie szczegółów wiadomości"""
    logger.start_scenario('Get Message Details', 'Pobieranie pełnych szczegółów wiadomości')
    
    try:
        # Najpierw pobierz listę
        messages = client.get_messages(folder='inbox', limit=1)
        
        if not messages:
            logger.info('API', 'Brak wiadomości do pobrania')
            logger.end_scenario(success=True)
            return True
        
        message_id = messages[0]['messageId']
        logger.info('API', f'Pobieranie szczegółów: {message_id}')
        
        msg = client.get_message(message_id)
        
        logger.success('DETAILS', 'Szczegóły wiadomości', {
            'subject': msg.get('subject'),
            'sender': msg.get('sender', {}).get('address'),
            'receivedAt': msg.get('receivedAt'),
            'attachments': len(msg.get('attachments', []))
        })
        
        # Pokaż załączniki
        for att in msg.get('attachments', []):
            logger.debug('ATTACH', f"📎 {att.get('filename')}", {
                'type': att.get('contentType'),
                'size': att.get('size')
            })
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('API', f'Błąd pobierania: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def scenario_list_directories(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Pobieranie katalogów"""
    logger.start_scenario('List Directories', 'Pobieranie struktury katalogów e-Doręczeń')
    
    try:
        directories = client.get_directories()
        
        for dir in directories:
            logger.debug('DIR', f"📁 {dir.get('name')}", {
                'id': dir.get('directoryId'),
                'label': dir.get('label'),
                'type': dir.get('type')
            })
        
        logger.success('API', f'Pobrano {len(directories)} katalogów')
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('API', f'Błąd pobierania: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def scenario_full_flow(client: EDoreczeniaClient, logger: MarkdownLogger) -> bool:
    """Scenariusz: Pełny przepływ wysyłki i odbioru"""
    logger.start_scenario('Full Flow', 'Kompletny przepływ: wysyłka → odbiór → weryfikacja')
    
    try:
        # Krok 1: Sprawdź początkową liczbę wiadomości
        logger.info('FLOW', 'Krok 1: Sprawdzenie stanu początkowego')
        initial_messages = client.get_messages(folder='inbox')
        initial_count = len(initial_messages)
        
        # Krok 2: Wyślij wiadomość
        logger.info('FLOW', 'Krok 2: Wysyłanie wiadomości testowej')
        test_subject = f"Full Flow Test {datetime.now().strftime('%H:%M:%S')}"
        
        send_result = client.send_message(
            recipient=config.default_recipient,
            subject=test_subject,
            content='Wiadomość testowa dla scenariusza Full Flow.'
        )
        
        message_id = send_result.get('messageId')
        logger.success('FLOW', f'Wysłano: {message_id}')
        
        # Krok 3: Poczekaj chwilę
        logger.info('FLOW', 'Krok 3: Oczekiwanie na przetworzenie (1s)')
        time.sleep(1)
        
        # Krok 4: Sprawdź czy wiadomość jest w sent
        logger.info('FLOW', 'Krok 4: Weryfikacja w folderze SENT')
        sent_messages = client.get_messages(folder='sent', limit=5)
        
        found_in_sent = any(
            msg.get('messageId') == message_id or test_subject in msg.get('subject', '')
            for msg in sent_messages
        )
        
        if found_in_sent:
            logger.success('FLOW', 'Wiadomość znaleziona w SENT')
        else:
            logger.info('FLOW', 'Wiadomość nie znaleziona w SENT (symulator może nie zapisywać)')
        
        # Krok 5: Podsumowanie
        logger.info('FLOW', 'Krok 5: Podsumowanie przepływu', {
            'initial_inbox': initial_count,
            'message_sent': message_id,
            'found_in_sent': found_in_sent
        })
        
        logger.end_scenario(success=True)
        return True
        
    except Exception as e:
        logger.error('FLOW', f'Błąd przepływu: {e}')
        logger.end_scenario(success=False, error=str(e))
        return False


def run_all_scenarios(log_dir: str = './logs') -> Dict[str, Any]:
    """Uruchamia wszystkie scenariusze testowe"""
    
    print("\n" + "═" * 60)
    print("  e-Doręczenia DSL - Scenariusze testowe")
    print("═" * 60 + "\n")
    
    # Inicjalizacja
    logger = MarkdownLogger(log_dir=log_dir, scenario_name='all_scenarios')
    client = EDoreczeniaClient(logger=logger)
    
    scenarios = [
        ('Health Check', scenario_health_check),
        ('OAuth2 Authentication', scenario_authentication),
        ('List Messages', scenario_list_messages),
        ('Send Message', scenario_send_message),
        ('Get Message Details', scenario_get_message_details),
        ('List Directories', scenario_list_directories),
        ('Full Flow', scenario_full_flow),
    ]
    
    results = {}
    
    for name, scenario_func in scenarios:
        print(f"\n{'─' * 40}")
        print(f"  📋 {name}")
        print(f"{'─' * 40}")
        
        try:
            success = scenario_func(client, logger)
            results[name] = success
        except Exception as e:
            results[name] = False
            logger.error('RUNNER', f'Błąd scenariusza {name}: {e}')
    
    # Zapisz raport
    report_path = logger.save()
    
    # Podsumowanie
    print("\n" + "═" * 60)
    print("  PODSUMOWANIE")
    print("═" * 60)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, success in results.items():
        icon = '✅' if success else '❌'
        print(f"  {icon} {name}")
    
    print(f"\n  Wynik: {passed}/{total} ({100*passed//total}%)")
    print(f"  Raport: {report_path}")
    print("═" * 60 + "\n")
    
    return {
        'results': results,
        'passed': passed,
        'total': total,
        'report_path': report_path
    }


if __name__ == '__main__':
    run_all_scenarios()
