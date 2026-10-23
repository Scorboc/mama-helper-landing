import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import ts from 'typescript';
const js = ts.transpileModule(fs.readFileSync(new URL('../src/lib/campaign-entry.ts', import.meta.url), 'utf8'), {
  compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ES2022 },
}).outputText;
const { campaignAccountPath } = await import('data:text/javascript;base64,' + Buffer.from(js).toString('base64'));

test('keeps only valid single campaign labels on the account transition', () => {
  const result = new URL(campaignAccountPath('?utm_source=reel&utm_medium=organic&utm_campaign=games_14&utm_content=soft'), 'https://example.invalid');
  assert.equal(result.pathname, '/account');
  assert.deepEqual(Object.fromEntries(result.searchParams), {
    mode: 'login', utm_source: 'reel', utm_medium: 'organic', utm_campaign: 'games_14', utm_content: 'soft',
  });
});
test('drops personal text, invite tokens, redirect and ambiguous or invalid tags', () => {
  assert.equal(campaignAccountPath('?invite=synthetic-secret&email=synthetic@example.test&next=https://example.invalid&mode=register&utm_source=a&utm_source=b&utm_medium=Name%20Surname&utm_content=' + 'x'.repeat(65)), '/account?mode=login');
  assert.equal(campaignAccountPath('?utm_source=%3Cscript%3E&utm_campaign=UPPERCASE&utm_term=private-note'), '/account?mode=login');
});
