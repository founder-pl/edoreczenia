// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Test 03: Połączenie z usługami
 * Odpowiednik: examples/04_connect_szyfromat.sh
 */

test.describe('Services Connection', () => {
  
  test.beforeEach(async ({ page }) => {
    // Zaloguj się przed każdym testem
    await page.goto('http://localhost:4100/login');
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('http://localhost:4100/', { timeout: 10000 });
  });

  test('Can view services list', async ({ page }) => {
    // Przejdź do usług
    await page.click('text=Usługi');
    await expect(page).toHaveURL(/.*services/);
    
    // Sprawdź czy widoczne są usługi
    await expect(page.locator('text=e-Doręczenia')).toBeVisible();
    await expect(page.locator('text=Detax AI')).toBeVisible();
  });

  test('Can navigate to e-Doręczenia service detail', async ({ page }) => {
    // Kliknij kafelek e-Doręczenia na dashboardzie
    await page.click('a[href="/services/edoreczenia"]');
    
    await expect(page).toHaveURL(/.*services\/edoreczenia/);
    await expect(page.locator('text=e-Doręczenia')).toBeVisible();
    await expect(page.locator('text=Status połączenia')).toBeVisible();
  });

  test('Can navigate to Detax service detail', async ({ page }) => {
    await page.click('a[href="/services/detax"]');
    
    await expect(page).toHaveURL(/.*services\/detax/);
    await expect(page.locator('text=Detax AI')).toBeVisible();
  });

  test('Dashboard shows service status', async ({ page }) => {
    // Na dashboardzie powinny być widoczne kafelki usług
    await expect(page.locator('text=e-Doręczenia')).toBeVisible();
    await expect(page.locator('text=szyfromat.pl')).toBeVisible();
    
    // Status powinien być widoczny (Połączono, Oczekuje lub Niepołączono)
    const statusBadge = page.locator('.rounded-full').first();
    await expect(statusBadge).toBeVisible();
  });
});
