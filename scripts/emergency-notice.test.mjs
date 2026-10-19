import assert from 'node:assert/strict';
import test from 'node:test';
import { localEmergencyNotice } from '../src/lib/emergency-notice.ts';

test('immediate critical phrases get a fixed local handoff without age or quota', () => {
  for (const text of ['Ребёнок не дышит', 'Я не могу дышать', 'Малыш без сознания', 'Проглотила батарейку', 'Не хочу жить', 'Сейчас наврежу себе']) {
    assert.match(localEmergencyNotice(text), /112/);
    assert.match(localEmergencyNotice(text), /Не ждите ответа чата/);
  }
});
test('ordinary requests and negated concerns do not become emergency answers', () => {
  for (const text of ['Предложи игру', 'Как я сегодня', 'Я не хочу навредить ребёнку', 'Я устала', 'Как организовать сон?']) assert.equal(localEmergencyNotice(text), '');
});
