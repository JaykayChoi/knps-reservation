import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// All requests are intercepted. No Flask process, database or Telegram used.
test.beforeEach(async ({ page }) => {
  await page.route('**/*', async route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/parking-lots') return route.fulfill({ json: [{ seq: 12, name: 'Test parking' }] });
    if (url.pathname === '/api/ktx/stations') return route.fulfill({ json: [
      { code: '0001', name: '서울', area: '0', major: 1 },
      { code: '0020', name: '부산', area: '9', major: 22 },
      { code: '0501', name: '광명', area: '1', major: 3 },
    ] });
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
  await expect(page.locator('input[name="ktx_seat_classes"]')).toHaveCount(3);
  await expect(page.locator('#parkinglots-container')).toBeHidden();
  await page.locator('#name').fill('KTX monitor');
  await page.getByRole('button', { name: '출발역 선택' }).click();
  await expect(page.getByRole('dialog', { name: '기차역 조회' })).toBeVisible();
  await page.locator('#station-grid').getByRole('button', { name: '서울', exact: true }).click();
  await page.getByRole('button', { name: '도착역 선택' }).click();
  await page.getByPlaceholder('역 이름 또는 초성 검색(서울 : ㅅㅇ)').fill('부');
  await page.locator('#station-grid').getByRole('button', { name: '부산', exact: true }).click();
  await page.locator('input[name="ktx_seat_classes"][value="special"]').uncheck();
  await page.locator('input[name="ktx_seat_classes"][value="standing"]').check();
  await page.locator('#ktx_date').fill('2099-10-01');
  const saved = page.waitForRequest(r => r.url().endsWith('/api/settings') && r.method() === 'PUT');
  await page.locator('#btn-save-setting').click();
  const body = (await saved).postDataJSON();
  expect(body.category).toBe('ktx');
  expect(body.selected_parkinglots).toEqual([]);
  expect(body.selected_parks).toEqual([]);
  expect(body.ktx_options.departure).toBe('서울');
  expect(body.ktx_options.departure_code).toBe('0001');
  expect(body.ktx_options.arrival_code).toBe('0020');
  expect(body.ktx_options.seat_classes).toEqual(['general', 'standing']);
  expect(body.ktx_options.seat_class).toBeUndefined();
});

test('KTX refresh status UI and endpoint polling are absent', async ({ page }) => {
  await page.route('**/api/check?test=true', route => route.fulfill({ json: { ktx: {status: 'queued'} } }));
  const statusRequests: string[] = [];
  page.on('request', request => { if (request.url().includes('/api/ktx/status')) statusRequests.push(request.url()); });
  await expect(page.locator('#ktx-status-panel')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Refresh KTX Status' })).toHaveCount(0);
  await page.locator('#btn-test').click();
  await expect(page.locator('#toast-container')).toContainText('KTX check queued');
  expect(statusRequests).toEqual([]);
});

test('legacy KTX seat class opens as equivalent checkboxes', async ({ page }) => {
  await page.route('**/api/settings/all', route => route.fulfill({ json: [{
    id: 6, name: 'Legacy KTX', category: 'ktx', is_active: true, cooldown_days: 1,
    ktx_options: { departure: '서울', arrival: '부산', date: '2099-10-01',
      start_time: '08:00', end_time: '18:00', seat_class: 'either' },
  }] }));
  await page.reload();
  await page.getByRole('button', { name: 'Edit', exact: true }).click();
  await expect(page.locator('input[name="ktx_seat_classes"][value="general"]')).toBeChecked();
  await expect(page.locator('input[name="ktx_seat_classes"][value="special"]')).toBeChecked();
  await expect(page.locator('input[name="ktx_seat_classes"][value="standing"]')).not.toBeChecked();
});
