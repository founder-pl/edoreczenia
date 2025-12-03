// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Test 05: Pełna ścieżka użytkownika
 * Odpowiednik: examples/07_full_demo.sh
 */

test.describe('Full User Journey', () => {
  
  test('Complete user flow: Register -> Connect Services -> Use AI', async ({ page, request }) => {
    const timestamp = Date.now();
    const testEmail = `journey.${timestamp}@test.pl`;
    
    // ═══════════════════════════════════════════════════════════════
    // KROK 1: Rejestracja w IDCard.pl
    // ═══════════════════════════════════════════════════════════════
    
    await test.step('Register in IDCard.pl', async () => {
      await page.goto('http://localhost:4100/login');
      await page.click('text=Nie masz konta? Zarejestruj się');
      
      await page.fill('input[type="text"]', 'Journey Test User');
      await page.fill('input[type="email"]', testEmail);
      await page.fill('input[type="password"]', 'Test123!');
      
      await page.click('button[type="submit"]');
      
      await expect(page).toHaveURL('http://localhost:4100/', { timeout: 10000 });
      await expect(page.locator('text=Dashboard')).toBeVisible();
    });
    
    // ═══════════════════════════════════════════════════════════════
    // KROK 2: Sprawdzenie dostępnych usług
    // ═══════════════════════════════════════════════════════════════
    
    await test.step('View available services', async () => {
      await page.click('text=Usługi');
      await expect(page).toHaveURL(/.*services/);
      
      // Sprawdź czy widoczne są wszystkie usługi
      await expect(page.locator('text=e-Doręczenia')).toBeVisible();
      await expect(page.locator('text=Detax AI')).toBeVisible();
    });
    
    // ═══════════════════════════════════════════════════════════════
    // KROK 3: Przejście do szczegółów e-Doręczeń
    // ═══════════════════════════════════════════════════════════════
    
    await test.step('Navigate to e-Doręczenia details', async () => {
      // Wróć na dashboard
      await page.click('text=Dashboard');
      await expect(page).toHaveURL('http://localhost:4100/');
      
      // Kliknij kafelek e-Doręczenia
      await page.click('a[href="/services/edoreczenia"]');
      await expect(page).toHaveURL(/.*services\/edoreczenia/);
      
      await expect(page.locator('text=e-Doręczenia')).toBeVisible();
      await expect(page.locator('text=Status połączenia')).toBeVisible();
    });
    
    // ═══════════════════════════════════════════════════════════════
    // KROK 4: Sprawdzenie Detax.pl
    // ═══════════════════════════════════════════════════════════════
    
    await test.step('Check Detax.pl AI', async () => {
      // Sprawdź API Detax
      const response = await request.post('http://localhost:8005/api/v1/chat', {
        data: {
          message: 'Cześć, kim jesteś?',
          model: 'llama3.1:8b'
        }
      });
      
      if (response.ok()) {
        const data = await response.json();
        expect(data.response).toBeTruthy();
        expect(data.response.length).toBeGreaterThan(10);
      }
    });
    
    // ═══════════════════════════════════════════════════════════════
    // KROK 5: Sprawdzenie skrzynki odbiorczej
    // ═══════════════════════════════════════════════════════════════
    
    await test.step('Check unified inbox', async () => {
      await page.click('text=Skrzynka');
      await expect(page).toHaveURL(/.*inbox/);
      
      // Skrzynka może być pusta lub mieć wiadomości
      const inboxContent = page.locator('main');
      await expect(inboxContent).toBeVisible();
    });
    
    // ═══════════════════════════════════════════════════════════════
    // KROK 6: Wylogowanie
    // ═══════════════════════════════════════════════════════════════
    
    await test.step('Logout', async () => {
      await page.click('text=Wyloguj');
      await expect(page).toHaveURL(/.*login/);
    });
  });
});
