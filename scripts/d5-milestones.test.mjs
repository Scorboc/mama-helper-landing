import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

// Small hook harness exercises the real event handlers without a browser or backend.
function compile(file, imports, source = fs.readFileSync(new URL(file, import.meta.url), 'utf8')) {
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX, target: ts.ScriptTarget.ES2020 } }).outputText;
  const exports = {};
  vm.runInNewContext(code, { exports, require: name => {
    if (!(name in imports)) throw new Error(`Unexpected import ${name}`);
    return imports[name];
  }, window: { addEventListener() {}, removeEventListener() {}, dispatchEvent() {} }, Event: class {}, Date, Intl, URLSearchParams, console });
  return exports;
}
const book = compile('../src/lib/first-year-book.ts', {});
const marks = compile('../src/lib/milestone-marks.ts', {});
const jsx = { jsx: (type, props, key) => ({ type, props, key }), jsxs: (type, props, key) => ({ type, props, key }), Fragment: 'fragment' };
// Execute the actual ParentWorkspace boundary, including its reconciliation key.
// The lightweight harness cannot mount the entire workspace (auth, journal, tabs).
const workspaceSource = fs.readFileSync(new URL('../src/pages/ParentWorkspace.tsx', import.meta.url), 'utf8');
const workspaceAst = ts.createSourceFile('ParentWorkspace.tsx', workspaceSource, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
let pushBoundary;
function findPushBoundary(node) {
  if (ts.isJsxSelfClosingElement(node) && node.tagName.getText(workspaceAst) === 'PushMilestoneMark') pushBoundary = node.getText(workspaceAst);
  ts.forEachChild(node, findPushBoundary);
}
findPushBoundary(workspaceAst);
assert.ok(pushBoundary, 'ParentWorkspace must render PushMilestoneMark');
const workspaceBoundary = compile('boundary.tsx', { 'react/jsx-runtime': jsx }, `export default function boundary(state, location, PushMilestoneMark) { return (${pushBoundary}); }`).default;
test('ParentWorkspace quick and mark siblings have distinct stable child keys', () => {
  const elements = [];
  function visit(node) {
    if (ts.isJsxSelfClosingElement(node) && ['QuickConveniences', 'PushMilestoneMark'].includes(node.tagName.getText(workspaceAst))) elements.push(node);
    ts.forEachChild(node, visit);
  }
  visit(workspaceAst);
  assert.equal(elements.length, 2);
  assert.equal(elements[0].parent, elements[1].parent, 'check the actual siblings');
  const keys = elements.map(node => {
    const key = node.attributes.properties.find(prop => ts.isJsxAttribute(prop) && prop.name.getText(workspaceAst) === 'key');
    assert.ok(key && ts.isJsxExpression(key.initializer) && key.initializer.expression);
    return compile('key.ts', {}, `export default function key(state, location) { return (${key.initializer.expression.getText(workspaceAst)}); }`).default;
  });
  for (const activeChildId of [undefined, '', 'primary', 'second', 'mark-primary', 'quick-primary']) {
    const state = { activeChildId };
    const before = keys.map(key => key(state, { search: '?mark=roll&child=primary' }));
    assert.notEqual(before[0], before[1]);
    assert.deepEqual(keys.map(key => key(state, { search: '' })), before, 'address cleanup must preserve both keys');
  }
  for (const key of keys) assert.notEqual(key({ activeChildId: 'primary' }, {}), key({ activeChildId: 'second' }, {}), 'child change must reset each component');
});
const Button = 'button', Input = 'input', FirstYearBook = 'FirstYearBook';

function harness({ initialSearch = '?mark=roll&child=primary&tab=trackers', skill = 'crawl', records = [], achievements = [], permission = 'owner', hintError = false, hint = { title: 'Проверенная подсказка', text: 'Безопасность. Игра.', milestoneSkill: skill } } = {}, component = 'mark') {
  let location = { pathname: '/cabinet', search: initialSearch, hash: '#content' };
  const navigations = [];
  const navigate = (to, options) => { navigations.push({ to, options }); location = { ...to, search: to.search ? '?' + to.search : '' }; dirty = true; };
  let cursor = 0, effects = [], dirty = true, tree, componentFn;
  const slots = [], cleanups = [], calls = [];
  let mountedKey;
  const today = book.familyDay(Date.now(), 'Europe/Moscow');
  const birth = today.slice(0, 4) + '-01-01';
  const state = { activeChildId: 'primary', preferences: { timezone: 'Europe/Moscow' }, profile: { stage: 'child', birthDate: birth } };
  const react = {
    useState(initial) {
      const i = cursor++;
      if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial;
      return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; dirty = true; }];
    },
    useRef(initial) { const i = cursor++; slots[i] ??= { current: initial }; return slots[i]; },
    useId() { return `field-${cursor++}`; },
    useEffect(fn, deps) {
      const i = cursor++;
      if (!slots[i] || deps.some((v, n) => v !== slots[i][n])) {
        slots[i] = deps; effects.push(() => { cleanups[i]?.(); cleanups[i] = fn(); });
      }
    },
  };
  const api = async (action, data) => {
    calls.push({ action, data });
    if (action === 'care-list') return { records, achievements, permission, profile: { stage: 'child', birthDate: birth }, summary: { timezone: 'Europe/Moscow' } };
    if (action === 'age-guidance') { if (hintError) throw new Error('synthetic offline'); return { selected: hint }; }
    if (action === 'care-put') return { record: data.record };
    return { ok: true };
  };
  const imports = {
    'react-router-dom': { useLocation: () => location, useNavigate: () => navigate },
    react, 'react/jsx-runtime': jsx, 'react-dom': { createPortal: x => x },
    '@/components/ui/button': { Button }, '@/components/ui/input': { Input },
    './ui/button': { Button }, './ui/input': { Input }, './ui/textarea': { Textarea: 'textarea' },
    './ui/dialog': Object.fromEntries(['Dialog','DialogContent','DialogHeader','DialogTitle','DialogDescription'].map(x => [x,x])),
    '@/lib/parent-api': { api }, '@/lib/id': { randomId: () => 'synthetic-id' },
    '@/lib/care-journal': { journalDay: book.familyDay }, '@/lib/first-year-book': book,
    '@/lib/milestone-marks': marks, '@/lib/family': { familyList: () => [{ id: 'primary' }, { id: 'second' }] },
    './FirstYearBook': { default: FirstYearBook }, '@/lib/book-postcard': { renderPostcard() {} }, './first-year-book.css': {},
  };
  const compiled = compile(component !== 'book' ? '../src/components/MilestoneMark.tsx' : '../src/components/FirstYearBook.tsx', imports);
  componentFn = component === 'push' ? compiled.PushMilestoneMark : compiled.default;
  function render() {
    cursor = 0; dirty = false;
    if (component === 'push') {
      const boundary = workspaceBoundary(state, location, componentFn);
      if (boundary.key !== mountedKey) {
        cleanups.forEach(fn => fn?.()); cleanups.length = 0; slots.length = 0;
        mountedKey = boundary.key;
      }
    }
    tree = componentFn(component === 'push' ? { state, search: location.search } : component === 'mark' ? { state, skill, push: true } : { context: { childId: 'primary' }, zone: 'Europe/Moscow', startAdding: true });
    const pending = effects; effects = []; pending.forEach(fn => fn());
    return tree;
  }
  async function flush() { for (let i = 0; i < 5; i++) { await new Promise(resolve => setImmediate(resolve)); if (dirty) render(); } }
  function nodes(node) {
    if (Array.isArray(node)) return node.flatMap(n => nodes(n));
    if (!node || typeof node !== 'object') return [];
    return [node, ...nodes(node.props?.children)];
  }
  function text(node) {
    if (Array.isArray(node)) return node.map(text).join(' ');
    if (node == null || node === false) return '';
    if (typeof node !== 'object') return String(node);
    return text(node.props?.children);
  }
  function button(label) { return nodes(tree).find(n => n.type === Button && text(n) === label); }
  async function click(label) { const b = button(label); assert.ok(b, label); assert.ok(!b.props.disabled, label); b.props.onClick(); await flush(); }
  render();
  return { navigations, flush, nodes: () => nodes(tree), text: () => text(tree), button, click, calls, today, birth,
    route: async (search, childId = state.activeChildId) => { location = { ...location, search }; state.activeChildId = childId; dirty = true; await flush(); },
    unmount: () => cleanups.forEach(fn => fn?.()) };
}

test('server hint precedes question, old mark/child skill maps through server', async () => {
  const h = harness(); await h.flush();
  assert.ok(h.text().indexOf('Безопасность. Игра.') < h.text().indexOf(marks.milestoneQuestions.crawl));
  assert.equal(h.calls.find(c => c.action === 'age-guidance').data.milestoneSkill, 'crawl');
  assert.equal(h.calls.filter(c => c.action === 'care-list').length, 1);
  assert.equal(h.calls.filter(c => c.action === 'care-put').length, 0);
});
test('not yet leaves hint visible and creates no record', async () => {
  const h = harness(); await h.flush(); await h.click('Пока нет');
  assert.match(h.text(), /Здесь нечего сдавать или догонять.*«Наших открытиях»\./);
  assert.match(h.text(), /Безопасность. Игра./);
  assert.equal(h.calls.filter(c => c.action === 'care-put').length, 0);
  assert.equal(h.button('Да'), undefined);
});
test('yes opens date step; birth inclusive, future and before birth rejected', async () => {
  const h = harness(); await h.flush(); await h.click('Да');
  assert.equal(h.calls.filter(c => c.action === 'care-put').length, 0);
  const input = () => h.nodes().find(n => n.type === Input && n.props.type === 'date');
  assert.equal(input().props.min, h.birth); assert.equal(input().props.max, h.today);
  for (const bad of ['1999-01-01','2099-01-01','2025-02-30']) {
    input().props.onChange({ target: { value: bad } }); await h.flush();
    assert.equal(h.button('Сохранить').props.disabled, true);
    h.button('Сохранить').props.onClick(); await h.flush();
    assert.equal(h.calls.filter(c => c.action === 'care-put').length, 0);
  }
  input().props.onChange({ target: { value: h.birth } }); await h.flush();
  await h.click('Сохранить');
  const saved = h.calls.find(c => c.action === 'care-put').data.record;
  assert.equal(saved.skill, 'crawl'); assert.equal(book.familyDay(saved.at, 'Europe/Moscow'), h.birth);
  assert.match(h.text(), /Сохранено: .+ — в «Наших открытиях» и «Книге первого года»\./);
});
test('already marked from new, legacy or both never asks question', async () => {
  const newRecord = { id: 'existing', kind: 'achievement', skill: 'crawl', at: new Date().toISOString() };
  const old = { id: 'old', kind: 'crawl', date: '2026-01-01' };
  for (const data of [{ records: [newRecord] }, { achievements: [old] }, { records: [newRecord], achievements: [old] }]) {
    const h = harness(data); await h.flush();
    assert.match(h.text(), /Уже отмечено/); assert.equal(h.button('Да'), undefined); assert.equal(h.button('Пока нет'), undefined);
    assert.ok(h.button('Закрыть'));
  }
});
test('guest has no mark action; crawl own movement opens existing free memory path', async () => {
  const guest = harness({ permission: 'write' }); await guest.flush();
  assert.equal(guest.button('Да'), undefined); assert.match(guest.text(), /владелец профиля/);
  const h = harness(); await h.flush();
  await h.click('Передвигается по-своему — записать своими словами');
  assert.ok(h.nodes().some(n => n.type === FirstYearBook && n.props.startAdding));
  assert.equal(h.calls.filter(c => c.action === 'care-put').length, 0);
});
test('existing free memory form saves note without crawl or canonical label', async () => {
  const h = harness({}, 'book'); await h.flush();
  h.nodes().find(n => n.type === 'textarea').props.onChange({ target: { value: 'Передвигается своим способом' } });
  await h.flush();
  await h.nodes().find(n => n.type === 'form').props.onSubmit({ preventDefault() {} }); await h.flush();
  const writes = h.calls.filter(c => c.action === 'care-put'); assert.equal(writes.length, 1);
  assert.equal(writes[0].data.record.note, 'Передвигается своим способом');
  assert.equal(writes[0].data.record.skill, undefined); assert.equal(writes[0].data.record.value, undefined);
});
test('family day conversion preserves chosen day at UTC extremes', () => {
  for (const zone of ['Pacific/Kiritimati','Etc/GMT+12','Europe/Moscow']) {
    for (const day of ['2024-02-29','2026-01-01']) assert.equal(book.familyDay(book.memoryInstant(day, zone), zone), day);
  }
});
test('hint read failure never opens a mark question; expired hint stays separate from manual observation', async () => {
  const failed = harness({ hintError: true }); await failed.flush();
  assert.match(failed.text(), /Не удалось открыть подсказку/);
  assert.equal(failed.button('Да'), undefined);
  const expired = harness({ hint: null }); await expired.flush();
  assert.match(expired.text(), /возрастная подсказка сейчас недоступна/);
  assert.ok(expired.button('Да'));
});

test('opening push consumes mark and child with replace and retains the opened card', async () => {
  const h = harness({}, 'push'); await h.flush();
  assert.equal(h.navigations.length, 1);
  assert.equal(h.navigations[0].options.replace, true);
  assert.equal(h.navigations[0].to.search, 'tab=trackers');
  assert.equal(h.navigations[0].to.pathname, '/cabinet');
  assert.equal(h.navigations[0].to.hash, '#content');
  assert.ok(h.nodes().some(n => n.props?.skill === 'roll' && n.props?.push));
});

test('ParentWorkspace opens a new skill after cleanup and resets on child change', async () => {
  const h = harness({}, 'push'); await h.flush();
  await h.route('?mark=crawl&child=primary');
  assert.ok(h.nodes().some(n => n.props?.skill === 'crawl'));
  assert.equal(h.navigations.at(-1).to.search, '');
  await h.route('', 'second');
  assert.equal(h.nodes().length, 0);
  await h.route('', 'primary');
  assert.equal(h.nodes().length, 0, 'returning to child must not restore old card');
  await h.route('?mark=stand&child=second', 'second');
  assert.ok(h.nodes().some(n => n.props?.skill === 'stand' && n.props.state.activeChildId === 'second'));
  await h.route('');
  assert.ok(h.nodes().some(n => n.props?.skill === 'stand'));
});

test('ParentWorkspace fresh mount at cleaned address does not reopen a card', async () => {
  const fresh = harness({ initialSearch: '' }, 'push');
  await fresh.flush();
  assert.equal(fresh.nodes().length, 0);
});
