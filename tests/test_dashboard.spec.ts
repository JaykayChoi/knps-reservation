import { test, expect } from '@playwright/test';

test.describe('KNPS Monitor Dashboard', () => {
  test.beforeEach(async ({ page }) => {
    // Go to the local dashboard (assuming it's running on port 5000)
    await page.goto('http://localhost:5000');
  });

  test('should open edit modal when Edit button is clicked', async ({ page }) => {
    // Wait for settings list to load
    await page.waitForSelector('#settings-list');
    
    // Check if there are any settings. If not, create one first.
    const editButtons = await page.locator('button:has-text("Edit")');
    const count = await editButtons.count();
    
    if (count === 0) {
      console.log('No settings found, creating a test setting first...');
      await page.click('#btn-add-setting');
      await page.fill('#name', 'Playwright Test Monitor');
      await page.click('#btn-save-setting');
      // Wait for the card to appear
      await page.waitForSelector('.brutal-card h3:has-text("Playwright Test Monitor")');
    }

    // Now click the first Edit button
    await page.locator('button:has-text("Edit")').first().click();

    // Verify modal is visible
    const modal = page.locator('#setting-modal');
    await expect(modal).toBeVisible();

    // Verify modal title
    const modalTitle = page.locator('#modal-title');
    await expect(modalTitle).toHaveText('Edit Setting');

    // Verify form is populated (name field should not be empty)
    const nameInput = page.locator('#name');
    await expect(nameInput).not.toHaveValue('');
    
    console.log('Edit modal opened and populated successfully!');
  });

  test('should show Clear Cooldown History button in edit mode only', async ({ page }) => {
    // Open Add modal
    await page.click('#btn-add-setting');
    await expect(page.locator('#btn-clear-history')).toBeHidden();
    await page.click('#btn-close-modal');

    // Open Edit modal
    await page.waitForSelector('button:has-text("Edit")');
    await page.locator('button:has-text("Edit")').first().click();
    await expect(page.locator('#btn-clear-history')).toBeVisible();
    
    console.log('Clear Cooldown History button visibility verified.');
  });
});
