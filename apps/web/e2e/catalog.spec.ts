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
