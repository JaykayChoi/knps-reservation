import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  testMatch: ['categories.spec.ts', 'search.spec.ts'],
  use: { headless: true },
});
