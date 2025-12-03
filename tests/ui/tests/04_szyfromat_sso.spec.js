// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Test 04: SSO z IDCard.pl do Szyfromat.pl
 * Testuje Single Sign-On między usługami
 */

test.describe('SSO - Single Sign-On', () => {
  
  test('SSO endpoint accepts valid token', async ({ request }) => {
    // Najpierw pobierz token z IDCard
    const loginResponse = await request.post('http://localhost:4000/api/auth/login', {
      data: {
        email: 'demo@idcard.pl',
        password: 'demo123'
      }
    });
    
    expect(loginResponse.ok()).toBeTruthy();
    const { access_token } = await loginResponse.json();
    expect(access_token).toBeTruthy();
    
    // Sprawdź SSO endpoint
    const ssoResponse = await request.get(`http://localhost:8500/sso?token=${access_token}&redirect=/`, {
      maxRedirects: 0
    });
    
    // Powinien zwrócić redirect (302)
    expect(ssoResponse.status()).toBe(302);
    
    // Location header powinien zawierać sso_token
    const location = ssoResponse.headers()['location'];
    expect(location).toContain('sso_token=');
  });

  test('SSO redirects to Szyfromat with token', async ({ page }) => {
    // Zaloguj się w IDCard
    await page.goto('http://localhost:4100/login');
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('http://localhost:4100/', { timeout: 10000 });
    
    // Przejdź do szczegółów e-Doręczeń
    await page.click('a[href="/services/edoreczenia"]');
    await expect(page).toHaveURL(/.*services\/edoreczenia/);
    
    // Jeśli jest przycisk "Otwórz e-Doręczenia", sprawdź czy ma SSO token w URL
    const openButton = page.locator('text=Otwórz e-Doręczenia');
    if (await openButton.isVisible()) {
      const href = await openButton.getAttribute('href');
      expect(href).toContain('/sso?token=');
    }
  });

  test('Szyfromat accepts SSO token from URL', async ({ page, request }) => {
    // Pobierz token z IDCard
    const loginResponse = await request.post('http://localhost:4000/api/auth/login', {
      data: {
        email: 'demo@idcard.pl',
        password: 'demo123'
      }
    });
    
    const { access_token } = await loginResponse.json();
    
    // Przejdź do Szyfromat z SSO tokenem
    await page.goto(`http://localhost:3500/?sso_token=${access_token}`);
    
    // Powinno zalogować i pokazać inbox (nie login)
    await expect(page).not.toHaveURL(/.*login/, { timeout: 5000 });
  });
});
