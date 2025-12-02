/**
 * e-Doręczenia DSL - Wysyłanie dokumentu
 * 
 * Przykład wysłania dokumentu PDF przez API e-Doręczeń.
 * 
 * Użycie:
 *   groovy send-document.groovy --file dokument.pdf --recipient AE:PL-ODBIORCA-00001
 */

@Grab('org.apache.camel:camel-core:4.4.0')
@Grab('org.apache.camel:camel-http:4.4.0')
@Grab('org.apache.camel:camel-jackson:4.4.0')

import org.apache.camel.impl.DefaultCamelContext
import org.apache.camel.builder.RouteBuilder
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

/**
 * Pobiera token OAuth2
 */
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

/**
 * Wysyła wiadomość z załącznikiem
 */
def sendMessage(config, token, recipient, subject, content, attachments = []) {
    def url = new URL("${config.apiUrl}/ua/v5/${config.address}/messages")
    def conn = url.openConnection()
    conn.setRequestMethod('POST')
    conn.setDoOutput(true)
    conn.setRequestProperty('Content-Type', 'application/json')
    conn.setRequestProperty('Authorization', "Bearer ${token}")
    
    def message = [
        subject: subject,
        recipients: [[address: recipient, name: 'Odbiorca']],
        content: content,
        attachments: attachments
    ]
    
    conn.outputStream.write(JsonOutput.toJson(message).bytes)
    
    if (conn.responseCode == 202 || conn.responseCode == 200) {
        return new JsonSlurper().parseText(conn.inputStream.text)
    } else {
        throw new Exception("Błąd wysyłania: ${conn.responseCode} - ${conn.errorStream?.text}")
    }
}

/**
 * Przygotowuje załącznik z pliku
 */
def prepareAttachment(File file) {
    def mimeType = file.name.endsWith('.pdf') ? 'application/pdf' :
                   file.name.endsWith('.xml') ? 'application/xml' :
                   file.name.endsWith('.txt') ? 'text/plain' :
                   'application/octet-stream'
    
    return [
        filename: file.name,
        contentType: mimeType,
        content: file.bytes.encodeBase64().toString()
    ]
}

// ═══════════════════════════════════════════════════════════════════════════
// GŁÓWNA LOGIKA
// ═══════════════════════════════════════════════════════════════════════════

def cli = new CliBuilder(usage: 'send-document.groovy [options]')
cli.with {
    h(longOpt: 'help', 'Wyświetl pomoc')
    f(longOpt: 'file', args: 1, 'Plik do wysłania')
    r(longOpt: 'recipient', args: 1, 'Adres odbiorcy (AE:PL-...)')
    s(longOpt: 'subject', args: 1, 'Temat wiadomości')
    c(longOpt: 'content', args: 1, 'Treść wiadomości')
}

def options = cli.parse(args)

if (options.h || !options.r) {
    cli.usage()
    println """
Przykład:
  groovy send-document.groovy -f dokument.pdf -r AE:PL-ODBIORCA-00001 -s "Ważny dokument"

Zmienne środowiskowe:
  EDORECZENIA_API_URL      - URL API (domyślnie: http://localhost:8180)
  EDORECZENIA_ADDRESS      - Adres nadawcy
  EDORECZENIA_CLIENT_ID    - Client ID OAuth2
  EDORECZENIA_CLIENT_SECRET - Client Secret OAuth2
"""
    return
}

println "═══════════════════════════════════════════════════════════════"
println "  e-Doręczenia DSL - Wysyłanie dokumentu"
println "═══════════════════════════════════════════════════════════════"

try {
    // 1. Pobierz token
    println "\n[1] 🔑 Pobieranie tokenu OAuth2..."
    def token = getToken(config)
    println "    ✓ Token pobrany: ${token.take(20)}..."
    
    // 2. Przygotuj załączniki
    def attachments = []
    if (options.f) {
        println "\n[2] 📎 Przygotowywanie załącznika..."
        def file = new File(options.f)
        if (file.exists()) {
            attachments << prepareAttachment(file)
            println "    ✓ Załącznik: ${file.name} (${file.length()} bajtów)"
        } else {
            println "    ⚠ Plik nie istnieje: ${options.f}"
        }
    }
    
    // 3. Wyślij wiadomość
    println "\n[3] 📤 Wysyłanie wiadomości..."
    def subject = options.s ?: "Dokument: ${options.f ?: 'wiadomość'}"
    def content = options.c ?: "W załączeniu przesyłam dokument."
    
    def result = sendMessage(config, token, options.r, subject, content, attachments)
    
    println "    ✓ Wiadomość wysłana!"
    println "    └─ ID: ${result.messageId}"
    println "    └─ Status: ${result.status}"
    
    println "\n═══════════════════════════════════════════════════════════════"
    println "  ✅ Dokument wysłany pomyślnie"
    println "═══════════════════════════════════════════════════════════════"
    
} catch (Exception e) {
    println "\n❌ Błąd: ${e.message}"
    e.printStackTrace()
}
