/**
 * e-Doręczenia DSL - Groovy Route Definition
 * 
 * Ten plik definiuje przepływy wiadomości w formie DSL.
 * Może być ładowany dynamicznie przez Apache Camel.
 * 
 * Użycie:
 *   camel run edoreczenia.groovy
 */

// ═══════════════════════════════════════════════════════════════════════════
// KONFIGURACJA
// ═══════════════════════════════════════════════════════════════════════════

def config = [
    api: [
        baseUrl: '{{env:EDORECZENIA_API_URL:http://localhost:8180}}',
        address: '{{env:EDORECZENIA_ADDRESS:AE:PL-12345-67890-ABCDE-12}}',
        clientId: '{{env:EDORECZENIA_CLIENT_ID:test_client_id}}',
        clientSecret: '{{env:EDORECZENIA_CLIENT_SECRET:test_client_secret}}'
    ],
    proxy: [
        imapHost: '{{env:PROXY_IMAP_HOST:localhost}}',
        imapPort: '{{env:PROXY_IMAP_PORT:11143}}',
        smtpHost: '{{env:PROXY_SMTP_HOST:localhost}}',
        smtpPort: '{{env:PROXY_SMTP_PORT:11025}}',
        user: '{{env:PROXY_USER:testuser}}',
        password: '{{env:PROXY_PASSWORD:testpass123}}'
    ],
    sync: [
        imapHost: '{{env:SYNC_IMAP_HOST:localhost}}',
        imapPort: '{{env:SYNC_IMAP_PORT:21143}}',
        user: '{{env:SYNC_USER:mailuser}}',
        password: '{{env:SYNC_PASSWORD:mailpass123}}'
    ]
]

// ═══════════════════════════════════════════════════════════════════════════
// DSL ROUTES
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Route: Wysyłanie wiadomości e-Doręczenia
 * 
 * Przykład użycia:
 *   producerTemplate.sendBodyAndHeaders('direct:edoreczenia-send', content, [
 *       'recipient': 'AE:PL-ODBIORCA-00001',
 *       'subject': 'Tytuł wiadomości'
 *   ])
 */
from('direct:edoreczenia-send')
    .routeId('edoreczenia-send')
    .description('Wysyłanie wiadomości przez API e-Doręczeń')
    .log('📤 [SEND] Rozpoczęcie wysyłania: ${header.subject}')
    
    // Krok 1: Pobranie tokenu OAuth2
    .to('direct:edoreczenia-auth')
    
    // Krok 2: Przygotowanie wiadomości
    .process { exchange ->
        def body = exchange.in.body
        def message = [
            subject: exchange.in.getHeader('subject') ?: 'Wiadomość e-Doręczenia',
            recipients: [[
                address: exchange.in.getHeader('recipient'),
                name: exchange.in.getHeader('recipientName') ?: 'Odbiorca'
            ]],
            content: body instanceof String ? body : body?.content,
            contentHtml: body?.contentHtml,
            attachments: body?.attachments ?: []
        ]
        exchange.in.body = groovy.json.JsonOutput.toJson(message)
    }
    
    // Krok 3: Wysłanie do API
    .setHeader('Content-Type', constant('application/json'))
    .setHeader('CamelHttpMethod', constant('POST'))
    .toD("${config.api.baseUrl}/ua/v5/${config.api.address}/messages")
    
    .log('📤 [SEND] Wiadomość wysłana pomyślnie')

/**
 * Route: Odbieranie wiadomości e-Doręczenia
 */
from('direct:edoreczenia-receive')
    .routeId('edoreczenia-receive')
    .description('Odbieranie wiadomości z API e-Doręczeń')
    .log('📥 [RECEIVE] Pobieranie wiadomości...')
    
    .to('direct:edoreczenia-auth')
    
    .setHeader('CamelHttpMethod', constant('GET'))
    .toD("${config.api.baseUrl}/ua/v5/${config.api.address}/messages?folder=inbox&limit=50")
    
    .unmarshal().json()
    .setBody(simple('${body[messages]}'))
    
    .log('📥 [RECEIVE] Pobrano ${body.size()} wiadomości')

/**
 * Route: Autoryzacja OAuth2
 */
from('direct:edoreczenia-auth')
    .routeId('edoreczenia-auth')
    .description('Pobieranie tokenu OAuth2')
    
    .setHeader('Content-Type', constant('application/x-www-form-urlencoded'))
    .setHeader('CamelHttpMethod', constant('POST'))
    .setBody(constant("grant_type=client_credentials&client_id=${config.api.clientId}&client_secret=${config.api.clientSecret}"))
    
    .toD("${config.api.baseUrl}/oauth/token")
    
    .unmarshal().json()
    .setHeader('Authorization', simple('Bearer ${body[access_token]}'))
    .setBody(constant(null))

/**
 * Route: Synchronizacja API → IMAP (Dovecot)
 */
from('direct:edoreczenia-sync-to-imap')
    .routeId('edoreczenia-sync-to-imap')
    .description('Synchronizacja wiadomości z API do serwera IMAP')
    .log('🔄 [SYNC] API → IMAP rozpoczęta')
    
    .to('direct:edoreczenia-receive')
    
    .split(body())
        .log('🔄 [SYNC] Przetwarzanie: ${body[subject]}')
        .process { exchange ->
            def msg = exchange.in.body
            exchange.in.body = """From: ${msg.sender?.address ?: 'system@edoreczenia.gov.pl'}
To: ${config.api.address}
Subject: ${msg.subject ?: '(brak tematu)'}
Date: ${msg.receivedAt ?: new Date()}
Content-Type: text/plain; charset=UTF-8
X-EDoreczenia-ID: ${msg.messageId}
X-EDoreczenia-Status: ${msg.status}

${msg.content ?: msg.contentHtml ?: '(brak treści)'}
"""
        }
        // Zapis do IMAP
        .log('🔄 [SYNC] Zapisywanie do IMAP...')
    .end()
    
    .log('🔄 [SYNC] API → IMAP zakończona')

/**
 * Route: Wysyłanie przez SMTP Proxy
 */
from('direct:edoreczenia-smtp-send')
    .routeId('edoreczenia-smtp-send')
    .description('Wysyłanie wiadomości przez SMTP Proxy e-Doręczeń')
    .log('📤 [SMTP] Wysyłanie: ${header.subject}')
    
    .setHeader('From', simple('${header.from}'))
    .setHeader('To', simple('${header.to}'))
    .setHeader('Subject', simple('${header.subject}'))
    
    .toD("smtp://${config.proxy.smtpHost}:${config.proxy.smtpPort}?username=${config.proxy.user}&password=${config.proxy.password}")
    
    .log('📤 [SMTP] Wysłano pomyślnie')

/**
 * Route: Odbieranie przez IMAP Proxy
 */
from('direct:edoreczenia-imap-receive')
    .routeId('edoreczenia-imap-receive')
    .description('Odbieranie wiadomości przez IMAP Proxy e-Doręczeń')
    .log('📥 [IMAP] Odbieranie z Proxy...')
    
    .pollEnrich("imap://${config.proxy.imapHost}:${config.proxy.imapPort}?username=${config.proxy.user}&password=${config.proxy.password}&folderName=INBOX")
    
    .choice()
        .when(body().isNotNull())
            .log('📥 [IMAP] Odebrano: ${header.Subject}')
        .otherwise()
            .log('📥 [IMAP] Brak nowych wiadomości')
    .end()

/**
 * Route: Odbieranie zsynchronizowanych z Dovecot
 */
from('direct:edoreczenia-dovecot-receive')
    .routeId('edoreczenia-dovecot-receive')
    .description('Odbieranie zsynchronizowanych wiadomości z Dovecot')
    .log('📥 [DOVECOT] Odbieranie zsynchronizowanych...')
    
    .pollEnrich("imap://${config.sync.imapHost}:${config.sync.imapPort}?username=${config.sync.user}&password=${config.sync.password}&folderName=INBOX.e-Doreczenia")
    
    .choice()
        .when(body().isNotNull())
            .log('📥 [DOVECOT] Odebrano: ${header.Subject}')
        .otherwise()
            .log('📥 [DOVECOT] Brak wiadomości')
    .end()

// ═══════════════════════════════════════════════════════════════════════════
// TIMER ROUTES (opcjonalne)
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Automatyczna synchronizacja co minutę
 */
from('timer:auto-sync?period=60000&delay=10000')
    .routeId('auto-sync-timer')
    .autoStartup('{{env:AUTO_SYNC:false}}')
    .log('⏰ [TIMER] Automatyczna synchronizacja...')
    .to('direct:edoreczenia-sync-to-imap')
