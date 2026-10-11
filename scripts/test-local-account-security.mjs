// Exercise the actual browser-only account implementation with synthetic storage.
// No real browser storage, user data, network, or AI provider is used.
import assert from "node:assert/strict";
import { createHash, randomUUID, webcrypto } from "node:crypto";
import { readFileSync } from "node:fs";
import vm from "node:vm";
import ts from "typescript";

const source = readFileSync(new URL("../src/lib/parent-api.ts", import.meta.url), "utf8")
  .replaceAll("import.meta.env", "({})") + "\nexports.localApi = localApi;";
const compiled = ts.transpileModule(source, {
  compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS },
}).outputText;
const accountsKey = "mh_local_accounts_v1";
const sessionKey = "mh_local_session_v1";
const digest = (value, salt) => createHash("sha256").update(`${salt}:${value}`).digest("hex");
const initial = () => ({
  id: "demo-account", email: "1", salt: "synthetic-salt",
  passwordHash: digest("old-test-password", "synthetic-salt"),
  recoveryHash: digest("SYNTHETIC-CODE", "synthetic-salt"),
  state: { profile: { childName: "Synthetic" }, messages: [{ text: "before" }] }, revision: 0,
});
function harness(shared, locks) {
  const storage = shared || new Map([[accountsKey, JSON.stringify([initial()])], [sessionKey, "demo-account"]]);
  let pause;
  const context = {
    exports: {}, URL, TextEncoder, Uint8Array,
    localStorage: {
      getItem: key => storage.get(key) ?? null,
      setItem: (key, value) => storage.set(key, String(value)),
      removeItem: key => storage.delete(key),
    },
    crypto: {
      randomUUID, getRandomValues: values => webcrypto.getRandomValues(values),
      subtle: { digest: async (algorithm, data) => {
        const current = pause;
        if (current) { pause = undefined; current.enter(); await current.ready; }
        return webcrypto.subtle.digest(algorithm, data);
      } },
    },
    navigator: locks ? { locks } : {},
    require: name => {
      assert.equal(name, "./parent-model");
      return { emptyState: () => ({ profile: null, messages: [], medicalCard: [] }), demoAnswer: () => "Synthetic" };
    },
  };
  vm.runInNewContext(compiled, context);
  return {
    storage, api: context.exports.localApi,
    account: () => JSON.parse(storage.get(accountsKey)).find(a => a.id === "demo-account"),
    pauseNextHash: () => {
      let release, enter;
      const entered = new Promise(resolve => { enter = resolve; });
      const ready = new Promise(resolve => { release = resolve; });
      pause = { enter, ready };
      return { entered, release };
    },
  };
}
const changedState = { profile: { childName: "Synthetic saved profile" }, messages: [{ text: "new history" }], medicalCard: [] };
const tests = [];
function test(name, run) { tests.push({ name, run }); }
for (const action of ["change-password", "rotate-recovery"]) {
  test(`${action} preserves a save while password hashing is paused`, async () => {
    const h = harness(); const gate = h.pauseNextHash();
    const operation = h.api(action, { currentPassword: "old-test-password", password: "new-test-password" });
    await gate.entered;
    await h.api("save", { revision: 0, state: changedState });
    gate.release(); await operation;
    assert.equal(h.account().revision, 1);
    assert.deepEqual(h.account().state, changedState);
  });
}
test("old password cannot authenticate after a concurrent password change", async () => {
  const h = harness(); const gate = h.pauseNextHash();
  const login = h.api("login", { email: "1", password: "old-test-password" });
  const rejected = assert.rejects(login, e => e.status === 409);
  await gate.entered;
  await h.api("change-password", { currentPassword: "old-test-password", password: "new-test-password" });
  gate.release(); await rejected;
});
test("recovery code is consumed once under concurrent recovery", async () => {
  const h = harness(); const gate = h.pauseNextHash();
  const recover = h.api("recover", { email: "1", recoveryCode: "SYNTHETIC-CODE", password: "first-test-password" });
  const rejected = assert.rejects(recover, e => e.status === 409);
  await gate.entered;
  await h.api("recover", { email: "1", recoveryCode: "SYNTHETIC-CODE", password: "second-test-password" });
  gate.release(); await rejected;
  assert.equal(h.account().passwordHash, digest("second-test-password", "synthetic-salt"));
});
test("logout during reauthentication cannot be undone by credential changes", async () => {
  const h = harness(); const gate = h.pauseNextHash();
  const change = h.api("change-password", { currentPassword: "old-test-password", password: "new-test-password" });
  const rejected = assert.rejects(change, e => e.status === 409);
  await gate.entered; await h.api("logout", {}); gate.release(); await rejected;
  assert.equal(h.storage.has(sessionKey), false);
  assert.equal(h.account().passwordHash, initial().passwordHash);
});
test("concurrent registrations preserve other accounts and reject duplicate email", async () => {
  const h = harness(); const gate = h.pauseNextHash();
  const first = h.api("register", { email: "synthetic@example.test", password: "register-test-password", consent: true });
  const rejected = assert.rejects(first, e => e.status === 409);
  await gate.entered;
  await h.api("register", { email: "synthetic@example.test", password: "register-test-password", consent: true });
  gate.release(); await rejected;
  assert.equal(JSON.parse(h.storage.get(accountsKey)).length, 2);
  assert.deepEqual(h.account(), initial());
});
test("deleting one account cannot remove a concurrently created account", async () => {
  const h = harness(); const gate = h.pauseNextHash();
  const deleting = h.api("delete", { password: "old-test-password" });
  await gate.entered;
  await h.api("register", { email: "other@example.test", password: "register-test-password", consent: true });
  h.storage.set(sessionKey, "demo-account"); gate.release(); await deleting;
  const accounts = JSON.parse(h.storage.get(accountsKey));
  assert.equal(accounts.length, 1); assert.equal(accounts[0].email, "other@example.test");
});
test("shared browser lock serializes operations across two tab contexts", async () => {
  let tail = Promise.resolve();
  const locks = { request: (_name, callback) => {
    const work = tail.then(callback); tail = work.catch(() => {}); return work;
  } };
  const first = harness(undefined, locks); const second = harness(first.storage, locks);
  const gate = first.pauseNextHash();
  const change = first.api("change-password", { currentPassword: "old-test-password", password: "new-test-password" });
  await gate.entered;
  let saved = false;
  const save = second.api("save", { revision: 0, state: changedState }).then(() => { saved = true; });
  await Promise.resolve(); assert.equal(saved, false);
  gate.release(); await Promise.all([change, save]);
  assert.deepEqual(first.account().state, changedState); assert.equal(first.account().revision, 1);
});
for (const { name, run } of tests) { await run(); console.log(`PASS: ${name}`); }
console.log(`${tests.length} browser-only account security checks passed.`);
