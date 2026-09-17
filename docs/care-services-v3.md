# Care services v3

## Implemented

- Mobile-first care hub in My Day; existing palette retained.
- Age-aware five-day plan, manual tasks, save AI response as an editable task.
- Parent-entered outcomes and optional in-app follow-up dates. Hard activities excluded for 14 days; AI gets latest results.
- Diary for sleep episodes, feeding, parent wellbeing, observations. Seven-day counts are exact sums of entered records, not diagnoses or full sleep totals.
- Parent-confirmed development events and event-specific home safety checklist.
- Visit notes, question preparation, text export, exact copying of clinician instructions to tasks (no AI alteration).
- AI service forms: immediate situation, household games, behavior, dad mode, emotional support, kindergarten, school, Russian documents/benefits navigation.
- Per-answer basis/source passport. Optional retrieval from five fixed official pages, with timeout/failure transparency. This is NOT whole-web search, a comprehensive clinical KB, or medical validation of every claim. No numerical confidence score.
- Browser speech recognition with explicit audio-provider disclosure; recognized text is reviewed before submission. Local Russian speech synthesis only; unavailable voices are explained.
- Neutral ICS calendar export without health details.
- Server-side validation and account-scoped storage. Existing accounts are migrated lazily without removing history. Existing quota and safety checks retained.

## Limits to show to users

- Follow-ups appear when the cabinet is opened, not through background push. VAPID/scheduler not configured.
- School/dad/support are specialized AI workflows, not staffed professional services. No diagnosis or treatment.
- Documents navigator does not calculate entitlement or guarantee current amounts; links to SFR. Official page availability varies by network.
- Browser audio depends on support and user permission. No always-on listening.
- Plan uses a small curated set of low-risk activities plus optional AI adaptation, not a comprehensive developmental assessment.
- No subscriptions/payments added. Shared test accounts must use synthetic data.

## QA

`node --test ai-proxy/care.test.mjs ai-proxy/services.test.mjs`
`npx tsc --noEmit && npm run build`
`node scripts/test-parent-model.mjs && node scripts/test-preschool.mjs`

Worker deployment runs ten live scenario requests in an isolated synthetic account and deletes it afterward. Failures are visible in GitHub Actions; passing unit tests does not prove live availability or clinical safety. Browser QA and Poehali publishing status must be reported separately.
