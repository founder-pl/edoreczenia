// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Test 02: Rejestracja i logowanie w IDCard.pl
 * Odpowiednik: examples/03_register_idcard.sh
 */

test.describe('IDCard.pl Registration & Login', () => {
  
  test('Can register new user', async ({ page }) => {
    await page.goto('http://localhost:4100/login');
    
    // Kliknij "Zarejestruj się"
    await page.click('text=Nie masz konta? Zarejestruj się');
    
    // Wypełnij formularz
    const timestamp = Date.now();
    const email = `test.ui.${timestamp}@example.com`;
    
    await page.fill('input[type="text"]', 'Test UI User');
    await page.fill('input[type="email"]', email);
    await page.fill('input[type="password"]', 'Test123!');
    
    // Wyślij formularz
    await page.click('button[type="submit"]');
    
    // Powinno przekierować na dashboard
    await expect(page).toHaveURL('http://localhost:4100/', { timeout: 10000 });
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('Can login with demo account', async ({ page }) => {
    await page.goto('http://localhost:4100/login');
    
    // Wypełnij formularz logowania
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    
    // Wyślij formularz
    await page.click('button[type="submit"]');
    
    // Powinno przekierować na dashboard
    await expect(page).toHaveURL('http://localhost:4100/', { timeout: 10000 });
    await expect(page.locator('text=Dashboard')).toBeVisible();
  });

  test('Shows error for invalid credentials', async ({ page }) => {
    await page.goto('http://localhost:4100/login');
    
    await page.fill('input[type="email"]', 'invalid@example.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    
    await page.click('button[type="submit"]');
    
    // Powinien pokazać błąd
    await expect(page.locator('text=Błąd')).toBeVisible({ timeout: 5000 });
  });

  test('Can logout', async ({ page }) => {
    // Najpierw zaloguj
    await page.goto('http://localhost:4100/login');
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    
    await expect(page).toHaveURL('http://localhost:4100/', { timeout: 10000 });
    
    // Wyloguj
    await page.click('text=Wyloguj');
    
    // Powinno przekierować na login
    await expect(page).toHaveURL(/.*login/);
  });
});
