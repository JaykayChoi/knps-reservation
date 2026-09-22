import { test, expect } from '@playwright/test';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

test('quick search validates a range and renders provider text safely', async ({ page }) => {
  let query = '';
  await page.route('**/*', route => {
    const url = new URL(route.request().url());
    if (url.pathname === '/api/search') {
      query = url.search;
      return route.fulfill({ json: [{ park_name: '<img src=x>', campsite_name: '야영장',
        facility_type: '카라반', date: '2099-10-01', available_count: 2, waiting_count: 0 }] });
    }
    if (url.hostname === 'search.test') {
      const relative = url.pathname === '/' ? 'search.html' : url.pathname.slice(1);
      return route.fulfill({ contentType: relative.endsWith('.js') ? 'application/javascript' : relative.endsWith('.css') ? 'text/css' : 'text/html',
        body: readFileSync(resolve('frontend', relative), 'utf8') });
    }
    if (url.hostname === 'cdn.tailwindcss.com') return route.fulfill({ contentType: 'application/javascript', body: 'window.tailwind = {};' });
    return route.fulfill({ body: '' });
  });
  await page.goto('http://search.test');
  await page.locator('input[name="date_mode"][value="absolute"]').check();
  await page.locator('#start_date').fill('2099-10-01');
  await page.locator('#end_date').fill('2099-10-02');
  await page.locator('#btn-search').click();
  await expect(page.locator('#results-container')).toContainText('<img src=x>');
  await expect(page.locator('#results-container img')).toHaveCount(0);
  expect(query).toContain('dates=2099-10-01%2C2099-10-02');
});
