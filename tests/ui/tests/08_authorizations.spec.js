/**
 * Test 08: Authorizations (Upoważnienia)
 * 
 * Scenariusz: Firma udziela upoważnienia księgowemu
 * Nowa funkcjonalność IDCard.pl
 */

const { test, expect } = require('@playwright/test');

const URLS = {
  idcard: 'http://localhost:4100',
  idcardApi: 'http://localhost:4000'
};

test.describe('IDCard.pl Authorizations', () => {
  
  test('should list authorization types', async ({ request }) => {
    const response = await request.get(`${URLS.idcardApi}/api/authorization-types`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.types).toBeDefined();
    expect(data.types.length).toBeGreaterThan(0);
    
    // Sprawdź typy
    const typeNames = data.types.map(t => t.type);
    expect(typeNames).toContain('full');
    expect(typeNames).toContain('accounting');
    expect(typeNames).toContain('legal');
    expect(typeNames).toContain('tax');
  });

  test('should list identities for user', async ({ request }) => {
    // Najpierw zaloguj się
    const loginResponse = await request.post(`${URLS.idcardApi}/api/auth/login`, {
      data: { email: 'demo@idcard.pl', password: 'demo123' }
    });
    
    if (!loginResponse.ok()) {
      // Zarejestruj użytkownika
      await request.post(`${URLS.idcardApi}/api/auth/register`, {
        data: {
          email: 'demo@idcard.pl',
          password: 'demo123',
          name: 'Demo User',
          company_name: 'Demo Company'
        }
      });
    }
    
    const loginData = await (await request.post(`${URLS.idcardApi}/api/auth/login`, {
      data: { email: 'demo@idcard.pl', password: 'demo123' }
    })).json();
    
    const token = loginData.access_token;
    
    // Pobierz tożsamości
    const response = await request.get(`${URLS.idcardApi}/api/identities`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.identities).toBeDefined();
  });

  test('should create and list authorizations', async ({ request }) => {
    // Zaloguj jako firma
    const loginData = await (await request.post(`${URLS.idcardApi}/api/auth/login`, {
      data: { email: 'demo@idcard.pl', password: 'demo123' }
    })).json();
    
    const token = loginData.access_token;
    
    // Pobierz tożsamości
    const identitiesResponse = await request.get(`${URLS.idcardApi}/api/identities`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    const identities = await identitiesResponse.json();
    
    if (identities.identities && identities.identities.length > 0) {
      const identityId = identities.identities[0].id;
      
      // Utwórz upoważnienie
      const authResponse = await request.post(`${URLS.idcardApi}/api/authorizations`, {
        headers: { 'Authorization': `Bearer ${token}` },
        data: {
          identity_id: identityId,
          grantee_email: 'ksiegowy@example.com',
          type: 'accounting',
          title: 'Pełnomocnictwo do spraw księgowych'
        }
      });
      
      expect(authResponse.ok()).toBeTruthy();
      const authData = await authResponse.json();
      expect(authData.authorization).toBeDefined();
      expect(authData.authorization.type).toBe('accounting');
    }
    
    // Lista upoważnień
    const listResponse = await request.get(`${URLS.idcardApi}/api/authorizations`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    
    expect(listResponse.ok()).toBeTruthy();
    const listData = await listResponse.json();
    expect(listData.granted).toBeDefined();
    expect(listData.received).toBeDefined();
  });

  test('IDCard services page should show Detax', async ({ page }) => {
    // Zaloguj się
    await page.goto(`${URLS.idcard}/login`);
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    
    await page.waitForURL(`${URLS.idcard}/`);
    
    // Przejdź do usług
    await page.goto(`${URLS.idcard}/services`);
    await page.waitForLoadState('networkidle');
    
    // Sprawdź czy Detax jest widoczny
    await expect(page.locator('text=Detax AI')).toBeVisible();
    await expect(page.locator('text=e-Doręczenia')).toBeVisible();
  });
});
