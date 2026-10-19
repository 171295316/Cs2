import { test, expect } from '@playwright/test';

test('home → bilingual catalog search → honest empty state', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { level: 1 })).toContainText('CS2');
  await page.getByRole('link', { name: '饰品目录', exact: true }).click();
  await page.getByRole('textbox', { name: '搜索饰品' }).fill('不存在的测试目录记录');
  await page.getByRole('combobox', { name: '分类' }).selectOption('sticker');
  await page.getByRole('button', { name: '搜索', exact: true }).click();
  await expect(page).toHaveURL(/category=sticker/);
  await expect(page.getByRole('status')).toContainText('暂无可核实数据');
  await expect(page.getByRole('status')).not.toContainText('0');
  await page.getByRole('link', { name: '返回首页' }).click();
  await page.getByRole('link', { name: '数据方法', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
});

test('隔离演示记录：目录→价格全历史→缺口→在售数量→变体空态', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', error => errors.push(error.message));
  await page.goto('/items?query=测试专用饰品');
  await page.getByRole('link', { name: '测试专用饰品（演示）', exact: true }).click();
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('测试专用饰品（演示）');
  await expect(page.getByText('存在 2 处记录缺口', { exact: false })).toBeVisible();
  await expect(page.getByRole('img').first()).toBeVisible();
  await expect(page.locator('canvas').first()).toBeVisible();
  await page.getByText('原始记录、来源证据与方法（3 条）', { exact: true }).click();
  await expect(page.getByRole('cell', { name: '123.45 USD', exact: true })).toBeVisible();
  await page.getByRole('combobox', { name: '供给口径' }).selectOption('listed_units');
  await page.getByRole('button', { name: '更新供给', exact: true }).click();
  await expect(page.getByText('平台在售数量，不等于总存世量', { exact: true })).toBeVisible();
  await page.getByText('实际快照与来源证明（1 条）', { exact: true }).click();
  await expect(page.getByRole('cell', { name: '12', exact: true })).toBeVisible();
  await page.getByRole('link', { name: '快照来源证明', exact: true }).getAttribute('href').then(href => expect(href).toContain('example.invalid'));
  await expect(page.getByText('TEST ONLY <script>alert(1)</script>', { exact: true })).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth)).toBe(false);
  expect(errors).toEqual([]);
  await page.getByRole('link', { name: /test-variant/ }).click();
  await expect(page.getByRole('status').first()).toContainText('暂无可核实数据');
});

test('手机布局与近期有效样本排行', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/?source=e2e-fixture');
  await expect(page.getByText('345.67 USD', { exact: false })).toBeVisible();
  const overflowing = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth);
  expect(overflowing).toBe(false);
});
