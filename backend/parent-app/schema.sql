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
CREATE TABLE IF NOT EXISTS mh_email_status (
 user_id TEXT PRIMARY KEY REFERENCES mh_users(id) ON DELETE CASCADE,
 required INTEGER NOT NULL, verified_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS mh_email_tokens (
 token_hash TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, credential_hash TEXT NOT NULL, expires_at BIGINT NOT NULL, created_at BIGINT NOT NULL
);
CREATE TABLE IF NOT EXISTS mh_email_outbox (
 id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, encrypted_message TEXT NOT NULL, expires_at BIGINT NOT NULL,
 lease_until BIGINT NOT NULL, attempts INTEGER NOT NULL, delivered_at BIGINT NOT NULL, status TEXT NOT NULL
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

CREATE TABLE IF NOT EXISTS mh_care_records (owner_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE, child_id TEXT NOT NULL, id TEXT NOT NULL, encrypted_data TEXT NOT NULL, PRIMARY KEY(owner_id,child_id,id));
CREATE TABLE IF NOT EXISTS mh_family_access (id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE, child_id TEXT NOT NULL, guest_id TEXT REFERENCES mh_users(id) ON DELETE CASCADE, token_hash TEXT UNIQUE, expires_at BIGINT NOT NULL, permission TEXT NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS mh_family_guest ON mh_family_access(owner_id,child_id,guest_id);
CREATE TABLE IF NOT EXISTS mh_product_suggestions (
 id TEXT PRIMARY KEY, owner_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 week_id TEXT NOT NULL, encrypted_data TEXT NOT NULL, status TEXT NOT NULL,
 created_at BIGINT NOT NULL
);
CREATE INDEX IF NOT EXISTS mh_product_suggestions_week ON mh_product_suggestions(week_id,status,created_at);
CREATE TABLE IF NOT EXISTS mh_suggestion_votes (
 ballot_week TEXT NOT NULL, user_id TEXT NOT NULL REFERENCES mh_users(id) ON DELETE CASCADE,
 suggestion_id TEXT NOT NULL REFERENCES mh_product_suggestions(id) ON DELETE CASCADE,
 created_at BIGINT NOT NULL, PRIMARY KEY(ballot_week,user_id)
);
