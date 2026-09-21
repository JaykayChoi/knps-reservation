import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// All requests are intercepted. No Flask process, database or Telegram used.
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/parking-lots') return route.fulfill({ json: [{ seq: 12, name: 'Test parking' }] });
    if (url.pathname === '/api/settings/all') return route.fulfill({ json: [{
      id: 1, name: 'Parking monitor', category: 'moduparking', is_active: false,
      include_waiting: false, selected_parkinglots: ['12'], cooldown_days: 0,
    }] });
    if (url.pathname.startsWith('/api/')) return route.fulfill({ json: { success: true } });
    if (url.hostname === 'monitor.test') return route.fulfill({ contentType: 'text/html',
      body: readFileSync(resolve('frontend/index.html'), 'utf8') });
    if (url.hostname === 'cdn.tailwindcss.com') return route.fulfill({ contentType: 'application/javascript', body: 'window.tailwind = {};' });
    return route.fulfill({ body: '' });
  });
  await page.goto('http://monitor.test');
  await page.addStyleTag({ content: '.hidden {display:none!important}' });
});

test('edit parking preserves active state and only shows its fields', async ({ page }) => {
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(page.locator('#category')).toHaveValue('moduparking');
  await expect(page.locator('#is_active')).not.toBeChecked();
  await expect(page.locator('#parkinglots-container')).toBeVisible();
  await expect(page.locator('#parks-container')).toBeHidden();
  await expect(page.locator('#ktx-section')).toBeHidden();
});

test('category click and drag select a single category and save KTX', async ({ page }) => {
  await page.locator('#btn-add-setting').click();
  await page.locator('[data-category="moduparking"]').dragTo(page.locator('#category-dropzone'));
  await expect(page.locator('#category')).toHaveValue('moduparking');
  await page.locator('[data-category="ktx"]').click();
  await expect(page.locator('#ktx-section')).toBeVisible();
  await expect(page.locator('#ktx_seat_class option[value="general"]')).toHaveText('일반실');
  await expect(page.locator('#parkinglots-container')).toBeHidden();
  await page.locator('#name').fill('KTX monitor');
  await page.locator('#ktx_departure').fill('서울');
  await page.locator('#ktx_arrival').fill('부산');
  await page.locator('#ktx_date').fill('2099-10-01');
  const saved = page.waitForRequest(r => r.url().endsWith('/api/settings') && r.method() === 'PUT');
  await page.locator('#btn-save-setting').click();
  const body = (await saved).postDataJSON();
  expect(body.category).toBe('ktx');
  expect(body.selected_parkinglots).toEqual([]);
  expect(body.selected_parks).toEqual([]);
  expect(body.ktx_options.departure).toBe('서울');
  expect(body.ktx_options.seat_class).toBe('either');
});

test('test action reports a failed KTX background check', async ({ page }) => {
  await page.route('**/api/check?test=true', route => route.fulfill({ json: { ktx: {status: 'queued'} } }));
  await page.route('**/api/ktx/status', route => route.fulfill({ json: {
    status: 'failed', errors: [{setting_id: 1, error: 'KTX login failed'}],
  } }));
  await page.locator('#btn-test').click();
  await expect(page.locator('#ktx-status-text')).toContainText('KTX login failed');
});
