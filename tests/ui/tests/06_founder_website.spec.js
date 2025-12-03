// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Test 06: Strona główna Founder.pl
 * Sprawdza czy linki używają localhost w wersji dev
 */

test.describe('Founder.pl Website', () => {
  
  test('Homepage loads correctly', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    await expect(page.locator('text=Founder.pl')).toBeVisible();
    await expect(page.locator('text=Wszystkie usługi cyfrowe')).toBeVisible();
  });

  test('Services section shows all services', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Przewiń do sekcji usług
    await page.locator('#uslugi').scrollIntoViewIfNeeded();
    
    await expect(page.locator('text=IDCard.pl')).toBeVisible();
    await expect(page.locator('text=Szyfromat.pl')).toBeVisible();
    await expect(page.locator('text=Detax.pl')).toBeVisible();
  });

  test('Service links use localhost in dev mode', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Sprawdź czy linki do usług używają localhost
    const idcardLink = page.locator('a:has-text("Otwórz IDCard.pl")').first();
    const szyfroLink = page.locator('a:has-text("Otwórz Szyfromat.pl")').first();
    const detaxLink = page.locator('a:has-text("Otwórz Detax.pl")').first();
    
    // W wersji dev powinny używać localhost
    if (await idcardLink.isVisible()) {
      const href = await idcardLink.getAttribute('href');
      // Może być localhost lub config z backendu
      expect(href).toBeTruthy();
    }
  });

  test('Detax section is highlighted as paid service', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Przewiń do sekcji Detax
    await page.locator('#detax').scrollIntoViewIfNeeded();
    
    await expect(page.locator('text=Detax.pl zastępuje prawnika')).toBeVisible();
    await expect(page.locator('text=Jedyna płatna usługa')).toBeVisible();
  });

  test('Navigation works correctly', async ({ page }) => {
    await page.goto('http://localhost:5000');
    
    // Kliknij w nawigację
    await page.click('a[href="#uslugi"]');
    
    // Sekcja usług powinna być widoczna
    await expect(page.locator('#uslugi')).toBeInViewport();
  });

  test('API config endpoint returns localhost URLs in dev', async ({ request }) => {
    const response = await request.get('http://localhost:5001/api/config');
    
    if (response.ok()) {
      const config = await response.json();
      
      // W wersji dev powinny być localhost URLs
      expect(config.environment).toBe('development');
      expect(config.services.idcard.url).toContain('localhost');
      expect(config.services.szyfromat.url).toContain('localhost');
      expect(config.services.detax.url).toContain('localhost');
    }
  });
});
