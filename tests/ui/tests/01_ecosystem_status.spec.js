// @ts-check
const { test, expect } = require('@playwright/test');

/**
 * Test 01: Sprawdzenie statusu ekosystemu
 * Odpowiednik: examples/02_check_status.sh
 */

test.describe('Ecosystem Status', () => {
  
  test('Founder.pl website is accessible', async ({ page }) => {
    const response = await page.goto('http://localhost:5000');
    expect(response.status()).toBe(200);
    await expect(page.locator('text=Founder.pl')).toBeVisible();
  });

  test('IDCard.pl login page is accessible', async ({ page }) => {
    await page.goto('http://localhost:4100');
    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator('text=IDCard.pl')).toBeVisible();
  });

  test('Szyfromat.pl login page is accessible', async ({ page }) => {
    await page.goto('http://localhost:3500');
    // Should redirect to login
    await expect(page).toHaveURL(/.*login/);
    await expect(page.locator('text=Szyfromat')).toBeVisible();
  });

  test('Detax.pl is accessible', async ({ page }) => {
    const response = await page.goto('http://localhost:3005');
    expect(response.status()).toBe(200);
  });

  test('All health endpoints respond', async ({ request }) => {
    const endpoints = [
      { name: 'Founder API', url: 'http://localhost:5001/health' },
      { name: 'IDCard API', url: 'http://localhost:4000/health' },
      { name: 'Szyfromat API', url: 'http://localhost:8500/health' },
      { name: 'Detax API', url: 'http://localhost:8005/health' },
    ];

    for (const endpoint of endpoints) {
      const response = await request.get(endpoint.url);
      expect(response.ok(), `${endpoint.name} should be healthy`).toBeTruthy();
    }
  });
});
