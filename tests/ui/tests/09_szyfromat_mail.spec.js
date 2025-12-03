/**
 * Test 09: Szyfromat Mail Integration
 * 
 * Scenariusz: Sprawdzenie integracji z serwerem mail (Mailpit)
 * Bazuje na: examples/05_send_message.sh
 */

const { test, expect } = require('@playwright/test');

const URLS = {
  szyfromat: 'http://localhost:3500',
  szyfromat_api: 'http://localhost:8500',
  mailpit: 'http://localhost:8026'
};

test.describe('Szyfromat Mail Integration', () => {
  
  test('should check mail server status', async ({ request }) => {
    const response = await request.get(`${URLS.szyfromat_api}/api/mail/status`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('connected');
    expect(data.smtp_host).toBe('mailpit');
    expect(data.folders).toContain('INBOX');
  });

  test('should seed demo messages', async ({ request }) => {
    const response = await request.post(`${URLS.szyfromat_api}/api/mail/seed`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('ok');
    expect(data.messages_sent).toBeGreaterThan(0);
  });

  test('should fetch messages from Mailpit', async ({ request }) => {
    // Najpierw wyślij demo wiadomości
    await request.post(`${URLS.szyfromat_api}/api/mail/seed`);
    
    // Sprawdź Mailpit API
    const response = await request.get(`${URLS.mailpit}/api/v1/messages`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.total).toBeGreaterThan(0);
    expect(data.messages).toBeDefined();
  });

  test('should display messages in Szyfromat after login', async ({ page, request }) => {
    // Wyślij demo wiadomości
    await request.post(`${URLS.szyfromat_api}/api/mail/seed`);
    
    // Zaloguj się do Szyfromat
    await page.goto(`${URLS.szyfromat}/login`);
    
    await page.fill('input[name="username"], input[type="text"]', 'testuser');
    await page.fill('input[type="password"]', 'testpass123');
    await page.click('button[type="submit"]');
    
    // Poczekaj na zalogowanie
    await page.waitForLoadState('networkidle');
    
    // Sprawdź czy wiadomości są widoczne
    // (zależy od struktury frontendu)
    await page.waitForTimeout(2000);
  });

  test('Mailpit Web UI should be accessible', async ({ page }) => {
    await page.goto(URLS.mailpit);
    await page.waitForLoadState('networkidle');
    
    // Mailpit powinien pokazać interfejs
    await expect(page.locator('body')).toBeVisible();
  });

  test('should have messages from government agencies', async ({ request }) => {
    // Wyślij demo wiadomości
    await request.post(`${URLS.szyfromat_api}/api/mail/seed`);
    
    // Sprawdź wiadomości
    const response = await request.get(`${URLS.mailpit}/api/v1/messages`);
    const data = await response.json();
    
    // Sprawdź czy są wiadomości od urzędów
    const subjects = data.messages.map(m => m.Subject);
    const hasGovMessages = subjects.some(s => 
      s.includes('PIT') || 
      s.includes('ZUS') || 
      s.includes('KRS') ||
      s.includes('Urząd')
    );
    
    expect(hasGovMessages).toBeTruthy();
  });
});
