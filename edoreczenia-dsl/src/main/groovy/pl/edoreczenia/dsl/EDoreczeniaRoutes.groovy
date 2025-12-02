package pl.edoreczenia.dsl

import org.apache.camel.builder.RouteBuilder
import org.apache.camel.Exchange
import org.apache.camel.model.dataformat.JsonLibrary
import groovy.json.JsonSlurper
import groovy.json.JsonOutput

/**
 * Apache Camel Routes dla e-Doręczeń DSL.
 * Definiuje przepływy wiadomości między API a usługami Docker.
 */
class EDoreczeniaRoutes extends RouteBuilder {
    
    // Konfiguracja z zmiennych środowiskowych
    String apiBaseUrl = System.getenv('EDORECZENIA_API_URL') ?: 'http://localhost:8180'
    String apiAddress = System.getenv('EDORECZENIA_ADDRESS') ?: 'AE:PL-12345-67890-ABCDE-12'
    String clientId = System.getenv('EDORECZENIA_CLIENT_ID') ?: 'test_client_id'
    String clientSecret = System.getenv('EDORECZENIA_CLIENT_SECRET') ?: 'test_client_secret'
    
    String imapHost = System.getenv('IMAP_HOST') ?: 'localhost'
    String imapPort = System.getenv('IMAP_PORT') ?: '21143'
    String imapUser = System.getenv('IMAP_USER') ?: 'mailuser'
    String imapPassword = System.getenv('IMAP_PASSWORD') ?: 'mailpass123'
    
    String smtpHost = System.getenv('SMTP_HOST') ?: 'localhost'
    String smtpPort = System.getenv('SMTP_PORT') ?: '11025'
    String smtpUser = System.getenv('SMTP_USER') ?: 'testuser'
    String smtpPassword = System.getenv('SMTP_PASSWORD') ?: 'testpass123'
    
    // Cache tokenu OAuth2
    String accessToken = null
    long tokenExpiry = 0
    
    @Override
    void configure() throws Exception {
        
        // ═══════════════════════════════════════════════════════════════
        // ERROR HANDLING
        // ═══════════════════════════════════════════════════════════════
        
        onException(Exception.class)
            .handled(true)
            .log('ERROR: ${exception.message}')
            .setHeader(Exchange.HTTP_RESPONSE_CODE, constant(500))
            .setBody(simple('{"error": "${exception.message}"}'))
        
        // ═══════════════════════════════════════════════════════════════
        // OAUTH2 TOKEN
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:get-token')
            .routeId('oauth2-token')
            .log('🔑 Pobieranie tokenu OAuth2...')
            .process { exchange ->
                // Sprawdź czy token jest ważny
                if (accessToken && System.currentTimeMillis() < tokenExpiry) {
                    exchange.message.setHeader('Authorization', "Bearer ${accessToken}")
                    return
                }
                
                // Pobierz nowy token
                def http = new URL("${apiBaseUrl}/oauth/token").openConnection()
                http.setRequestMethod('POST')
                http.setDoOutput(true)
                http.setRequestProperty('Content-Type', 'application/x-www-form-urlencoded')
                
                def params = "grant_type=client_credentials&client_id=${clientId}&client_secret=${clientSecret}"
                http.outputStream.write(params.bytes)
                
                def response = new JsonSlurper().parseText(http.inputStream.text)
                accessToken = response.access_token
                tokenExpiry = System.currentTimeMillis() + (response.expires_in ?: 3600) * 1000 - 60000
                
                exchange.message.setHeader('Authorization', "Bearer ${accessToken}")
            }
            .log('🔑 Token OAuth2 pobrany')
        
        // ═══════════════════════════════════════════════════════════════
        // WYSYŁANIE WIADOMOŚCI (DSL → API)
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:send-message')
            .routeId('send-message')
            .log('📤 Wysyłanie wiadomości: ${header.subject}')
            .to('direct:get-token')
            .process { exchange ->
                def body = exchange.message.body
                def message = [
                    subject: exchange.message.getHeader('subject') ?: body?.subject ?: 'Wiadomość e-Doręczenia',
                    recipients: [[
                        address: exchange.message.getHeader('recipient') ?: body?.recipient,
                        name: exchange.message.getHeader('recipientName') ?: body?.recipientName ?: 'Odbiorca'
                    ]],
                    content: body?.content ?: body?.toString() ?: '',
                    contentHtml: body?.contentHtml,
                    attachments: body?.attachments ?: []
                ]
                exchange.message.body = JsonOutput.toJson(message)
            }
            .setHeader(Exchange.HTTP_METHOD, constant('POST'))
            .setHeader(Exchange.CONTENT_TYPE, constant('application/json'))
            .toD("${apiBaseUrl}/ua/v5/${apiAddress}/messages")
            .log('📤 Wiadomość wysłana: ${body}')
        
        // ═══════════════════════════════════════════════════════════════
        // ODBIERANIE WIADOMOŚCI (API → DSL)
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:receive-messages')
            .routeId('receive-messages')
            .log('📥 Pobieranie wiadomości z API...')
            .to('direct:get-token')
            .setHeader(Exchange.HTTP_METHOD, constant('GET'))
            .toD("${apiBaseUrl}/ua/v5/${apiAddress}/messages?folder=inbox&limit=50")
            .unmarshal().json(JsonLibrary.Jackson)
            .process { exchange ->
                def response = exchange.message.body
                def messages = response?.messages ?: []
                log.info("📥 Pobrano ${messages.size()} wiadomości")
                exchange.message.body = messages
            }
        
        // ═══════════════════════════════════════════════════════════════
        // POBIERANIE SZCZEGÓŁÓW WIADOMOŚCI
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:get-message')
            .routeId('get-message')
            .log('📧 Pobieranie wiadomości: ${header.messageId}')
            .to('direct:get-token')
            .setHeader(Exchange.HTTP_METHOD, constant('GET'))
            .toD("${apiBaseUrl}/ua/v5/${apiAddress}/messages/\${header.messageId}")
            .unmarshal().json(JsonLibrary.Jackson)
        
        // ═══════════════════════════════════════════════════════════════
        // POBIERANIE ZAŁĄCZNIKA
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:get-attachment')
            .routeId('get-attachment')
            .log('📎 Pobieranie załącznika: ${header.attachmentId}')
            .to('direct:get-token')
            .setHeader(Exchange.HTTP_METHOD, constant('GET'))
            .toD("${apiBaseUrl}/ua/v5/${apiAddress}/messages/\${header.messageId}/attachments/\${header.attachmentId}")
        
        // ═══════════════════════════════════════════════════════════════
        // SYNCHRONIZACJA DO IMAP (API → Dovecot)
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:sync-to-imap')
            .routeId('sync-to-imap')
            .log('🔄 Synchronizacja API → IMAP...')
            .to('direct:receive-messages')
            .split(body())
                .log('🔄 Synchronizacja wiadomości: ${body[subject]}')
                .process { exchange ->
                    def msg = exchange.message.body
                    def emailContent = """From: ${msg.sender?.address ?: 'noreply@edoreczenia.gov.pl'}
To: ${apiAddress}
Subject: ${msg.subject ?: '(brak tematu)'}
Date: ${msg.receivedAt ?: new Date().toString()}
Content-Type: text/plain; charset=UTF-8
X-EDoreczenia-ID: ${msg.messageId}

${msg.content ?: msg.contentHtml ?: ''}
"""
                    exchange.message.body = emailContent
                    exchange.message.setHeader('folderName', 'INBOX.e-Doreczenia')
                }
                .toD("imap://${imapHost}:${imapPort}?username=${imapUser}&password=${imapPassword}&folderName=INBOX.e-Doreczenia&unseen=false")
            .end()
            .log('🔄 Synchronizacja zakończona')
        
        // ═══════════════════════════════════════════════════════════════
        // SYNCHRONIZACJA Z IMAP (Dovecot → API)
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:sync-from-imap')
            .routeId('sync-from-imap')
            .log('🔄 Synchronizacja IMAP → API...')
            .pollEnrich()
                .simple("imap://${imapHost}:${imapPort}?username=${imapUser}&password=${imapPassword}&folderName=e-Doreczenia-Wyslij&unseen=true&delete=false")
            .choice()
                .when(body().isNotNull())
                    .log('🔄 Znaleziono wiadomość do wysłania')
                    .process { exchange ->
                        def mail = exchange.message
                        def body = [
                            subject: mail.getHeader('Subject') ?: 'Wiadomość',
                            recipient: mail.getHeader('To'),
                            content: mail.body?.toString() ?: ''
                        ]
                        exchange.message.body = body
                        exchange.message.setHeader('subject', body.subject)
                        exchange.message.setHeader('recipient', body.recipient)
                    }
                    .to('direct:send-message')
                .otherwise()
                    .log('🔄 Brak nowych wiadomości do wysłania')
            .end()
        
        // ═══════════════════════════════════════════════════════════════
        // WYSYŁANIE PRZEZ SMTP PROXY
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:send-via-smtp')
            .routeId('send-via-smtp')
            .log('📤 Wysyłanie przez SMTP: ${header.subject}')
            .setHeader('From', simple('${header.from}'))
            .setHeader('To', simple('${header.to}'))
            .setHeader('Subject', simple('${header.subject}'))
            .toD("smtp://${smtpHost}:${smtpPort}?username=${smtpUser}&password=${smtpPassword}")
            .log('📤 Wiadomość wysłana przez SMTP')
        
        // ═══════════════════════════════════════════════════════════════
        // ODBIERANIE PRZEZ IMAP PROXY
        // ═══════════════════════════════════════════════════════════════
        
        from('direct:receive-via-imap')
            .routeId('receive-via-imap')
            .log('📥 Odbieranie przez IMAP Proxy...')
            .pollEnrich()
                .simple("imap://${smtpHost}:11143?username=${smtpUser}&password=${smtpPassword}&folderName=INBOX&unseen=true")
            .choice()
                .when(body().isNotNull())
                    .log('📥 Odebrano wiadomość: ${header.Subject}')
                .otherwise()
                    .log('📥 Brak nowych wiadomości')
            .end()
        
        // ═══════════════════════════════════════════════════════════════
        // TIMER - AUTOMATYCZNA SYNCHRONIZACJA
        // ═══════════════════════════════════════════════════════════════
        
        from('timer:sync?period=60000&delay=5000')
            .routeId('auto-sync')
            .autoStartup(System.getenv('AUTO_SYNC') == 'true')
            .log('⏰ Automatyczna synchronizacja...')
            .to('direct:sync-to-imap')
        
        // ═══════════════════════════════════════════════════════════════
        // FILE WATCHER - WYSYŁANIE PLIKÓW
        // ═══════════════════════════════════════════════════════════════
        
        from('file:outbox?noop=false&delete=true&include=.*\\.(pdf|xml|txt)')
            .routeId('file-sender')
            .autoStartup(System.getenv('FILE_WATCH') == 'true')
            .log('📁 Nowy plik do wysłania: ${header.CamelFileName}')
            .process { exchange ->
                def fileName = exchange.message.getHeader('CamelFileName')
                def content = exchange.message.body
                
                // Przygotuj załącznik
                def attachment = [
                    filename: fileName,
                    contentType: getMimeType(fileName),
                    content: content.bytes.encodeBase64().toString()
                ]
                
                exchange.message.body = [
                    subject: "Dokument: ${fileName}",
                    recipient: System.getenv('DEFAULT_RECIPIENT') ?: 'AE:PL-ODBIORCA-00001',
                    content: "W załączeniu przesyłam dokument: ${fileName}",
                    attachments: [attachment]
                ]
                exchange.message.setHeader('subject', "Dokument: ${fileName}")
                exchange.message.setHeader('recipient', System.getenv('DEFAULT_RECIPIENT') ?: 'AE:PL-ODBIORCA-00001')
            }
            .to('direct:send-message')
            .log('📁 Plik wysłany: ${header.CamelFileName}')
        
        // ═══════════════════════════════════════════════════════════════
        // REST API ENDPOINT
        // ═══════════════════════════════════════════════════════════════
        
        restConfiguration()
            .component('netty-http')
            .host('0.0.0.0')
            .port(8090)
            .bindingMode('json')
        
        rest('/api/v1')
            .post('/messages')
                .to('direct:send-message')
            .get('/messages')
                .to('direct:receive-messages')
            .get('/messages/{messageId}')
                .to('direct:get-message')
            .post('/sync/to-imap')
                .to('direct:sync-to-imap')
            .post('/sync/from-imap')
                .to('direct:sync-from-imap')
    }
    
    static String getMimeType(String fileName) {
        if (fileName.endsWith('.pdf')) return 'application/pdf'
        if (fileName.endsWith('.xml')) return 'application/xml'
        if (fileName.endsWith('.txt')) return 'text/plain'
        if (fileName.endsWith('.doc') || fileName.endsWith('.docx')) return 'application/msword'
        return 'application/octet-stream'
    }
}
