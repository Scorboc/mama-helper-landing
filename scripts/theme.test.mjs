import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const html = readFileSync(new URL('../index.html', import.meta.url), 'utf8');
test('first paint and browser chrome use the same approved palette', () => {
  const background = html.match(/html\s*\{[^}]*background:\s*(#[0-9a-f]+)/i)?.[1];
  const chrome = html.match(/<meta name="theme-color" content="(#[0-9a-f]+)"/i)?.[1];
  assert.ok(background);
  assert.equal(background, chrome);
  assert.match(html, /color-scheme:\s*dark/);
});
test('the retired clock-based initializer is not loaded', () => {
  assert.doesNotMatch(html, /<script[^>]*theme-init\.js/i);
  assert.match(html, /<script type="module" src="\/src\/main\.tsx"/);
});
