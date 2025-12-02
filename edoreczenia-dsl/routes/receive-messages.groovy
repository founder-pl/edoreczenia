/**
 * e-Doręczenia DSL - Odbieranie wiadomości
 * 
 * Pobiera wiadomości z API e-Doręczeń i wyświetla je.
 * 
 * Użycie:
 *   groovy receive-messages.groovy [--folder inbox|sent] [--limit 10]
 */

@Grab('org.apache.camel:camel-core:4.4.0')
@Grab('org.apache.camel:camel-http:4.4.0')

import groovy.json.JsonSlurper
import groovy.json.JsonOutput

// ═══════════════════════════════════════════════════════════════════════════
// KONFIGURACJA
// ═══════════════════════════════════════════════════════════════════════════

def config = [
    apiUrl: System.getenv('EDORECZENIA_API_URL') ?: 'http://localhost:8180',
    address: System.getenv('EDORECZENIA_ADDRESS') ?: 'AE:PL-12345-67890-ABCDE-12',
    clientId: System.getenv('EDORECZENIA_CLIENT_ID') ?: 'test_client_id',
    clientSecret: System.getenv('EDORECZENIA_CLIENT_SECRET') ?: 'test_client_secret'
]

// ═══════════════════════════════════════════════════════════════════════════
// DSL FUNKCJE
// ═══════════════════════════════════════════════════════════════════════════

def getToken(config) {
    def url = new URL("${config.apiUrl}/oauth/token")
    def conn = url.openConnection()
    conn.setRequestMethod('POST')
    conn.setDoOutput(true)
    conn.setRequestProperty('Content-Type', 'application/x-www-form-urlencoded')
    
    def params = "grant_type=client_credentials&client_id=${config.clientId}&client_secret=${config.clientSecret}"
    conn.outputStream.write(params.bytes)
    
    def response = new JsonSlurper().parseText(conn.inputStream.text)
    return response.access_token
}

def getMessages(config, token, folder = 'inbox', limit = 20) {
    def url = new URL("${config.apiUrl}/ua/v5/${config.address}/messages?folder=${folder}&limit=${limit}")
    def conn = url.openConnection()
    conn.setRequestMethod('GET')
    conn.setRequestProperty('Authorization', "Bearer ${token}")
    
    def response = new JsonSlurper().parseText(conn.inputStream.text)
    return response.messages ?: []
}

def getMessage(config, token, messageId) {
    def url = new URL("${config.apiUrl}/ua/v5/${config.address}/messages/${messageId}")
    def conn = url.openConnection()
    conn.setRequestMethod('GET')
    conn.setRequestProperty('Authorization', "Bearer ${token}")
    
    def response = new JsonSlurper().parseText(conn.inputStream.text)
    return response instanceof List ? response[0] : response
}

// ═══════════════════════════════════════════════════════════════════════════
// GŁÓWNA LOGIKA
// ═══════════════════════════════════════════════════════════════════════════

def cli = new CliBuilder(usage: 'receive-messages.groovy [options]')
cli.with {
    h(longOpt: 'help', 'Wyświetl pomoc')
    f(longOpt: 'folder', args: 1, 'Folder (inbox/sent/drafts)')
    l(longOpt: 'limit', args: 1, 'Limit wiadomości')
    d(longOpt: 'details', args: 1, 'Pokaż szczegóły wiadomości (ID)')
    j(longOpt: 'json', 'Wyświetl jako JSON')
}

def options = cli.parse(args)

if (options.h) {
    cli.usage()
    println """
Przykład:
  groovy receive-messages.groovy -f inbox -l 10
  groovy receive-messages.groovy -d msg-001

Zmienne środowiskowe:
  EDORECZENIA_API_URL      - URL API (domyślnie: http://localhost:8180)
  EDORECZENIA_ADDRESS      - Adres e-Doręczeń
  EDORECZENIA_CLIENT_ID    - Client ID OAuth2
  EDORECZENIA_CLIENT_SECRET - Client Secret OAuth2
"""
    return
}

println "═══════════════════════════════════════════════════════════════"
println "  e-Doręczenia DSL - Odbieranie wiadomości"
println "═══════════════════════════════════════════════════════════════"

try {
    // 1. Pobierz token
    println "\n[1] 🔑 Pobieranie tokenu OAuth2..."
    def token = getToken(config)
    println "    ✓ Token pobrany"
    
    if (options.d) {
        // Szczegóły pojedynczej wiadomości
        println "\n[2] 📧 Pobieranie szczegółów wiadomości: ${options.d}"
        def msg = getMessage(config, token, options.d)
        
        if (options.j) {
            println JsonOutput.prettyPrint(JsonOutput.toJson(msg))
        } else {
            println """
┌─────────────────────────────────────────────────────────────────
│ ID:        ${msg.messageId}
│ Temat:     ${msg.subject}
│ Od:        ${msg.sender?.name} <${msg.sender?.address}>
│ Do:        ${msg.recipients?.collect { it.address }?.join(', ')}
│ Data:      ${msg.receivedAt}
│ Status:    ${msg.status}
│ Załączniki: ${msg.attachments?.size() ?: 0}
├─────────────────────────────────────────────────────────────────
│ Treść:
│ ${msg.content?.take(500) ?: '(brak)'}
└─────────────────────────────────────────────────────────────────
"""
        }
    } else {
        // Lista wiadomości
        def folder = options.f ?: 'inbox'
        def limit = options.l ? options.l.toInteger() : 20
        
        println "\n[2] 📥 Pobieranie wiadomości z folderu: ${folder}"
        def messages = getMessages(config, token, folder, limit)
        
        println "    ✓ Pobrano ${messages.size()} wiadomości\n"
        
        if (options.j) {
            println JsonOutput.prettyPrint(JsonOutput.toJson(messages))
        } else {
            println "┌────────────────┬────────────────────────────────────────────────────┬─────────────┐"
            println "│ ID             │ Temat                                              │ Status      │"
            println "├────────────────┼────────────────────────────────────────────────────┼─────────────┤"
            
            messages.each { msg ->
                def id = (msg.messageId ?: '').padRight(14).take(14)
                def subject = (msg.subject ?: '(brak)').padRight(50).take(50)
                def status = (msg.status ?: '').padRight(11).take(11)
                println "│ ${id} │ ${subject} │ ${status} │"
            }
            
            println "└────────────────┴────────────────────────────────────────────────────┴─────────────┘"
        }
    }
    
    println "\n═══════════════════════════════════════════════════════════════"
    println "  ✅ Zakończono"
    println "═══════════════════════════════════════════════════════════════"
    
} catch (Exception e) {
    println "\n❌ Błąd: ${e.message}"
    e.printStackTrace()
}
