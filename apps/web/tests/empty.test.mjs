import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
test('home discloses unavailable authorized market data', () => {
  assert.match(readFileSync(new URL('../app/page.tsx', import.meta.url), 'utf8'), /不显示虚构报价或数量/);
});
