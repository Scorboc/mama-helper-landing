// Isolated service-worker event tests: no browser subscription or external calls.
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
import path from 'node:path';

const events = {};
let notification, navigated, focused = false, opened, closed = false;
let clients = [{url: 'http://localhost:5173/cabinet', navigate: async p => {navigated = p;}, focus: async () => {focused = true;}}];
const self = {
  location: {origin: 'http://localhost:5173'},
  addEventListener: (name, fn) => {events[name] = fn;},
  registration: {showNotification: async (title, options) => {notification = {title, ...options};}},
  clients: {matchAll: async () => clients, openWindow: async p => {opened = p;}}
};
vm.runInNewContext(fs.readFileSync(new URL('../public/parent-sw.js', import.meta.url), 'utf8'), {self, URL});
const emit = async (name, properties) => {
  let task;
  events[name]({...properties, waitUntil: promise => {task = promise;}});
  await task;
};
await emit('push', {data: {json: () => ({body: 'a'.repeat(250), path: '/cabinet?tab=chat&child=second&topic=month-care-5'})}});
assert.equal(notification.body.length, 180);
assert.equal(notification.data.path, '/cabinet?tab=chat&child=second&topic=month-care-5');
await emit('notificationclick', {notification: {data: notification.data, close: () => {closed = true;}}});
assert.equal(navigated, notification.data.path);
assert.ok(focused && closed);
await emit('push', {data: {json: () => ({path: 'https://evil.example/steal'})}});
assert.equal(notification.data.path, '/cabinet');
await emit('push', {data: {json: () => {throw new Error('malformed');}}});
assert.equal(notification.data.path, '/cabinet');
assert.ok(notification.body.length > 0);
clients = [{url: 'https://evil.example/other'}];
await emit('notificationclick', {notification: {data: {path: '//evil.example/steal'}, close: () => {}}});
assert.equal(opened, '/cabinet');
const report = {checks: 8, passed: 8, actualDeviceDelivery: false};
const out = path.resolve('outputs/qa-age-push-20261012');
fs.mkdirSync(out, {recursive: true});
fs.writeFileSync(path.join(out, 'service-worker.json'), JSON.stringify(report, null, 2));
console.log(JSON.stringify(report));
