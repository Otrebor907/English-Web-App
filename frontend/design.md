# Design — Prima conversazione

Locked design system for the "Prima conversazione" English-learning app. Every
screen redesign reads this file before touching code. Amend this file when the
system needs to grow — don't invent a parallel system per screen.

## Genre
playful

## Theme
Hum — the catalog's vibrant/alive register. Cream-pear paper, three accents
(pear-yellow primary, sky-cyan secondary, coral-red pop), rounded sans
throughout, mandatory hover/paint motion, one character moment. Chosen because
the brief — a daily English-learning path for adults, built around streaks,
progress and small wins — is Hum's canonical test brief ("learning platforms,
daily-thing apps, curiosity, considered but joyful").

## Screen families

This is a web app, not a marketing site — Hallmark's landing-page
macrostructures don't map 1:1 onto authenticated screens. Each screen family
below borrows the *closest* macrostructure's rhythm, not its literal shape.

- **Auth** (`/login`, `/registrati`) — Split Studio diptych: copy + character
  on the left, form card on the right. Unchanged shape from the previous
  build, refined voice and componentry.
- **Percorso** (dashboard) — Bento-flavoured index: a big rounded stat
  (lessons completed) anchors the page heading, followed by a card list with
  per-area colour-shift (signature move #3).
- **Lezione** (content + quiz) — Narrative Workflow: the section carousel is
  a numbered stage rail; quiz cards share the same button/card system.
- **Progressi / Profilo** — Stat-Led simple pages: one big rounded number,
  minimal chrome.
- **Contenuti da completare** (staff only) — Catalogue grid, restyled.

## Typography
- Display: Plus Jakarta Sans, weight 600, tracking -0.025em
- Body: Plus Jakarta Sans, weight 400 (500 for inline emphasis)
- Mono/label: JetBrains Mono, weight 500, uppercase, tracking 0.10em
- No serif anywhere (Hum disqualifier)
- Type scale anchor: `--text-display: clamp(2.5rem, 4vw + 1.2rem, 4rem)` —
  kept below the catalog's 5.25rem ceiling since headlines here are short
  functional statements ("Impara. Prova. Parla."), not landing-page drama.

## Colour
Multi-accent, OKLCH. See `tokens.css` for exact values. Area mapping (keeps
the existing mental model — grammar=green, vocabulary=amber, communication=
blue — while moving to Hum's exact hues):
- Grammatica → mint (soft green)
- Vocabolario → pear (primary yellow)
- Comunicazione → cyan (secondary)
- Coral is reserved for the one high-energy moment per page (streak/quiz-pass
  star-burst) — never a section background.

## Spacing
4-pt named scale (`--space-3xs` … `--space-4xl`), values in `tokens.css`.
Pages use named tokens only, never raw px.

## Motion
- Easings: `--ease-spring` (cards, canonical Hum bounce), `--ease-snap`
  (counters/reveals), `--ease-out` / `--ease-in-out` (fallback).
- Button system: press-down feedback (edge shadow shrinks), never scale().
- Reveal pattern: one page-load stagger on card lists only; no scroll-linked
  fade-everything.
- Counters (progress ring, quiz score) tick up once on mount.
- One star-burst micro-celebration on quiz pass. Never loops.
- Reduced-motion: springs collapse to opacity/colour only; counters render
  final value instantly; star-burst disabled.

## Microinteractions stance
- Silent success elsewhere (no toasts) — the visible state change is the
  feedback.
- Hover delay 800ms / focus delay 0ms on any tooltip-like affordance.
- Optimistic UI is out of scope here (all mutations already round-trip
  through explicit user actions with visible results).

## CTA voice
- Primary (`.primary` / `.btn--pear`): push button, pear-yellow fill, ink
  text, edge shadow, press-down active state.
- Secondary (`.secondary` / `.btn--soft`): soft flat-lift, tinted surface, no
  edge shadow.
- Copy: specific verbs, Italian throughout, matches existing wording (no
  copy invented — see [`copy.md`](../../.claude/skills/hallmark/references/copy.md)
  discipline: no rewrite of factual/product copy, only voice-neutral labels).

## Eyebrow / tag discipline
The previous build put an uppercase eyebrow above every page's H1 — the
single most common AI-templated tell. Fixed:
- Removed generic page-title eyebrows (Percorso, Progressi, Profilo,
  Contenuti da completare) — the H1 now carries the page alone.
- Kept only *meaningful* contextual tags, capped at one per screen: lesson
  category·level, quiz mode, in-preparation status, the one-time auth
  tagline. All stacked vertically above their heading — never the banned
  tag-left/heading-right two-column pattern.

## Nav / footer
App-shell nav (not a marketing nav archetype): wordmark + character mark
left, functional links right, restyled with Hum's rounded/warm voice and a
pill active-state indicator. Footer stays a single centred line
(the "compact single row" rotation Hum's variety levers name), reset in mono
label voice.

## Per-screen allowances
- All screens may use the button/card system and multi-accent bands.
- Only the Percorso and Lezione hero surfaces get a tinted accent band.
- Auth, Profilo, Progressi stay on plain cream paper — no band.

## What screens MUST share
- Wordmark + character mark.
- The three-accent palette and its area mapping.
- Plus Jakarta Sans + JetBrains Mono, no other family.
- The `.btn` system (push / soft / outline).
- 20px card radius, 999px pill radius, 12px input radius.

## Exports

### tokens.css
See [`src/tokens.css`](src/tokens.css) — the live token file the app imports.
