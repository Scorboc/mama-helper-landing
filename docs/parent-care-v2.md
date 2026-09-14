# Parent care v2 — closed-test release

## Implemented

- Child name and live age / pregnancy term above chat; profile correction link.
- Server-side current age in every AI request. Only current conversation is used.
- Short, step-by-step and detailed answer styles; parent-support starters.
- Up to 20 archived conversations plus active conversation, shared family profile and approved memory.
- Pending memory proposals: edit, reject, confirm as a parent observation or reported doctor confirmation. Older entries remain marked unverified in model context.
- Upstream SSE to browser NDJSON, paragraph buffering for output checks. This reduces perceived delay when the provider streams, not model computation time. No simulated typing.
- Explicit retry keeps message ID and revision; aborted upstream responses are not billed against test quota. Successfully persisted answers are replayed without another AI call.
- Independent server quota of 70 successful answers for test logins 2–5. Login 1 remains unrestricted. Test 5 password is 5; use fictitious data only.
- Helpful / unhelpful / unsafe feedback and feature requests. Context attachment requires explicit consent. Reports remain in private Durable Object storage, never GitHub issues.
- Source honesty instructions and filters. Online retrieval is NOT connected. No claim of clinical verification.
- Private, single-use, seven-day registration invitation links; personal password and recovery code. Regular individual registration still works.

## Organiser operations

Use `node ai-proxy/admin.mjs invite` or `node ai-proxy/admin.mjs feedback` in a trusted environment with the existing `PROXY_TOKEN` configured. Never expose that secret in frontend, source code or chat. Optional MAMA_API_URL overrides endpoint. Feedback export returns up to 200 items and a cursor; pass cursor as the next CLI argument. Reports may contain personal data; do not upload them into this public repository.

The assistant can analyse an authorised private export when asked. This is not automatic background monitoring. Invitations are not automatically emailed; the organiser shares the link privately. No invitation link is created merely by deployment.

## Verification

Run `node --test ai-proxy/care.test.mjs`, `npx tsc --noEmit`, `npm run build`.
Worker deployment runs safeguard tests before publishing. Test mocks verify logic, not the medical correctness of arbitrary generated answers. Real-provider latency and partial streaming must also be checked after deployment.

## Release limits / required external work

- Clinical review by a qualified independent specialist remains required. Regex checks and another model are not a substitute.
- Internet search, vetted clinical retrieval, background push and payments are not enabled by this change.
- Before public launch: confirm personal-data handling, provider terms, consent wording and retention policies with appropriate specialists; do not collect real health records during the shared-account test.
- General safety gates cannot guarantee all unsafe outputs are caught. Paragraphs may appear before the full answer completes; on error the temporary answer is removed.
- Frontend is published through Poehali; GitHub Worker deployment alone does not publish the website UI.
