import assert from 'node:assert/strict';
import test from 'node:test';
import { readFileSync } from 'node:fs';
import ts from 'typescript';
import { accountForRoom, rememberRoom, workspaceReturn, isRoomLocation, roomCues, ROOM_OUTRO_START, profileSavedTab } from '../src/lib/room-experience.ts';

const motionSource = readFileSync(new URL('../src/lib/room-motion.ts', import.meta.url), 'utf8');
const motionJs = ts.transpileModule(motionSource, {compilerOptions:{module:ts.ModuleKind.ESNext}}).outputText;
const {RoomMotion} = await import('data:text/javascript;base64,' + Buffer.from(motionJs).toString('base64'));
test('first profile creation completes the chosen games route without hijacking later profile edits', () => {
  const target = workspaceReturn('/chat?scene=room&tab=profile&games=1');
  assert.equal(profileSavedTab(false, new URL(target, 'https://example.invalid').search), 'home');
  assert.equal(profileSavedTab(true, '?scene=room&tab=profile&games=1'), 'chat');
  assert.equal(profileSavedTab(false, '?scene=room&tab=profile'), 'chat');
  assert.equal(profileSavedTab(false, '?games=0'), 'chat');
});
test('current motion can travel forward and back without jumping outside the film', () => {
  const motion = new RoomMotion(ROOM_OUTRO_START);
  let clock = 0, previous = 0;
  motion.scroll(100, clock);
  for (let step = 0; step < 600; step++) {
    clock += 40;
    const position = motion.step(40, clock);
    assert.ok(position >= previous && position <= ROOM_OUTRO_START);
    assert.ok(position - previous < .1, 'no discontinuous frame jump');
    previous = position;
  }
  assert.equal(previous, ROOM_OUTRO_START);
  motion.scroll(-100, clock);
  for (let step = 0; step < 600; step++) {
    clock += 40;
    const position = motion.step(40, clock);
    assert.ok(position >= 0 && position <= previous);
    previous = position;
  }
  assert.equal(previous, 0);
});

test('authentication preserves chat and tracker destinations without external redirects', () => {
  const next = new URLSearchParams(accountForRoom('register').split('?')[1]).get('next');
  assert.equal(workspaceReturn(next), '/chat?scene=room');
  assert.equal(workspaceReturn('/chat?scene=room&tab=trackers&tracker=doctor'), '/chat?scene=room&tab=trackers&tracker=doctor');
  assert.equal(isRoomLocation('?next=' + encodeURIComponent(next)), true);
  for (const value of ['https://example.com', '//example.com', '/chat/../../other', '/chat\\evil', '/chat#//evil', '/account', null]) assert.equal(workspaceReturn(value), '/cabinet');
});
test('ordinary account and workspace bookmarks keep the approved application', () => {
  for (const route of ['/chat', '/cabinet', '/account']) assert.equal(isRoomLocation('', route), true);
  for (const route of ['/', '/first-aid', '/privacy', '/chat/unknown']) assert.equal(isRoomLocation('', route), false);
});
test('finishing the introduction preserves authentication and drafts; blocked storage is harmless', () => {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  const data = new Map([['mh_remote_session_v1', 'unchanged'], ['chat-draft', 'draft']]);
  try {
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: { setItem: (key, value) => data.set(key, value) } });
    rememberRoom();
    assert.equal(data.get('mama_room_introduction_seen_v1'), 'yes');
    assert.equal(data.get('mh_remote_session_v1'), 'unchanged');
    assert.equal(data.get('chat-draft'), 'draft');
    Object.defineProperty(globalThis, 'localStorage', { configurable: true, get() { throw new Error('blocked'); } });
    assert.doesNotThrow(rememberRoom);
  } finally {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous);
    else delete globalThis.localStorage;
  }
});
test('current introduction captions have readable durations and stay inside the film', () => {
  assert.ok(ROOM_OUTRO_START > 0 && ROOM_OUTRO_START < 25);
  let previousEnd = 0;
  for (const cue of roomCues) {
    assert.ok(cue.start >= previousEnd);
    assert.ok(cue.end - cue.start >= 2.5);
    assert.ok(cue.end <= 25);
    previousEnd = cue.end;
  }
});
