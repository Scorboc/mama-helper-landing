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
