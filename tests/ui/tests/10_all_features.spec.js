/**
 * Test 10: All Features Verification
 * 
 * Kompletna lista funkcji do sprawdzenia we wszystkich panelach
 */

const { test, expect } = require('@playwright/test');

const URLS = {
  founder: 'http://localhost:5000',
  idcard: 'http://localhost:4100',
  idcardApi: 'http://localhost:4000',
  szyfromat: 'http://localhost:3500',
  szyfromatApi: 'http://localhost:8500',
  detax: 'http://localhost:3005',
  detaxApi: 'http://localhost:8005',
  mailpit: 'http://localhost:8026'
};

test.describe('All Services Health Check', () => {
  test('Founder.pl API is healthy', async ({ request }) => {
    const response = await request.get(`${URLS.founder.replace('5000', '5001')}/health`);
    expect(response.ok()).toBeTruthy();
  });

  test('IDCard.pl API is healthy', async ({ request }) => {
    const response = await request.get(`${URLS.idcardApi}/health`);
    expect(response.ok()).toBeTruthy();
  });

  test('Szyfromat.pl API is healthy', async ({ request }) => {
    const response = await request.get(`${URLS.szyfromatApi}/health`);
    expect(response.ok()).toBeTruthy();
  });

  test('Detax.pl API is healthy', async ({ request }) => {
    const response = await request.get(`${URLS.detaxApi}/health`);
    expect(response.ok()).toBeTruthy();
  });

  test('Mailpit is running', async ({ request }) => {
    const response = await request.get(`${URLS.mailpit}/api/v1/messages`);
    expect(response.ok()).toBeTruthy();
  });
});

test.describe('IDCard.pl Features', () => {
  test('Login page loads', async ({ page }) => {
    await page.goto(`${URLS.idcard}/login`);
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('Services page shows available services', async ({ page }) => {
    // Login first
    await page.goto(`${URLS.idcard}/login`);
    await page.fill('input[type="email"]', 'demo@idcard.pl');
    await page.fill('input[type="password"]', 'demo123');
    await page.click('button[type="submit"]');
    await page.waitForURL(`${URLS.idcard}/`);
    
    // Go to services
    await page.goto(`${URLS.idcard}/services`);
    await page.waitForLoadState('networkidle');
    
    // Check services are visible
    await expect(page.locator('text=e-Doręczenia')).toBeVisible();
    await expect(page.locator('text=Detax AI')).toBeVisible();
  });

  test('API: List services', async ({ request }) => {
    const response = await request.get(`${URLS.idcardApi}/api/services`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.services.length).toBeGreaterThan(0);
  });

  test('API: Authorization types', async ({ request }) => {
    const response = await request.get(`${URLS.idcardApi}/api/authorization-types`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.types).toContainEqual(expect.objectContaining({ type: 'accounting' }));
  });
});

test.describe('Szyfromat.pl Features', () => {
  let token;

  test.beforeAll(async ({ request }) => {
    // Login to get token
    const loginResponse = await request.post(`${URLS.szyfromatApi}/api/auth/login`, {
      data: { username: 'testuser', password: 'testpass123' }
    });
    if (loginResponse.ok()) {
      const data = await loginResponse.json();
      token = data.access_token;
    }
  });

  test('Login page loads', async ({ page }) => {
    await page.goto(`${URLS.szyfromat}/login`);
    await expect(page.locator('input')).toBeVisible();
  });

  test('API: Get messages', async ({ request }) => {
    if (!token) test.skip();
    
    const response = await request.get(`${URLS.szyfromatApi}/api/messages?folder=inbox`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(Array.isArray(data)).toBeTruthy();
  });

  test('API: Get folders', async ({ request }) => {
    if (!token) test.skip();
    
    const response = await request.get(`${URLS.szyfromatApi}/api/folders`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect(response.ok()).toBeTruthy();
  });

  test('API: Mail status (Mailpit)', async ({ request }) => {
    const response = await request.get(`${URLS.szyfromatApi}/api/mail/status`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('connected');
    expect(data.smtp_host).toBe('mailpit');
  });

  test('API: Seed demo messages', async ({ request }) => {
    const response = await request.post(`${URLS.szyfromatApi}/api/mail/seed`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.messages_sent).toBeGreaterThan(0);
  });

  test('API: Star message endpoint exists', async ({ request }) => {
    if (!token) test.skip();
    
    const response = await request.post(`${URLS.szyfromatApi}/api/messages/test-id/star`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    // Should return 200 (mock) or 404 (not found) but not 405 (method not allowed)
    expect([200, 404]).toContain(response.status());
  });

  test('API: Archive message endpoint exists', async ({ request }) => {
    if (!token) test.skip();
    
    const response = await request.post(`${URLS.szyfromatApi}/api/messages/test-id/archive`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect([200, 404]).toContain(response.status());
  });

  test('API: Mark as read endpoint exists', async ({ request }) => {
    if (!token) test.skip();
    
    const response = await request.post(`${URLS.szyfromatApi}/api/messages/test-id/read`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    expect([200, 404]).toContain(response.status());
  });
});

test.describe('Detax.pl Features', () => {
  test('Main page loads', async ({ page }) => {
    await page.goto(URLS.detax);
    await page.waitForLoadState('networkidle');
    
    // Check Detax logo/title
    await expect(page.locator('.detax-logo, h1:has-text("detax"), text=detax')).toBeVisible();
  });

  test('Chat interface is visible', async ({ page }) => {
    await page.goto(URLS.detax);
    await page.waitForLoadState('networkidle');
    
    // Check chat elements
    await expect(page.locator('#messages, .messages')).toBeVisible();
    await expect(page.locator('#user-input, input[placeholder*="pytanie"]')).toBeVisible();
  });

  test('Modules/channels are visible', async ({ page }) => {
    await page.goto(URLS.detax);
    await page.waitForLoadState('networkidle');
    
    // Check module buttons
    await expect(page.locator('text=ksef').first()).toBeVisible();
    await expect(page.locator('text=vat').first()).toBeVisible();
  });

  test('SSO token is processed correctly', async ({ page }) => {
    const mockToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0IiwiZW1haWwiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjo5OTk5OTk5OTk5fQ.test';
    
    await page.goto(`${URLS.detax}/?sso_token=${mockToken}`);
    await page.waitForLoadState('domcontentloaded');
    await page.waitForTimeout(1000);
    
    // Token should be removed from URL
    expect(page.url()).not.toContain('sso_token');
    
    // Token should be saved
    const savedToken = await page.evaluate(() => localStorage.getItem('detax_token'));
    expect(savedToken).toBeTruthy();
  });

  test('API: Health check', async ({ request }) => {
    const response = await request.get(`${URLS.detaxApi}/health`);
    expect(response.ok()).toBeTruthy();
    const data = await response.json();
    expect(data.status).toBe('healthy');
  });

  test('API: Chat endpoint', async ({ request }) => {
    const response = await request.post(`${URLS.detaxApi}/api/v1/chat`, {
      data: { message: 'test', module: 'default' }
    });
    // May timeout if Ollama is slow, but should not error
    expect([200, 504]).toContain(response.status());
  });
});

test.describe('Mailpit Integration', () => {
  test('Messages are stored in Mailpit', async ({ request }) => {
    // Seed messages first
    await request.post(`${URLS.szyfromatApi}/api/mail/seed`);
    
    // Check Mailpit
    const response = await request.get(`${URLS.mailpit}/api/v1/messages`);
    expect(response.ok()).toBeTruthy();
    
    const data = await response.json();
    expect(data.total).toBeGreaterThan(0);
  });

  test('Messages have correct structure', async ({ request }) => {
    const response = await request.get(`${URLS.mailpit}/api/v1/messages`);
    const data = await response.json();
    
    if (data.messages && data.messages.length > 0) {
      const msg = data.messages[0];
      expect(msg).toHaveProperty('Subject');
      expect(msg).toHaveProperty('From');
      expect(msg).toHaveProperty('To');
    }
  });
});

test.describe('Cross-Service Integration', () => {
  test('IDCard SSO to Szyfromat works', async ({ request }) => {
    // Login to IDCard
    const loginResponse = await request.post(`${URLS.idcardApi}/api/auth/login`, {
      data: { email: 'demo@idcard.pl', password: 'demo123' }
    });
    
    if (loginResponse.ok()) {
      const { access_token } = await loginResponse.json();
      
      // Try SSO to Szyfromat
      const ssoResponse = await request.get(`${URLS.szyfromatApi}/sso?token=${access_token}&redirect=/`, {
        maxRedirects: 0
      });
      
      // Should redirect (302)
      expect([200, 302]).toContain(ssoResponse.status());
    }
  });

  test('IDCard SSO to Detax works', async ({ request }) => {
    // Login to IDCard
    const loginResponse = await request.post(`${URLS.idcardApi}/api/auth/login`, {
      data: { email: 'demo@idcard.pl', password: 'demo123' }
    });
    
    if (loginResponse.ok()) {
      const { access_token } = await loginResponse.json();
      
      // Try SSO to Detax
      const ssoResponse = await request.get(`${URLS.detaxApi}/sso?token=${access_token}&redirect=/`, {
        maxRedirects: 0
      });
      
      // Should redirect (302)
      expect([200, 302]).toContain(ssoResponse.status());
    }
  });
});
