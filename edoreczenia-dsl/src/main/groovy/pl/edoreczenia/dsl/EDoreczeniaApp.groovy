package pl.edoreczenia.dsl

import org.apache.camel.main.Main

/**
 * Główna aplikacja e-Doręczenia DSL oparta na Apache Camel.
 * Uruchamia routing wiadomości między API e-Doręczeń a lokalnymi usługami.
 */
class EDoreczeniaApp {
    
    static void main(String[] args) {
        def main = new Main()
        
        // Rejestracja route'ów
        main.configure().addRoutesBuilder(new EDoreczeniaRoutes())
        
        // Uruchomienie
        println """
╔══════════════════════════════════════════════════════════════╗
║           e-Doręczenia DSL - Apache Camel + Groovy           ║
╠══════════════════════════════════════════════════════════════╣
║  Dostępne endpointy:                                         ║
║  • direct:send-message     - Wysyłanie wiadomości            ║
║  • direct:receive-messages - Odbieranie wiadomości           ║
║  • direct:sync-to-imap     - Synchronizacja do IMAP          ║
║  • direct:sync-from-imap   - Synchronizacja z IMAP           ║
╚══════════════════════════════════════════════════════════════╝
"""
        main.run(args)
    }
}
