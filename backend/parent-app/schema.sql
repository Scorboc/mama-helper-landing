CREATE TABLE IF NOT EXISTS mh_users (
 id TEXT PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL,
 recovery_hash TEXT NOT NULL, created_at BIGINT NOT NULL, consent_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mh_sessions (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 expires_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS mh_sessions_user ON mh_sessions(user_id);
CREATE TABLE IF NOT EXISTS mh_state (
 user_id TEXT PRIMARY KEY REFERENCES mh_users(id) ON DELETE CASCADE,
 encrypted_data TEXT NOT NULL, revision BIGINT NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mh_limits (
 key TEXT PRIMARY KEY, count BIGINT NOT NULL, until_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS mh_push (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 endpoint_hash TEXT PRIMARY KEY, encrypted_subscription TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS mh_delivery (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 event_id TEXT NOT NULL, endpoint_hash TEXT NOT NULL, sent_at BIGINT NOT NULL,
 PRIMARY KEY(user_id,event_id,endpoint_hash)
);
CREATE TABLE IF NOT EXISTS mh_daily (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 child_id TEXT NOT NULL, day TEXT NOT NULL, encrypted_data TEXT NOT NULL,
 version BIGINT NOT NULL DEFAULT 0, viewed BIGINT NOT NULL DEFAULT 0,
 updated_at BIGINT NOT NULL, PRIMARY KEY(user_id,child_id,day)
);
CREATE TABLE IF NOT EXISTS mh_daily_feedback (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 request_id TEXT NOT NULL, child_id TEXT NOT NULL, day TEXT NOT NULL,
 encrypted_data TEXT NOT NULL, PRIMARY KEY(user_id,request_id)
);
CREATE TABLE IF NOT EXISTS mh_daily_push (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 day TEXT NOT NULL, slot BIGINT NOT NULL, sent_at BIGINT NOT NULL,
 PRIMARY KEY(user_id,day,slot)
);
CREATE TABLE IF NOT EXISTS mh_feedback (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 request_id TEXT NOT NULL, encrypted_data TEXT NOT NULL, created_at BIGINT NOT NULL,
 PRIMARY KEY(user_id,request_id)
);
CREATE TABLE IF NOT EXISTS mh_paid_access (
 user_id TEXT PRIMARY KEY REFERENCES mh_users(id) ON DELETE CASCADE,
 period_key TEXT NOT NULL, starts_at BIGINT NOT NULL, ends_at BIGINT NOT NULL,
 answer_limit BIGINT NOT NULL CHECK(answer_limit>=0)
);
CREATE TABLE IF NOT EXISTS mh_birthday_gifts (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 child_id TEXT NOT NULL, year BIGINT NOT NULL, remaining BIGINT NOT NULL CHECK(remaining>=0 AND remaining<=5),
 PRIMARY KEY(user_id,child_id,year)
);
CREATE TABLE IF NOT EXISTS mh_guidance_delivery (
 user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 child_id TEXT NOT NULL, topic TEXT NOT NULL, sent_at BIGINT NOT NULL,
 PRIMARY KEY(user_id,child_id,topic)
);
