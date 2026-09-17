import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';

const source = readFileSync(new URL('../public/theme-init.js', import.meta.url), 'utf8');
function setup(hour, stored = null, blocked = false) {
  const listeners = {}, root = { style: {}, classList: { toggle(_name, value) { root.dark = value; } } };
  let tick;
  const storage = { value: stored, getItem() { if (blocked) throw Error(); return this.value; }, setItem(_key, value) { if (blocked) throw Error(); this.value = value; } };
  const window = { addEventListener(name, fn) { listeners[name] = fn; }, dispatchEvent() {} };
  const document = { documentElement: root, addEventListener(name, fn) { listeners[name] = fn; } };
  runInNewContext(source, { window, document, localStorage: storage, Date: class { getHours() { return hour; } }, CustomEvent: class {}, setInterval(fn) { tick = fn; } });
  return { window, root, storage, listeners, advance(value) { hour = value; tick(); } };
}
test('auto boundaries use local hours', () => {
  for (const [hour, dark] of [[0,true],[6,true],[7,false],[19,false],[20,true],[23,true]]) assert.equal(setup(hour).root.dark, dark);
});
test('auto updates without reload, including focus after sleep', () => {
  const s = setup(19); s.advance(20); assert.equal(s.root.dark, true); s.advance(7); s.listeners.focus(); assert.equal(s.root.dark, false);
});
test('manual choice persists and overrides clock until auto is chosen', () => {
  const s = setup(21); s.window.mamaTheme.set('light'); s.advance(23); assert.equal(s.root.dark, false); assert.equal(setup(23, s.storage.value).root.dark, false); s.window.mamaTheme.set('auto'); assert.equal(s.root.dark, true);
});
test('unavailable storage does not break switching', () => {
  const s = setup(10, null, true); s.window.mamaTheme.set('dark'); assert.equal(s.root.dark, true);
});
test('invalid preference falls back to auto and tabs synchronize', () => {
  const s = setup(21, 'invalid'); assert.equal(s.root.dark, true); s.listeners.storage({key:'mama-theme',newValue:'light'}); assert.equal(s.root.dark, false); s.listeners.storage({key:null,newValue:null}); assert.equal(s.root.dark, true);
});
