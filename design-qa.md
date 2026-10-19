# MAMA helper · olive room chat · 2026-10-18

final result: passed

## Visual truth and rendered evidence

- Selected target: `C:/Users/Admin/Documents/Codex/2026-10-17/codex-mcp-add-motionsites-npx-y/outputs/mama-concept-3-olive-evening.png` (third displayed ImageGen result).
- Source pixels: 853 × 1844. Normalized in the comparison browser to a 390 × 844 CSS viewport using object-fit contain; no stretching or phone frame.
- Implementation: `C:/Users/Admin/Documents/Codex/2026-10-17/codex-mcp-add-motionsites-npx-y/outputs/mama-olive-mobile.png`, 390 × 844 pixels, deviceScaleFactor 1.
- Full comparison: `C:/Users/Admin/Documents/Codex/2026-10-17/codex-mcp-add-motionsites-npx-y/outputs/mama-olive-reference-comparison.png`.
- Focused header/logo/composer/navigation comparison: `C:/Users/Admin/Documents/Codex/2026-10-17/codex-mcp-add-motionsites-npx-y/outputs/mama-olive-detail-comparison.png`.
- State: signed-in synthetic child profile; the same two support messages as the concept, greeting visible, Chat selected, composer empty, menus closed. All assets loaded and the arrival animation finished before final capture.

## Findings and comparison history

1. Resolved P1: legacy white fields, purple send button and pale navigation leaked into the first implementation. Evidence: `outputs/mama-olive-mobile-first.png`. Scoped room tokens and targeted overrides now render the field, microphone, send button, profile and navigation in olive/amber. Global themes outside this scene remain supported.
2. Resolved P2: a JavaScript viewport-height value briefly retained the previous height during resizing (568px viewport with navigation at 844px). Normal layout now uses native 100dvh; VisualViewport height is used only for a detected keyboard. Post-fix measured navigation bottoms are exactly 568, 932, 420 and 844px at those viewport heights.
3. Resolved P2: response utilities made the assistant bubble noticeably taller than the visual target. The author label remains accessible, while the collapsed existing actions now sit below the bubble. Opening actions still reveals all existing controls.
4. Final side-by-side comparison after the fixes: no actionable P0/P1/P2 findings. The olive palette, warm glass edges, amber mark, italic greeting, left assistant/right user hierarchy and anchored input/navigation match the selected direction.

## Required fidelity surfaces

- Typography: local Onest for functional text; locally hosted Lora italic for the greeting, with its OFL license. Body 15px, input 16px, menu 11px. Text remains readable and wraps naturally. Existing content and real profile age remain supported.
- Layout rhythm: compact 54px brand row and 54px profile row. At 390 × 844 the feed has 506px, composer begins at y=672 and bottom navigation ends at y=844. Only the feed scrolls during a long conversation; the document remains at scrollTop 0.
- Colors/tokens: warm olive surfaces and cream text, amber send action and urgent-help link; old purple/white overrides removed in this scene. Opaque text-bearing portions preserve contrast. Dialog overlays and buttons use the same warm palette.
- Assets: existing final video still retained for continuity with the actual film. The concept generation changed some furniture/lighting; copying that generated replacement would break the agreed film-to-chat continuity. Amber logo is a supplied generated transparent PNG; a real traced SVG master and provenance are saved separately. No CSS/SVG approximation replaces the logo image. Background remains static in chat.
- Copy/content: the selected greeting and synthetic example match the reference. Added exact profile age and the existing answer-action control preserve actual product behavior. The five navigation labels and urgent-help access are unchanged. Medical/account data is not sent to design tools.

## Interaction and responsive evidence

- Existing app checked at `http://127.0.0.1:5173/chat?scene=room`: new mark loaded, two existing messages present, composer/menu positions correct, no console errors. No real message or profile was changed for testing.
- Isolated fixture: sending a text message returns a new answer; all five sections open, returning to chat retains the typed draft. Quick marks and history/settings open and close with focus restoration. Urgent-help link remains outside the scroll.
- Long fixture: 24 messages; only `.room-chat-scroll` overflows. Its scroll position changes while composer y=672 and navigation y=774 remain unchanged at 390 × 844.
- Viewports verified: 320 × 568, 390 × 844, 430 × 932, and a reduced 390 × 420 viewport. No document overflow; five tabs and input remain on screen. The 420px case is reduced-height emulation, not a physical iOS keyboard test.
- TypeScript, changed-file ESLint and production build pass. The seven introduction/entry regression tests pass. No AI policy or backend changes; the 50-question medical/AI suite was not rerun for this visual change.
- Pages-path build checked in-browser under `/mama-helper-landing/`, including deep-link refresh, local fonts, room images, video loading and transition to chat. Video stays paused and its selected frame follows scrolling. No console errors on the final chat screen.

## Accepted constraints / follow-up

- The user explicitly requested more conversation space: the decorative upper gap is reduced relative to the concept. The greeting scrolls with messages and does not consume fixed header space.
- The existing room/video is the continuity source; this is a faithful implementation of the selected material/layout direction, not a claim of pixel-identical generated room geometry.
- The public Pages version is an interface review with synthetic, locally stored data and an explicit preview response if sending a question. It does not connect to real accounts or an AI backend. The unchanged main application continues using its configured API. The older public API hosts did not respond to the HTTPS verification attempt.
- P3: the traced SVG logo master is large and can be simplified for future brand exports; the UI uses the smaller original PNG.
- Physical-phone acceptance and real mobile keyboard behavior remain for the user's phone check. No physical-device pass is claimed.

## Published review verification

- Live review: `https://scorboc.github.io/mama-helper-landing/?intro=1`.
- GitHub Pages build is `built` for `bdaed2e06c38c0fbe881618c6bb9ee854f150f3c`, branch `room-preview`. Existing `main` stayed at `ac238d0930a0ffde34015f3f86df778b3ab287a9`.
- The live URL was opened in IAB at 390 × 844. Video metadata loaded (readyState 4), video remained paused, and scrolling the introduction to its end automatically opened the room chat.
- All five live navigation buttons became the active section in turn; deep-link refresh restored chat through the Pages fallback.
- Final live measurements: document 390 × 844, document scrollTop 0, input y=672, navigation bottom=844, 5 tabs, 2 example messages, logo and Lora loaded. No browser console errors; zero network requests to the preview API (all preview state is handled locally).
- Live screenshot: `C:/Users/Admin/Documents/Codex/2026-10-17/codex-mcp-add-motionsites-npx-y/outputs/mama-olive-public-mobile.png`.

## Implementation checklist

- [x] Selected third concept implemented in existing app.
- [x] Input and five menus anchored; a single message scroll.
- [x] Existing profile/dialogue/functions retained.
- [x] Real source assets and local licensed fonts used.
- [x] Browser interaction checks and matched visual comparisons completed.
- [x] No unresolved P0/P1/P2 visual findings.
