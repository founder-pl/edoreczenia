/**
 * Test 07: Detax SSO Integration
 * 
 * Scenariusz: Użytkownik łączy się z Detax przez IDCard.pl
 * Bazuje na: examples/06_ask_detax.sh
 */

const { test, expect } = require('@playwright/test');

const URLS = {
  idcard: 'http://localhost:4100',
  detax: 'http://localhost:3005',
  detaxApi: 'http://localhost:8005'
};

test.describe('Detax SSO Integration', () => {
  
  test('should redirect to Detax with SSO token from IDCard', async ({ page, context }) => {
    // 1. Zaloguj się do IDCard.pl
    await page.goto(`${URLS.idcard}/login`);
    
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    
    // Poczekaj na zalogowanie
    await page.waitForURL(`${URLS.idcard}/`);
    
    // 2. Przejdź do usług
    await page.goto(`${URLS.idcard}/services`);
    await page.waitForLoadState('networkidle');
    
    // 3. Znajdź Detax i kliknij Połącz
    const detaxCard = page.locator('text=Detax AI').first();
    await expect(detaxCard).toBeVisible();
    
    // Kliknij przycisk Połącz dla Detax
    const connectBtn = page.locator('button:has-text("Połącz")').first();
    
    // Oczekuj na nowe okno/tab
    const [newPage] = await Promise.all([
      context.waitForEvent('page'),
      connectBtn.click()
    ]);
    
    // 4. Sprawdź czy nowa strona to Detax z tokenem SSO
    await newPage.waitForLoadState('domcontentloaded');
    const url = newPage.url();
    
    // Token powinien być w URL lub już przetworzony
    expect(url).toContain('localhost:3005');
    
    // 5. Sprawdź czy Detax się załadował
    await expect(newPage.locator('.detax-logo, h1:has-text("detax")')).toBeVisible({ timeout: 10000 });
  });

  test('should handle SSO token in Detax frontend', async ({ page }) => {
    // Symuluj przekierowanie z SSO tokenem
    const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLXRlc3QiLCJlbWFpbCI6InRlc3RAZXhhbXBsZS5jb20iLCJleHAiOjk5OTk5OTk5OTksImlhdCI6MTcwMDAwMDAwMCwiaXNzIjoiZGV0YXgucGwiLCJzc29fZnJvbSI6ImlkY2FyZC5wbCJ9.test';
    
    await page.goto(`${URLS.detax}/?sso_token=${mockToken}`);
    await page.waitForLoadState('domcontentloaded');
    
    // Token powinien być usunięty z URL
    await page.waitForTimeout(1000);
    const currentUrl = page.url();
    expect(currentUrl).not.toContain('sso_token');
    
    // Sprawdź czy token został zapisany w localStorage
    const savedToken = await page.evaluate(() => localStorage.getItem('detax_token'));
    expect(savedToken).toBeTruthy();
  });

  test('should display Detax chat interface', async ({ page }) => {
    await page.goto(URLS.detax);
    await page.waitForLoadState('networkidle');
    
    // Sprawdź elementy interfejsu
    await expect(page.locator('.detax-logo, h1:has-text("detax")')).toBeVisible();
    await expect(page.locator('#messages, .messages')).toBeVisible();
    await expect(page.locator('#user-input, input[placeholder*="pytanie"]')).toBeVisible();
    
    // Sprawdź kanały/moduły
    await expect(page.locator('text=ksef').first()).toBeVisible();
    await expect(page.locator('text=b2b').first()).toBeVisible();
    await expect(page.locator('text=zus').first()).toBeVisible();
    await expect(page.locator('text=vat').first()).toBeVisible();
  });

  test('should send question to Detax AI', async ({ page }) => {
    await page.goto(URLS.detax);
    await page.waitForLoadState('networkidle');
    
    // Wpisz pytanie
    const input = page.locator('#user-input');
    await input.fill('Kiedy KSeF będzie obowiązkowy?');
    
    // Wyślij
    await page.click('#send-btn, button[type="submit"]');
    
    // Poczekaj na odpowiedź (może być wolne jeśli Ollama działa)
    await page.waitForTimeout(2000);
    
    // Sprawdź czy pytanie pojawiło się w czacie
    await expect(page.locator('.message.user, .message:has-text("KSeF")')).toBeVisible({ timeout: 5000 });
  });

  test('Detax API should be accessible', async ({ request }) => {
    const response = await request.get(`${URLS.detaxApi}/health`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('Detax SSO endpoint should work', async ({ request }) => {
    // Utwórz token testowy (w produkcji byłby z IDCard)
    const response = await request.get(`${URLS.detaxApi}/sso?token=invalid&redirect=/`);
    
    // Powinien zwrócić błąd dla nieprawidłowego tokena
    expect(response.status()).toBe(200); // Redirect lub error JSON
  });
});
