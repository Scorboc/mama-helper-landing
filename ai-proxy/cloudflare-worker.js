const ORIGIN = "https://mama-helper-landing--preview.poehali.dev",
  COOKIE = "mh_session",
  enc = new TextEncoder();
export default {
  async fetch(req, env) {
    const origin = req.headers.get("Origin") || "";
    if (req.method === "OPTIONS") {
      const headers = new Headers();
      cors(headers, origin);
      return new Response(null, { status: 204, headers });
    }
    if (req.method !== "POST")
      return out({ error: "POST required" }, 405, origin);
    let body;
    try {
      body = await req.json();
    } catch {
      return out({ error: "Неверный запрос." }, 400, origin);
    }
    if (!body.action) return proxy(req, body, env);
    if (origin !== ORIGIN)
      return out({ error: "Этот адрес сайта не разрешён." }, 403, origin);
    const id = env.ACCOUNT_STORE.idFromName("global-v1");
    const res = await env.ACCOUNT_STORE.get(id).fetch(
      new Request("https://internal/action", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Cookie: req.headers.get("Cookie") || "",
        },
        body: JSON.stringify(body),
      }),
    );
    const h = new Headers(res.headers);
    cors(h, origin);
    return new Response(res.body, { status: res.status, headers: h });
  },
};
export class AccountStore {
  constructor(state, env) {
    this.s = state.storage;
    this.env = env;
  }
  async fetch(req) {
    try {
      return await this.handle(
        await req.json(),
        req.headers.get("Cookie") || "",
      );
    } catch (e) {
      if (e instanceof AppError) return json({ error: e.message }, e.status);
      console.error(e);
      return json({ error: "Сервис временно недоступен." }, 500);
    }
  }
  async handle(d, cookies) {
    const a = d.action;
    if (a === "health")
      return json({ ok: true, database: true, platform: "cloudflare" });
    if (a === "config")
      return json({
        ok: true,
        chatConfigured: !!this.env.CHEAPAI_API_KEY,
        pushKey: "",
        storage: "cloudflare",
      });
    if (a === "register") {
      const email = mail(d.email),
        password = pass(d.password);
      if (d.consent !== true)
        throw new AppError(400, "Нужно принять условия тестирования.");
      if (await this.s.get("e:" + email))
        throw new AppError(409, "Аккаунт с такой почтой уже существует.");
      const id = crypto.randomUUID(),
        recovery = code(),
        u = {
          id,
          email,
          password: await pwd(password, this.env.PROXY_TOKEN),
          recovery: await sha(recovery),
          state: blank(),
          revision: 0,
        };
      await this.s.put({ ["e:" + email]: id, ["u:" + id]: u });
      return this.loginResponse(u, recovery);
    }
    if (a === "login") {
      const test =
          String(d.email || "").trim() === "1" &&
          String(d.password || "") === "1",
        email = test ? "test@mama-helper.local" : mail(d.email);
      let id = await this.s.get("e:" + email),
        u = id ? await this.s.get("u:" + id) : null;
      if (test && !u) {
        id = "test-account";
        let password;
        try {
          password = await pwd("1", this.env.PROXY_TOKEN);
        } catch {
          throw new AppError(500, "Ошибка запуска аккаунта: AUTH-01");
        }
        u = {
          id,
          email,
          password,
          recovery: "",
          state: blank(),
          revision: 0,
        };
        try {
          await this.s.put({ ["e:" + email]: id, ["u:" + id]: u });
        } catch {
          throw new AppError(500, "Ошибка запуска аккаунта: STORAGE-01");
        }
      }
      if (
        !u ||
        !(await match(
          String(d.password || ""),
          u.password,
          this.env.PROXY_TOKEN,
        ))
      )
        throw new AppError(401, "Неверная почта или пароль.");
      return this.loginResponse(u);
    }
    if (a === "recover") {
      const email = mail(d.email),
        password = pass(d.password),
        id = await this.s.get("e:" + email),
        u = id ? await this.s.get("u:" + id) : null;
      if (
        !u ||
        !u.recovery ||
        (await sha(String(d.recoveryCode || "").trim())) !== u.recovery
      )
        throw new AppError(400, "Проверьте почту и код восстановления.");
      const recovery = code();
      u.password = await pwd(password, this.env.PROXY_TOKEN);
      u.recovery = await sha(recovery);
      await this.removeSessions(id);
      await this.s.put("u:" + id, u);
      return this.loginResponse(u, recovery);
    }
    const i = await this.identity(cookies);
    if (a === "session") return json(pub(i.u));
    if (a === "logout") {
      await this.s.delete("s:" + i.token);
      return json({ ok: true }, 200, clearCookie());
    }
    if (a === "save") {
      if (!Number.isInteger(d.revision) || d.revision !== i.u.revision)
        throw new AppError(
          409,
          "Данные изменились в другой вкладке. Перезагрузите страницу.",
        );
      i.u.state = valid(d.state);
      i.u.revision++;
      await this.s.put("u:" + i.u.id, i.u);
      return json({ revision: i.u.revision });
    }
    if (a === "chat") return this.chat(i.u, d);
    if (a === "delete") {
      if (
        !(await match(
          String(d.password || ""),
          i.u.password,
          this.env.PROXY_TOKEN,
        ))
      )
        throw new AppError(401, "Неверный пароль.");
      await this.removeSessions(i.u.id);
      await this.s.delete(["u:" + i.u.id, "e:" + i.u.email]);
      return json({ ok: true }, 200, clearCookie());
    }
    if (a === "subscribe" || a === "unsubscribe") return json({ ok: true });
    throw new AppError(400, "Неизвестное действие.");
  }
  async chat(u, d) {
    const q = String(d.question || "").trim(),
      mid = String(d.messageId || "");
    if (
      !q ||
      q.length > 2000 ||
      !Number.isInteger(d.revision) ||
      !mid.match(/^[\w-]{1,100}$/)
    )
      throw new AppError(400, "Проверьте сообщение.");
    if (![d.revision, d.revision + 1].includes(u.revision))
      throw new AppError(
        409,
        "Данные изменились в другой вкладке. Перезагрузите страницу.",
      );
    const at = u.state.messages.findIndex((m) => m.id === mid);
    if (at >= 0) {
      const m = u.state.messages[at],
        ans = u.state.messages[at + 1];
      if (m.role !== "user" || m.text !== q)
        throw new AppError(409, "Идентификатор сообщения уже использован.");
      if (ans?.role === "assistant")
        return json({ answer: ans.text, state: u.state, revision: u.revision });
      u.state.messages = u.state.messages.slice(0, at + 1);
    } else {
      if (u.revision !== d.revision)
        throw new AppError(
          409,
          "Данные изменились в другой вкладке. Перезагрузите страницу.",
        );
      u.state.messages.push({ id: mid, role: "user", text: q });
    }
    if (u.state.messages.length >= 80)
      throw new AppError(400, "История слишком длинная. Начните новый чат.");
    const answer = emergency(q) ? EMERGENCY : await ai(q, u.state, this.env);
    const cardEntry = fact(q);
    if (cardEntry)
      u.state.medicalCard = [cardEntry, ...u.state.medicalCard].slice(0, 120);
    u.state.messages.push({
      id: crypto.randomUUID(),
      role: "assistant",
      text: answer,
    });
    u.state = valid(u.state);
    u.revision++;
    await this.s.put("u:" + u.id, u);
    return json({
      answer,
      state: u.state,
      revision: u.revision,
      ...(cardEntry ? { cardEntry } : {}),
    });
  }
  async loginResponse(u, recovery) {
    const token = random(32);
    try {
      await this.s.put(
        "s:" + token,
        { uid: u.id, expires: Date.now() + 604800000 },
        { expirationTtl: 604800 },
      );
    } catch {
      throw new AppError(500, "Ошибка запуска аккаунта: SESSION-01");
    }
    return json(
      { ...pub(u), ...(recovery ? { recoveryCode: recovery } : {}) },
      200,
      `${COOKIE}=${token}; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=604800`,
    );
  }
  async identity(h) {
    const token = cookie(h)[COOKIE];
    if (!token) throw new AppError(401, "Войдите в аккаунт.");
    const s = await this.s.get("s:" + token),
      u = s ? await this.s.get("u:" + s.uid) : null;
    if (!s || s.expires < Date.now() || !u)
      throw new AppError(401, "Сессия закончилась. Войдите снова.");
    return { token, u };
  }
  async removeSessions(uid) {
    const all = await this.s.list({ prefix: "s:" });
    await this.s.delete(
      [...all].filter(([, v]) => v.uid === uid).map(([k]) => k),
    );
  }
}
async function ai(q, state, env) {
  if (!env.CHEAPAI_API_KEY)
    throw new AppError(503, "Ключ AI ещё не подключён в Cloudflare.");
  const deep =
      q.length > 350 ||
      /стресс|тревог|депресс|паник|смес|прикорм|задерж|не говорит|истерик|аутиз/i.test(
        q,
      ),
    ctl = new AbortController(),
    timer = setTimeout(() => ctl.abort(), 60000);
  try {
    const r = await fetch("https://cheapai.io/v1/chat/completions", {
        method: "POST",
        signal: ctl.signal,
        headers: {
          "Content-Type": "application/json",
          Authorization: "Bearer " + env.CHEAPAI_API_KEY,
        },
        body: JSON.stringify({
          model: deep ? "gpt-5.6-sol" : "gpt-5.6-luna",
          messages: [
            { role: "system", content: SYSTEM },
            { role: "system", content: context(state, q) },
            { role: "user", content: q },
          ],
          max_tokens: 450,
          temperature: 0.5,
        }),
      }),
      b = await r.json(),
      text = b?.choices?.[0]?.message?.content?.trim();
    if (!r.ok || !text)
      throw new AppError(502, "AI-сервис временно не ответил.");
    return text;
  } catch (e) {
    if (e instanceof AppError) throw e;
    throw new AppError(504, "AI-сервис не успел ответить за минуту.");
  } finally {
    clearTimeout(timer);
  }
}
function context(s, q) {
  const p = s.profile;
  let x = !p
    ? "Профиль не заполнен."
    : p.stage === "pregnancy"
      ? `Беременность: ${p.week} недель на ${p.weekDate}; роль ${p.role}.`
      : `Дата рождения ребёнка ${p.birthDate}; вычисли точный возраст; роль ${p.role}; кормление ${p.feeding}; сон ${p.sleep || "не указан"}.`;
  if (p?.health && p.healthConfirmed)
    x += ` Подтверждённые особенности: ${p.health}.`;
  const hist = s.messages
      .slice(-11)
      .filter(
        (m, i, a) => !(i === a.length - 1 && m.role === "user" && m.text === q),
      )
      .map((m) => `${m.role}: ${m.text.slice(0, 700)}`)
      .join("\n"),
    card = s.medicalCard
      .slice(0, 12)
      .map((e) => `${e.date}: ${e.text}`)
      .join("\n");
  return `Профиль: ${x}\nКарта:\n${card || "пусто"}\nИстория:\n${hist || "пусто"}`;
}
function valid(s) {
  if (!s || typeof s !== "object") throw new AppError(400, "Неверные данные.");
  const v = { ...blank(), ...s };
  if (
    !Array.isArray(v.messages) ||
    v.messages.length > 80 ||
    v.messages.some(
      (m) =>
        !m ||
        !["user", "assistant"].includes(m.role) ||
        typeof m.id !== "string" ||
        typeof m.text !== "string" ||
        m.text.length > 2500,
    )
  )
    throw new AppError(400, "Неверная история.");
  if (!Array.isArray(v.medicalCard) || v.medicalCard.length > 120)
    throw new AppError(400, "Неверная карта.");
  return v;
}
function blank() {
  return {
    profile: null,
    saved: [],
    completed: [],
    events: {},
    preferences: { repeat: "never", push: false },
    messages: [],
    medicalCard: [],
  };
}
function pub(u) {
  return {
    user: { id: u.id, email: u.email },
    state: u.state,
    revision: u.revision,
  };
}
function mail(v) {
  const e = String(v || "")
    .trim()
    .toLowerCase();
  if (!/^\S+@\S+\.\S+$/.test(e) || e.length > 254)
    throw new AppError(400, "Укажите корректную электронную почту.");
  return e;
}
function pass(v) {
  const p = String(v || "");
  if (p.length < 12 || p.length > 200)
    throw new AppError(400, "Пароль должен содержать не меньше 12 символов.");
  return p;
}
async function pwd(p, pepper) {
  if (!pepper) throw new Error("password pepper is missing");
  const salt = random(16);
  return { salt, hash: await pbkdf(p, salt, pepper) };
}
async function match(p, r, pepper) {
  return !!r && !!pepper && (await pbkdf(p, r.salt, pepper)) === r.hash;
}
async function pbkdf(p, salt, pepper) {
  let material = enc.encode(`${pepper}:${p}`);
  for (let stage = 0; stage < 3; stage++) {
    const key = await crypto.subtle.importKey(
      "raw",
      material,
      "PBKDF2",
      false,
      ["deriveBits"],
    );
    material = new Uint8Array(
      await crypto.subtle.deriveBits(
        {
          name: "PBKDF2",
          salt: enc.encode(`${salt}:${stage}`),
          iterations: 70000,
          hash: "SHA-256",
        },
        key,
        256,
      ),
    );
  }
  return hex(material);
}
async function sha(v) {
  return hex(await crypto.subtle.digest("SHA-256", enc.encode(v)));
}
function hex(v) {
  return [...new Uint8Array(v)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}
function random(n) {
  return hex(crypto.getRandomValues(new Uint8Array(n)));
}
function code() {
  return `${random(3)}-${random(3)}-${random(3)}-${random(3)}`.toUpperCase();
}
function cookie(h) {
  return Object.fromEntries(
    h
      .split(";")
      .map((x) => x.trim().split("=").map(decodeURIComponent))
      .filter((x) => x.length === 2),
  );
}
function clearCookie() {
  return `${COOKIE}=; Path=/; HttpOnly; Secure; SameSite=None; Max-Age=0`;
}
function fact(q) {
  const n = q.toLowerCase().replaceAll("ё", "е");
  if (
    !/сделал|сделали|прошли|были у|сходили|начал|начала|начали|привив|вакцин|анализ|осмотр|педиатр|узи/.test(
      n,
    )
  )
    return null;
  return {
    id: crypto.randomUUID(),
    date: new Date().toISOString().slice(0, 10),
    text: q.slice(0, 500),
    source: "chat",
  };
}
function emergency(q) {
  return /не дыш|задыха|судорог|без созн|отравил|сильн.*кровотеч|не хочу жить|суицид|навредить себе/i.test(
    q,
  );
}
class AppError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}
async function proxy(req, b, env) {
  if (
    !env.PROXY_TOKEN ||
    req.headers.get("Authorization") !== `Bearer ${env.PROXY_TOKEN}`
  )
    return json({ error: "Unauthorized" }, 401);
  if (!env.CHEAPAI_API_KEY)
    return json({ error: "CHEAPAI_API_KEY is not configured" }, 503);
  return fetch("https://cheapai.io/v1/chat/completions", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${env.CHEAPAI_API_KEY}`,
    },
    body: JSON.stringify(b),
  });
}
function cors(h, o) {
  if (o === ORIGIN) {
    h.set("Access-Control-Allow-Origin", o);
    h.set("Access-Control-Allow-Credentials", "true");
    h.set("Access-Control-Allow-Headers", "Content-Type");
    h.set("Access-Control-Allow-Methods", "POST, OPTIONS");
  }
  h.set("Cache-Control", "no-store");
  h.set("Vary", "Origin");
}
function out(v, s, o) {
  const r = json(v, s);
  cors(r.headers, o);
  return r;
}
function json(v, s = 200, c) {
  const h = {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-store",
  };
  if (c) h["Set-Cookie"] = c;
  return new Response(JSON.stringify(v), { status: s, headers: h });
}
const EMERGENCY =
  "Если прямо сейчас есть угроза жизни, затруднённое дыхание, судороги, потеря сознания, сильное кровотечение, отравление или риск навредить себе либо ребёнку — звоните 112. Не ждите ответа чата.";
const SYSTEM =
  "Ты — тёплый русскоязычный информационный помощник для беременных, мам и пап детей до 3 лет. Используй профиль, точный возраст, историю и карту. Отвечай понятно и пошагово. Не ставь диагнозы, не назначай лечение и не рассчитывай дозировки. При медицинских вопросах направляй к врачу, при угрозе жизни — 112. Не выдумывай факты.";
