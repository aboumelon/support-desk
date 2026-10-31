# Tarvio SupportDesk — Desktop Design Refinement

> Archived approved design baseline, captured before implementation. Statements below
> about unchanged application source and unavailable authenticated evidence describe
> the design exploration, not the current branch. Phase 1 implementation and fresh
> frontend evidence are tracked in [Phase 1 verification](../evidence/inbox-phase1/README.md).
> The comparison board/HTML concepts remain in the separately delivered design package;
> only this specification is archived here. Later-phase proposals below remain approved
> design intent, **not implemented** by this PR.

Date: 31 October 2026. Design exploration only. Application source and backend contracts are unchanged.

## Evidence and deliverables

The comparison board is `index.html`, served at `/desktop/` by the existing proposal preview on port 5174. The earlier responsive board remains at the preview root, with a link to this desktop board. Native-resolution PNGs and HTML concepts are provided for:

1. Operator Inbox 1440 × 1000, normal conversation.
2. Operator Inbox 1920 × 1080, source inspector open.
3. Customer Chat 1440 × 1000, mixed-language answer and citation.
4. Knowledge 1440 × 1000, 20 fictional documents.
5. Knowledge 1920 × 1080, expanded version history.
6. Additional operator concept at 1280 × 900.

The 24px design-concept ribbon in rendered images is presentation labeling, not proposed application UI. Product pane heights exclude that ribbon.

Historical references: `docs/evidence/portfolio/operator-1440.png`, `customer-1440.png`, and `knowledge-1440.png`. There is no historical 1920px reference; the board labels the native dimensions and does not pretend these are same-viewport pixel comparisons.

Current browser evidence: public entry page at 1440px and 1920px on port 5173, with the API unavailable. No current authenticated inbox, messaging, source retrieval, ownership mutation or Knowledge operation was tested. Docker and uv remain unavailable. The historical screen evidence was reviewed alongside the current source and documentation.

The HTML concepts support limited source opening/closing, filter pressed styling and version disclosure. Other controls illustrate placement only. Mockup render checks are not application tests, accessibility certification or product performance measurements.

## A. Direction

Retain Tarvio's ink navigation (#202735), cobalt (#354AE8), selected lavender (#EEF0FF), white surfaces, neutral canvas, Estedad, existing mark, restrained borders and conversation-thread motif. Preserve the real responsibility and lifecycle model, explicit fictional/simulated disclosure and customer/staff distinction.

Use desktop space for persistent conversation switching, a conditional source reference, stable column alignment and bounded reading lanes. Do not add dashboards, contact profiles, made-up queue counts, analytics, new search/sort capabilities, extra settings or decorative panels.

Do not stretch mobile composition across the screen. Keep the approved list/detail model below 1120px, then introduce genuine simultaneous work areas on desktop.

## B. Operator Inbox

### Primary decision

Two working panes (conversation index + active conversation), plus the navigation rail. A third working pane appears contextually when a source is selected and the viewport is at least 1440px. Do not reserve a persistent empty source pane. Do not add draggable splitters or collapse preferences.

### Alternatives

- Persistent source pane: immediate access, but wastes 320–360px when no citation is selected, or invites placeholder content. Rejected.
- Dialog at every width: easiest to reuse, but interrupts operators comparing a response against its evidence on wide desktops. Rejected as universal default.
- Contextual aside with width fallback: preserves side-by-side reference where space permits, reuses SourceInspector/Modal, and keeps the list visible. Selected.

### Dimensions (CSS pixels, borders included)

| Viewport | Rail | Index | Conversation, closed source | Source | Conversation, open source |
|---|---:|---:|---:|---:|---:|
| 1280 | 84 | 304 | 892 | Dialog | 892 behind dialog |
| 1440 | 92 | 320 | 1028 | 320 | 708 |
| 1920 | 92 | 344 | 1484 | 360 | 1124 |

Rules:

- 1120–1439px: 84px rail + 304px index; sources use shared dialog.
- 1440–1599px: 92px rail + 320px index; contextual source aside 320px.
- At least 1600px: 92px rail + 344px index; contextual source aside 360px.
- Below 1120px: the approved list/detail model. Do not preserve split panes merely because CSS can fit them.
- Source breakpoint is refined from the earlier approximate 1400px to 1440px. Keeping the index stable and a ~680px minimum conversation pane requires this extra allowance.
- Minimum split-mode conversation pane is 680px including padding; this is a layout budget, not a narrow-screen min-width that creates overflow.
- Do not shrink the index when the source opens. It is the operator's primary switching tool.

### Reading and composer

- Conversation header: 76px, 24px inline padding, 38px avatar. Title 15px semibold, reference 12px.
- Status strip: 12px block-start and 24px inline margins, 8×12px internal padding; responsibility at RTL start, connection at opposite end. No duplicated claim/resolve controls inside it.
- Transcript: 24px inline padding, maximum lane 840px; lane contains 28px thread gutter.
- Assistant message: fit-content, max 720px or available space. Customer: fit-content, max 560px and 85% of available message area. Operator: same bounded max as assistant, ink edge instead of cobalt.
- Body: 15px, line-height 1.85. Sender 12–13px semibold; time and receipt 12px. Use one sender label; remove redundant `customer / customer message` labeling.
- Bubble padding: 12px block, 16px inline. Gap 16px.
- Composer shares the 840px lane, aligned with transcript boundaries. Keep 24px outer gutters, 12px internal padding, 52px minimum editable area and up to 160px expansion. Empty preview textarea is illustrative; implementation retains existing autosizing policy unless deliberately adjusted.
- Keep one 44px primary workflow control appropriate to ownership. The normal mockup shows an accepted conversation and the existing resolve action. Use the existing claim action for queued conversations, reopen for resolved, and existing overflow actions for release/return-to-assistant.
- Compose, timeline and control-event order remain real. Never fabricate staff names or timestamps.

### Index

- Search 44px high; 16px inline inset, growing to 20px at 1600px.
- Four visible 44px filter buttons: باز / در صف / با من / بسته‌شده. Preserve backend filter identifiers. Native buttons in a labeled group, aria-pressed state; not incomplete ARIA tabs.
- Row padding 12px; 14px at 1600px. Title 13px semibold; preview 12px / 1.8, clamped to two lines; status and reference 12px.
- Selected row retains lavender background, subtle border and cobalt inline-start edge. No new background gradient or large avatar.
- Row height remains content-driven. Preserve unread badge from real data; never infer counts from fictional mockup rows.
- Entire row remains the conversation selection target; accessible name includes the visible title, with reference/status/unread in description.

### Scrolling and source behavior

Index, transcript and source have independent vertical scroll areas. Conversation header/status and composer do not scroll away with the transcript. The desktop page itself must not create a competing vertical scroller.

On source open: preserve selected conversation and list width; reflow only the middle pane; restore the same message's viewport offset if the reader is not at bottom. If already at bottom, remain bottom-anchored. No animated pane-width transition. Update selected citation state. Do not reset transcript to first or last message indiscriminately.

On close: restore normal middle-pane width and scroll anchor, return focus to the triggering source button. Do not leave a blank inspector column.

Switching conversations closes the source selected from the old conversation. Drafts remain scoped and preserved. The old citation must never remain attached to a different conversation.

Explicit keyboard opening focuses source heading (tabindex -1). Aside is nonmodal: no focus trap, background remains interactive. Escape closes only while focus is within that aside. Modal fallback uses existing focus containment, inert background and restoration.

Resizing across 1440px keeps the same selected source and changes its presentation to dialog/aside, preserving focus and avoiding simultaneous hidden focusable copies. At 1120px transition to list/detail without losing selection, drafts, filters or scroll position. These behaviors require implementation tests; the concept demonstrates layout, not the full state lifecycle.

### Ultrawide (optional)

At 2560px, retain 92/344/360px rail/index/source widths; do not expand message measure, add a fourth pane, or display a second conversation. Neutral space is preferable to unsupported product panels. The 840px lane remains the hard reading cap. No dedicated ultrawide visual or device verification is claimed.

## C. Customer Chat

### Decision

Keep a lighter, centered customer workspace with a persistent conversation list only at desktop widths. Use a source dialog on customer desktop at all widths, rather than copying the operator's conditional three-pane behavior. Customer source checks are task-focused and less frequent; stable chat geometry is more valuable than another permanent work region. This intentionally refines the previous generalized aside recommendation for customer chat.

### Geometry

- Global header: 68px, 32px inline padding, existing mark/brand at RTL start, disclosure and audience/logout controls. No separate staff workspace-status bar.
- Shell: width min(1320px, viewport minus 64px), centered, 24px top/bottom margin. Thus outer margins are 32px at 1280px (shell 1216px), 60px at 1440px, 300px at 1920px. Do not fill those margins with decorative content.
- Conversation list: 260px on desktop. Persistent split begins at 1120px; below that reuse approved list/detail.
- Transcript lane maximum: 800px, 24px padding. Assistant max 720px, customer max 560px/85%, same role distinction as operator.
- Header within conversation: 68px. Responsibility strip compact; no redundant secondary panel.
- Composer uses the 800px lane (implementation should align it to the customer transcript rather than inheriting the operator's 840px cap). 44px send target, input expands within bounded height.
- Handoff is a compact secondary row directly above composer. After handoff, show queue state and allow continued messaging; no made-up wait times or guaranteed availability.
- Source dialog: max 640px wide, max calc(100dvh - 32px) high, scroll inside. Below 760px retain the approved bottom sheet, max 85dvh.

### Mixed content

The mockup uses a new fictional answer with a Persian introductory block, a separate LTR quotation, Persian source text and a citation. It does not propose reinterpreting stored customer text.

Reuse MessageMarkdown. Apply dir=auto to appropriate paragraphs, headings, list items and quotes; LTR isolate URLs/IDs/technical spans; code uses a genuine monospace stack and its own horizontal scroll. Do not infer language from a Latin product name or automatically translate. Preserve simulated-provider disclosure, citation authorization and source-unavailable behavior.

Citation labels remain منبع S1 unless an actual title is already available from authorized data. Do not create N+1 source fetches just for prettier chips.

### Empty/loading/failure states

- Empty customer: first-message invitation and existing new-conversation action; do not create a dashboard or fictional conversation history.
- Loading: skeleton or concise loading notice inside the existing shell, not whole-screen disappearance on background refetch.
- List error: contextual retry, preserve active conversation if already loaded.
- Send failure: retain pending text and same idempotent retry; not a false saved state.
- Assistant queue/running/provisional: distinct real states, no fake typing while merely queued.
- Source unavailable: retain historical answer, explain reference is unavailable; network failures retain retry.
- Handoff failure: remain in actual responsibility state and expose retry. Don't imply successful handoff before confirmation.

## D. Knowledge

### Alternatives and selected approach

1. Compact unaligned document cards: works for five, but makes comparisons harder with 20–100 rows and duplicates chrome. Keep mobile stacked units, not desktop cards.
2. Plain lightweight table: excellent comparison but insufficient for variable-length version histories and failure explanations if forced into fixed cells.
3. Expandable document rows with stable columns: selected. On desktop, use native table semantics with an adjacent colspan history row; on mobile, present the same document data as the approved stacked unit. This is one lifecycle presentation, not a new grid application.

Do not add sortable headings, document search, selection checkboxes, bulk actions, invented file metadata, pagination or analytics. None is necessary to improve the existing surface.

### Dimensions

- Workspace rail remains 84px below 1440px / 92px above.
- Content gutters: 32px desktop, 24px tablet, 16px mobile.
- Main content maximum: 1440px, centered within the workspace after gutters. At 1440px viewport the main content is 1284px; at 1920px it is capped at 1440px, keeping actions near titles rather than filling the entire screen.
- Page title 24px; description 12px; main upload button 44px.
- Header to activation 24px; activation padding 16×20px, radius 11px, cobalt edge. Keep one activation switch for new conversations.
- Four columns, right to left: flexible title; active version 160px; usability 250px; actions 300px. Below 1440px, 140/220/280px fixed columns and remaining width for title. When this stops fitting below desktop split width, transition to stacked rows, not horizontal scrolling.
- Header height 44px, 12px labels. Ordinary row minimum 84px; 14px block and 20px inline padding, 44px controls. Long titles/failure notes may increase height; do not clamp away essential lifecycle information.
- Title 13px semibold; secondary/status/versions/actions 12px. 32px book icon container. No active-version UUID in the ordinary row.
- Actions: existing replacement, withdrawal and an explicit history disclosure. Withdrawal is restrained danger text, not a large red button. Confirmation still required.
- Expanded history is full width immediately below its parent row, lightly tinted container. Version/status/reference/active designation align; no second screen, nested vertical scroller or active-version toggle. Disclosure button has aria-expanded and aria-controls; history uses proper list/table structure.

### Lifecycle precedence

Usability refers to the active version, not merely the most recently uploaded version:

- Active ready v2 + failed v3: primary badge ready; secondary text says v3 failed and v2 is still active.
- Active ready v1 + processing v2: primary ready; secondary replacement progress.
- No ready active version: processing or failed, with clear explanation.
- Withdrawn: withdrawn; preserve existing disabled mutation behavior.

Version history remains derived from actual API versions. Do not invent dates, sizes or uploaders that are absent from the current presentation contract.

### Five, twenty and one hundred documents

Use the same component, no density-mode preference:

- Five: a compact natural-height list, not stretched rows to fill the viewport.
- Twenty: one page scroll, sticky column heading, document actions visible per row.
- One hundred: same behavior, collapsed histories by default, no virtualization required without measured need. Preserve expanded document IDs through polling; don't collapse a history every three seconds when the query refreshes.

One workspace content scroller owns page/table/history. No independently scrolling table embedded inside a scrolling page. Sticky headings stick at the top of that scroller and must not obscure focused row actions. Expanded history remains in normal flow.

Current API listing orders documents by created_at descending and limits to 100; no cursor/total is supplied. Display the number in this returned list, not an installation-wide total. Beyond 100 is an existing API boundary, not solved by this design proposal. Do not silently add pagination or change contracts.

## E. Tokens and accessibility

Keep core color, radius and Estedad tokens. Only apply the previously proposed necessary refinements:

- Focus on light: 3px solid #354AE8, 2px offset; dark rail focus #AEB8FF.
- Essential input boundary #7A8596, separate from #E1E5EB surface dividers.
- Shared spacing 4/8/12/16/24/32px where touched; no global refactor.
- Body 15px / 1.85. Visible metadata at least 12px. Large monitors are not a reason to shrink type.
- Minimum control target 44px; do not achieve density by tiny click targets.
- Code: ui-monospace, SFMono-Regular, Consolas, monospace. Keep LTR and horizontal overflow local.

Keyboard and RTL:

- Real button/link semantics, meaningful conversation names including visible title; described unread/reference/status.
- Filters are pressed buttons, not incomplete tabs. Standard Tab/Enter/Space; no custom keyboard shortcuts required.
- Native table headers use scope=col. No role=grid or spreadsheet keyboard model.
- History opening leaves focus on its disclosure; closing cannot leave focus hidden inside the history.
- Incoming committed messages announce once politely; no history/token announcement flood and no unsolicited focus movement.
- Right-pointing SVG Back chevron in RTL, logical CSS, fa-IR counts; Latin IDs, versions and citations remain isolated.
- Target WCAG 1.4.3 text contrast, 1.4.10 reflow, 1.4.11 non-text contrast, 2.4.7 visible focus, 2.4.11 unobscured focus, 2.5.8 target sizing, 4.1.2 semantics and 4.1.3 status messages. Rendered screen-reader/zoom tests are still necessary; no conformance claim is made.

## F. Implementation impact and acceptance

Reuse Desk, ConversationPane, Timeline, SourceInspector, MessageMarkdown, Knowledge, UploadDialog, documentPresentation, Button, Icon, Modal, EmptyState, DemoIndicator and current routing/query/draft infrastructure. Small local helper components are acceptable; no new design-system package or state architecture is required.

Likely files:

- apps/web/src/styles/app.css: pane budgets, content caps, row styles, source breakpoints, source/dialog audience distinction. Only consolidate conflicting rules for touched components.
- apps/web/src/features/conversation/desk.tsx: layout mode, list hierarchy, action placement and scoped source state.
- apps/web/src/features/conversation/timeline.tsx: metadata hierarchy, reading lane and scroll-anchor preservation on pane width change.
- apps/web/src/features/conversation/source-inspector.tsx: contextual aside for staff >=1440px, dialog fallback, customer dialog policy, focus/close behavior.
- apps/web/src/lib/markdown.tsx: block direction and code presentation; do not rewrite stored body strings.
- apps/web/src/main.tsx: rail widths/customer frame, preserving audience/auth boundaries.
- apps/web/src/features/knowledge/knowledge.tsx and presentation.ts: aligned expandable rows and truthful usability state.
- apps/web/src/components/ui.tsx: only small shared focus/loading/empty-state additions where useful.
- apps/web/src/locales/fa.json and en.json: centralized labels.

No backend schema, contracts, message authority, ownership rules, citation authorization, polling interval, idempotency or provider execution change is required by this desktop proposal. The previously discussed demo answer/title improvements are separate coordinated fixture work, not hidden prerequisites for the desktop layout.

Acceptance tests for implementation:

1. At 1280/1440/1920px, compare measured panes against the dimension table, with and without sources; no document-level overflow.
2. At 1439/1440 and 1599/1600px, verify conditional pane policy and stable conversation/index. At 1119/1120px verify approved list/detail transition.
3. Source open/close keeps viewport anchor, selected citation and draft; switching conversations cannot leak an old source. Keyboard source open, Escape and focus restoration work for aside/dialog.
4. Source loading/error/410 states keep the correct layout; no empty placeholder inspector is reserved when closed.
5. Conversation switching, drafts, history prepends, new-message indicator and persistent-send retry still pass the real-backend browser suite.
6. Knowledge datasets of 5/20/100 returned documents show no clipped actions, false total, accidental history reset or nested page/table scroll. Long Persian titles and status notes may expand rows naturally.
7. Failed replacement preserves ready active version; withdrawn action rules and upload/activation mutations remain unchanged.
8. At 200% zoom and 320-CSS-pixel-equivalent reflow, use the narrower existing model without forcing desktop minimum widths.
9. Persian/English paragraphs, headings, lists, code and URLs render without page overflow; safe Markdown policy remains unchanged.
10. Keyboard-only and NVDA/VoiceOver review verifies names, announcements, row disclosure and unclipped focus. Mockup interactions are not evidence that these application tests passed.

## G. Quality review and priorities

Criticism of earlier proposal visuals: full-width list/detail was a tablet solution, not a desktop composition; applying it to desktop would slow frequent switching. The reconstructed board also used a mobile-like Knowledge presentation that did not demonstrate cross-row scanning or 20-document scale. These desktop concepts deliberately retain simultaneous working panes and aligned rows instead.

Self-review revisions: removed detached version-history bands; eliminated prominent UUIDs from default document rows; increased application secondary text to 12px; placed the operator viewport at the latest reply; avoided fake statistics, timestamps and panels. The design does not attempt to eliminate every blank area by making text unreadably wide. Neutral margins around a capped reading lane are intentional.

Essential for portfolio quality (P0, relative effort):

- Desktop pane budget and conditional source policy: Medium.
- Consistent bounded transcript/composer alignment, legible content and source anchors: Medium.
- Visible filters, correct semantics/focus and truthful action feedback: Small–Medium.

High-value next (P1):

- Compact expandable Knowledge rows and active-versus-latest state hierarchy: Medium.
- Customer width cap and deliberate dialog policy: Small–Medium.
- Fixture naming/content formatting from prior proposal, separately tested: Small–Medium.

Optional (P2):

- Dedicated ultrawide tuning and expanded visual regression matrix.
- No draggable splitters, saved density preference, new dashboard, advanced document controls or architectural rewrite is recommended now.

Build the Inbox pane budget first; verify width transitions and actual conversation state before refining Knowledge. Stop at this proposal in the present task; no application implementation is authorized.
