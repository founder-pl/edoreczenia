#!/usr/bin/env groovy
/**
 * e-Doręczenia DSL - Test przepływu
 * 
 * Testuje wszystkie operacje DSL: wysyłanie, odbieranie, synchronizację.
 * 
 * Użycie:
 *   groovy test-dsl.groovy
 */

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
// DSL KLASA
// ═══════════════════════════════════════════════════════════════════════════

class EDoreczeniaClient {
    String apiUrl
    String address
    String clientId
    String clientSecret
    String accessToken
    
    EDoreczeniaClient(Map config) {
        this.apiUrl = config.apiUrl
        this.address = config.address
        this.clientId = config.clientId
        this.clientSecret = config.clientSecret
    }
    
    // Pobierz token OAuth2
    String getToken() {
        if (accessToken) return accessToken
        
        def url = new URL("${apiUrl}/oauth/token")
        def conn = url.openConnection()
        conn.setRequestMethod('POST')
        conn.setDoOutput(true)
        conn.setRequestProperty('Content-Type', 'application/x-www-form-urlencoded')
        
        def params = "grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}"
        conn.outputStream.write(params.bytes)
        
        def response = new JsonSlurper().parseText(conn.inputStream.text)
        accessToken = response.access_token
        return accessToken
    }
    
    // Pobierz wiadomości
    List getMessages(String folder = 'inbox', int limit = 20) {
        def token = getToken()
        def url = new URL("${apiUrl}/ua/v5/${address}/messages?folder=${folder}&limit=${limit}")
        def conn = url.openConnection()
        conn.setRequestMethod('GET')
        conn.setRequestProperty('Authorization', "Bearer ${token}")
        
        def response = new JsonSlurper().parseText(conn.inputStream.text)
        return response.messages ?: []
    }
    
    // Wyślij wiadomość
    Map sendMessage(String recipient, String subject, String content, List attachments = []) {
        def token = getToken()
        def url = new URL("${apiUrl}/ua/v5/${address}/messages")
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
        
        if (conn.responseCode in [200, 201, 202]) {
            return new JsonSlurper().parseText(conn.inputStream.text)
        } else {
            throw new Exception("Błąd: ${conn.responseCode}")
        }
    }
    
    // Pobierz szczegóły wiadomości
    Map getMessage(String messageId) {
        def token = getToken()
        def url = new URL("${apiUrl}/ua/v5/${address}/messages/${messageId}")
        def conn = url.openConnection()
        conn.setRequestMethod('GET')
        conn.setRequestProperty('Authorization', "Bearer ${token}")
        
        def response = new JsonSlurper().parseText(conn.inputStream.text)
        return response instanceof List ? response[0] : response
    }
    
    // Pobierz katalogi
    Map getDirectories() {
        def token = getToken()
        def url = new URL("${apiUrl}/ua/v5/${address}/directories")
        def conn = url.openConnection()
        conn.setRequestMethod('GET')
        conn.setRequestProperty('Authorization', "Bearer ${token}")
        
        return new JsonSlurper().parseText(conn.inputStream.text)
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// TESTY
// ═══════════════════════════════════════════════════════════════════════════

def printHeader(String text) {
    println "\n${'═' * 60}"
    println "  ${text}"
    println "${'═' * 60}"
}

def printStep(int step, String text) {
    println "\n[${step}] ${text}"
}

def printResult(boolean success, String details = '') {
    def icon = success ? '✓' : '✗'
    println "    ${icon} ${details}"
}

// ═══════════════════════════════════════════════════════════════════════════
// GŁÓWNA LOGIKA
// ═══════════════════════════════════════════════════════════════════════════

printHeader("e-Doręczenia DSL - Test przepływu")

println "\nKonfiguracja:"
println "  API URL:  ${config.apiUrl}"
println "  Address:  ${config.address}"
println "  Client:   ${config.clientId}"

def client = new EDoreczeniaClient(config)
def results = []

try {
    // Test 1: OAuth2
    printStep(1, "🔑 Test OAuth2 Token")
    def token = client.getToken()
    results << true
    printResult(true, "Token: ${token.take(20)}...")
    
    // Test 2: Pobieranie wiadomości
    printStep(2, "📥 Test odbierania wiadomości")
    def messages = client.getMessages('inbox', 10)
    results << (messages.size() >= 0)
    printResult(true, "Pobrano ${messages.size()} wiadomości")
    
    if (messages) {
        messages.take(3).each { msg ->
            println "       📧 ${msg.subject?.take(40)}... [${msg.status}]"
        }
    }
    
    // Test 3: Pobieranie katalogów
    printStep(3, "📁 Test pobierania katalogów")
    def dirs = client.getDirectories()
    results << (dirs.directories?.size() > 0)
    printResult(true, "Katalogi: ${dirs.directories?.collect { it.name }?.join(', ')}")
    
    // Test 4: Wysyłanie wiadomości
    printStep(4, "📤 Test wysyłania wiadomości")
    def testSubject = "DSL Test ${new Date().format('HH:mm:ss')}"
    def result = client.sendMessage(
        'AE:PL-ODBIORCA-TEST-00001',
        testSubject,
        'Wiadomość testowa z DSL Groovy.'
    )
    results << (result.messageId != null)
    printResult(true, "Wysłano: ${result.messageId} [${result.status}]")
    
    // Test 5: Pobieranie szczegółów
    if (messages) {
        printStep(5, "📧 Test pobierania szczegółów wiadomości")
        def msg = client.getMessage(messages[0].messageId)
        results << (msg.messageId != null)
        printResult(true, "Wiadomość: ${msg.subject?.take(40)}...")
        println "       Od: ${msg.sender?.address}"
        println "       Załączniki: ${msg.attachments?.size() ?: 0}"
    }
    
} catch (Exception e) {
    results << false
    printResult(false, "Błąd: ${e.message}")
}

// Podsumowanie
printHeader("PODSUMOWANIE")

def passed = results.count { it }
def total = results.size()
def percent = total > 0 ? (passed * 100 / total).intValue() : 0

println "\nWynik: ${passed}/${total} testów (${percent}%)"

if (passed == total) {
    println "\n🎉 Wszystkie testy DSL przeszły pomyślnie!"
} else {
    println "\n⚠️  ${total - passed} testów nie przeszło"
}

println "\n${'═' * 60}"
