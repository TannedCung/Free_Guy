# Reverie Pixel Town — Design System

> Retro pixel-art skin for **Free Guy**, a fork of Stanford's *Generative Agents: Interactive Simulacra of Human Behavior* (a.k.a. "Smallville"). This design system captures the skin the maintainer wrapped around the original Django/Phaser simulator — a bright, chunky, pixel-arcade aesthetic built on Press Start 2P, flat color blocks, hard offset shadows, and a cream paper background stamped with a faint sky/sun grid.

---

## What the product is

A three-tier full-stack platform for running and observing multi-agent LLM simulations in a top-down RPG town (Smallville / "the Ville"):

| Surface | What it is | Stack |
|---|---|---|
| **Reverie Pixel Town (SPA)** | User-facing web app. Sign in, create characters, launch a simulation, observe agents live or replay a saved run. | React 19 + TypeScript + Vite + Tailwind v4 + Phaser 3 |
| **Frontend Server (API)** | REST + WebSocket/SSE layer that serves tilemap assets, streams agent state, stores simulations. | Django 4.2 + DRF + Channels + Redis |
| **Backend Server (Engine)** | The original Stanford simulation engine. CLI-driven reasoning loop over OpenAI / Ollama. | Django 2.2 (legacy) + Python |

The design system is scoped to the user-facing SPA. The in-game world itself (tile maps, character sprites, speech bubbles) is rendered by Phaser against the original research-paper art assets and isn't re-skinnable — but its palette (grass greens, pastel yellows, soft earth tones) feeds the SPA's supporting color decisions.

**In short:** the app is a hobbyist/research playground for watching a pixel town of AI agents live their lives. Tone matches: earnest, low-stakes, game-adjacent.

---

## Sources

- **Codebase** — GitHub: `TannedCung/Free_Guy` (branch `main`). Imported relevant TS/TSX under `reference/frontend/`. Key files:
  - `reference/frontend/index.css` — the full original retro-* stylesheet (source of truth for tokens)
  - `reference/frontend/App.tsx` — route map
  - `reference/frontend/pages/LandingPage.tsx`, `LoginPage.tsx`, `DashboardPage.tsx`, `CharactersPage.tsx` — canonical UI patterns
  - `reference/frontend/components/Header.tsx` — nav pattern
  - `reference/frontend/game/GameCanvas.tsx` — Phaser integration (for context only, not re-skinned here)
- **Research origin** — Park et al. 2023, *Generative Agents: Interactive Simulacra of Human Behavior* (arXiv:2304.03442).
- **Cover / key art** — `cover.png` from the repo root (imported as `assets/cover.png`). Hand-drawn pixel-art town with speech-bubble overlays; defines the in-world look.
- **Character art** — 25-agent cast from `frontend_server/static_dirs/assets/characters/`; selection imported as `assets/portraits/*.png` (32×32 facing-front headshots) and `assets/sprites/*.png` (walk-cycle sheets).
- **Font** — Press Start 2P (Google Fonts, OFL) — used throughout the SPA for headings, buttons, inputs. VT323 reserved for dense / terminal-ish content. No local TTFs needed; both fonts are CDN-loaded.
- **Substitutions flagged** — none; the original CSS specifies Press Start 2P from Google Fonts, which we use directly.

---

## Index

```
.
├── README.md                       ← you are here
├── SKILL.md                        ← Claude-Code-compatible skill manifest
├── colors_and_type.css             ← tokens: color, type, spacing, borders, shadows
├── assets/
│   ├── cover.png                   ← key art / hero image
│   ├── portraits/*.png             ← 12 agent headshots (32×32)
│   └── sprites/*.png               ← 12 agent walk-cycle sheets (~96×128)
├── preview/                        ← Design-System-tab cards
│   ├── type-*.html                 ← typography specimens
│   ├── color-*.html                ← palette + semantic color
│   ├── spacing-*.html              ← spacing / shadow / border cards
│   ├── components-*.html           ← buttons, inputs, badges, cards, steps, header
│   └── brand-*.html                ← logo, cover art, portraits
├── ui_kits/
│   └── reverie_pixel_town/
│       ├── README.md
│       ├── index.html              ← clickable multi-screen walkthrough
│       └── *.jsx                   ← Header, Panel, Button, Dashboard, Login, Observe...
└── reference/
    └── frontend/                   ← imported source from TannedCung/Free_Guy
```

---

## Content fundamentals

**Vibe.** Earnest, mildly playful, research-forward. Not ironic; not corporate. The product is a toy *and* a serious research artifact, and the copy sits right on that line — short sentences, lowercase punctuation, no exclamation-point sparkle.

**Voice.** Second person + imperative for instructions ("Sign in and create a simulation"). First person *possessive* for user's own data ("My simulations", "My characters"). Third-person neutral for system state ("Characters: 3 · Step: 128"). The product almost never says "we" or "our".

**Case.**
- **UPPERCASE** for every heading, button, nav link, badge, label, and meta text. This is load-bearing — Press Start 2P is all-caps-friendly, and the uniform case is a big part of the arcade feel.
- **Sentence case** for body paragraphs, error messages, placeholders, and dialog/chat content.
- Never title case.

**Emoji & exclamation.** Almost none. The source uses zero emoji in UI copy. Exclamation points appear exactly once or twice in empty-state encouragements ("No simulations yet. Create your first simulation!") and nowhere else. Match that restraint.

**Punctuation quirks.** Middle dot `·` separates inline meta ("Characters: 3 · Step: 128"). Em-dash fallback `—` for missing data. Ellipsis `…` (single char, not three dots) for loading ("Loading…", "Signing in…"). Straight apostrophes in code contexts, curly elsewhere.

**Example copy — landing hero**
> PIXEL-STYLE AGENT PLAYGROUND
> Follow three easy steps: create your simulation, drop characters, then watch your town come alive in a retro map view.

**Example copy — login subhead**
> Step 1: Sign in. Step 2: create simulation. Step 3: watch your pixel town.

**Example copy — empty state**
> No characters yet. Create your first character!

**Example copy — agent meta**
> Status: Available · Sim: base_the_ville_isabella_maria_klaus

**Naming.** Simulations use snake_case identifiers (`base_the_ville_isabella_maria_klaus`, `my_ville_experiment`). Characters use real human names (`Isabella Rodriguez`, `Klaus Mueller`) — inherited from the research paper. Keep those exact.

**Things NOT to do.** No "Let's get started!", no "✨ Powered by AI", no "Join thousands of researchers", no growth-loopy CTAs. This is a research toy — keep copy literal and practical.

---

## Visual foundations

### Palette

Seven named colors carry the whole system. Everything else is a `color-mix()` derivation.

| Token | Hex | Role |
|---|---|---|
| `--retro-sky` | `#77bef0` | Cool primary. Header fill, primary buttons, focus ring, step callouts. |
| `--retro-sun` | `#ffcb61` | Warm secondary. Step markers, warm buttons. |
| `--retro-orange` | `#ff894f` | Accent. Panel/card border (3px), hover-on-sun. |
| `--retro-rose` | `#ea5b6f` | Danger + link text. Logout, error, hyperlinks. |
| `--retro-paper` | `#fffdf3` | Page background — a warm cream, never white. |
| `--retro-ink` | `#2f2a3a` | Near-black with a violet undertone. All body text + borders. |
| `--retro-shadow` | `#9d4f5c` | Dusty plum — the offset drop-shadow color. |

The palette is warm-dominant. Even the cool sky blue is a soft pastel, not saturated. There is **no pure white** anywhere: surfaces are `#fffdf3` or `#fffdf7`, never `#fff`.

### Type

- **Display + UI body:** Press Start 2P (Google Fonts). 8-bit pixel font. All-caps behavior on headings/buttons. Size bias is **UP** — Press Start 2P is hard to read at small sizes, so 0.72rem is our floor for non-decorative text, 0.64rem only on badges.
- **Dense / terminal:** VT323. Used sparingly — agent dialog logs, step counters in long lists, debug-ish panels.
- **Mono fallback:** system mono (`ui-monospace`) for in-world speech bubbles (matches Phaser's default font rendering) and snake_case identifiers.

Tracking is open (0.03–0.06em) to counteract Press Start 2P's tight default spacing. Uppercase text gets more tracking (0.05–0.06em) than mixed-case (0.03–0.04em).

### Spacing

Coarse scale, pixel-grid friendly. 8px is the fundamental module (the grid backdrop is 20×20px, panel shadows offset 6px). Component padding sits in the 16–32px range; gutters in the 16–24px range. Dense UI (step items, badges) drops to 8–12px.

Scale: `0, 4, 8, 12, 16, 24, 32, 40, 48` (sp-0 … sp-8).

### Backgrounds

The page background is **not a flat color**. `body` is a layered `linear-gradient()` stack: 20×20 grid of sky-blue 15%-opacity vertical hairlines + sun-yellow 20%-opacity horizontal hairlines, all laid over `--retro-paper`. The effect reads like graph paper or a tiled town map — subtle but iconic to this skin. It is fixed (`background-attachment: fixed`) so it doesn't scroll with content.

No full-bleed photography. No hero video. Imagery is **pixel art only**: the cover key art, portrait sprites, and in-game Phaser tilemap. When the SPA needs "imagery," it shows these — never stock photos, never illustrations drawn in another style, never gradients masquerading as imagery.

### Animation

Minimal. The original codebase has essentially no CSS transitions on hover/focus — colors swap instantly, which reinforces the 8-bit flat feel. Motion lives inside the Phaser canvas (walk cycles at 4fps, camera panning) and in timing-based UI states (loading ellipses, SSE/WebSocket updates to the agent list). When you add motion, keep it:

- **Instant state swaps** for hover/press — no `transition: background 200ms` sugar.
- **Step-like easing** if you must ease — avoid smooth `ease-out`, prefer `steps(4, end)` or low-framerate CSS keyframes that feel chunky.
- **Fade-in only where data arrives** — e.g. toast-style invitation count badge, brief.

Never fancy (no scroll-reveals, no parallax, no spring physics). The product's dynamism is the simulation itself, not the chrome.

### Hover / press states

- **Buttons** — background color swaps to the next-darker sibling (sky → sky-dark, sun → orange, rose → rose-dark). No opacity change, no scale, no shadow lift.
- **Nav links** (`.retro-navlink`) — background flips from sun-yellow to orange. Text color holds.
- **Links** (`.retro-link`) — color shifts from rose to deeper rose-orange (`#b94053`).
- **Disabled** — `opacity: 0.5; cursor: not-allowed;`. Underlying color stays.
- **Focus** — `outline: 3px solid var(--retro-sky); outline-offset: 1px;` on inputs. Never a soft ring-shadow.
- **Press** — not styled separately. Hover styling persists through click.

### Borders

Chunky and ever-present. The system uses three border weights, no more:

- **2px solid ink** — inputs, buttons, badges, nav links. Makes everything feel like a sticker.
- **3px solid orange** — panels / cards. The orange frame is the single strongest brand signal.
- **3px solid sky** — step callouts. Sky variant instead of orange when the component is instructional rather than containing data.
- **2px dashed sky** — empty states. The only dashed border in the system.
- **4px bottom-only orange** — site header (plus 6px ink-shadow underneath).

### Shadows

Hard offset blocks, never blurred. This is the single most load-bearing visual motif after the pixel font.

- Panels: `6px 6px 0 #9d4f5c` (dusty plum).
- Small cards / compact variants: `4px 4px 0 #9d4f5c`.
- Header: `0 6px 0 #9d4f5c` (bottom-only).
- Tailwind `shadow` overrides: `5px 5px 0 rgb(159 77 95 / 65%)` (slightly softer so legacy classes don't overpower).

Never `filter: drop-shadow`, never `blur`. If you need an inner shadow, you're doing it wrong — this system doesn't use them.

### Transparency & blur

Essentially none. The only transparency in play is the body-grid wash (15–20% alpha on the sky/sun hairlines) and the semi-transparent in-game speech-bubble fill (`#ffffffcc` in GameCanvas). No frosted-glass panels, no backdrop-filter, no translucent overlays. Every surface is opaque.

### Corner radii

`0` for every UI element. The CSS explicitly overrides Tailwind's `rounded`, `rounded-lg`, `rounded-xl` to `0 !important`. Hard edges everywhere — inputs, buttons, cards, badges, images. The only "round" thing in the entire product is the pixel-art character heads inside the Phaser canvas, and those are raster, not CSS.

### Cards

A card = `.surface-panel`:

- Cream fill (`#fffdf7`, half-a-shade warmer than the body paper).
- 3px orange border.
- 6px/6px dusty-plum offset shadow.
- 0 radius.
- Padding: `1.25rem`–`2rem` depending on density.
- Inside, uppercase H3 title → optional caption → body content → link-text actions at the bottom-left.

Cards never nest more than one deep. A card inside a card is fine; a card inside a card inside a card is cramped and visually noisy — use a bare `<div>` with padding instead.

### Layout rules

- Central `.retro-main` column, `max-width: 76rem` (~1216px), `padding: 2rem 1rem 2.5rem`. No fluid-width layouts.
- Header spans 100% width, content centered inside another 76rem inner wrapper.
- Grid gaps: `1rem` (16px) for dense card grids, `1.5rem` (24px) for section-to-section spacing.
- Mobile: Tailwind responsive (`grid-cols-1 md:grid-cols-2 lg:grid-cols-3`). Nav collapses to wrap, not a hamburger.
- No fixed/sticky elements. Header is standard flow. The only "fixed" thing is the grid body background (`background-attachment: fixed`).

### Imagery tone

- **Pixel art only.** Cover key art has a warm, sunlit, saturated-but-not-garish palette — pastel grass green, yellow-tan paths, terracotta roofs, cream house walls. Matches the UI palette by being warm-dominant with cool accents.
- **Speech bubbles** (from cover art) are pure white-fill + black 2–3px outline + black drop shadow + initials-in-box avatar. Use this motif if you need to indicate "an agent is saying something" outside the Phaser canvas.
- **Portraits** are 32×32 front-facing headshots — tiny, chunky, monocolor-dominant (hair color is often the most saturated thing). Display them pixelated (`image-rendering: pixelated`) and at integer scale (32px, 64px, 96px).
- **No photography. No non-pixel illustrations.** If you need a placeholder, use a flat color block with a 2px ink border and uppercase label text.

---

## Iconography

**The app's own approach:** the reference codebase uses **essentially no decorative icons.** Chunky 8-bit text does all the labelling. The only icons in the entire frontend are two logo marks — Google's 4-color "G" and GitHub's Octocat — used exclusively on the login-page "Continue with…" OAuth buttons. Both are inline multi-path SVGs sized `w-5 h-5` (20×20), with the brand's own colors (`#4285F4`, `#34A853`, `#FBBC05`, `#EA4335` for Google; `currentColor` for GitHub).

**This is deliberate.** The system leans on typography, color, and hard-edged borders for affordance. A "delete" action says "Delete" in uppercase red text, not a trash-can icon. Navigation tabs say "Dashboard", "Explore", "Invites" — no home icon, no compass, no inbox.

**Rules for adding new icons**

1. **Prefer text labels.** If the label fits, don't add an icon.
2. **When you must use an icon** (e.g. external brand marks like OAuth, or dense toolbar chrome where text is infeasible), match the existing OAuth-logo treatment: inline SVG, 20×20, monochrome or brand colors, no stroke-weight variation, no rounded caps.
3. **Emoji: never.** The codebase has zero emoji. Do not introduce any.
4. **Unicode characters as icons: yes, a few specific ones.**
   - `·` middle dot for inline meta separators
   - `—` em-dash for missing data
   - `…` ellipsis for loading
   - `×` multiplication sign for close buttons (when absolutely needed)
   - `↑ ↓ ← →` arrows *never in UI* — they live inside the Phaser canvas for camera controls only
5. **Pixel-art sprites as iconography.** The character portraits (`assets/portraits/*.png`) *are* the product's iconography for the "character" concept. A character card is best illustrated by its sprite, not a generic user icon. Use `image-rendering: pixelated` and integer scale (2×, 3×, or 4×).
6. **Substitute set, if you really need a utility icon library:** use **Lucide** via CDN (`https://unpkg.com/lucide@latest`), constrained to the thin stroke (default 2px) style and `var(--fg-1)` stroke color. **Flag the substitution** to the user — nothing in the original codebase ships Lucide, so its presence is a design-system extension, not a reproduction.

**Icon assets included here**

- `assets/portraits/*.png` — 12 hand-picked character headshots. Use these as the canonical "character" icon.
- The Google + GitHub SVGs live inline in `reference/frontend/pages/LoginPage.tsx` (lines 77–90). Copy them verbatim from there when recreating the OAuth pattern; do not redraw.

No custom icon font, no sprite sheet, no Heroicons / Font Awesome / Phosphor. The system's restraint on iconography is a feature, not a gap.

---

## Caveats

- **Phaser game canvas is out of scope.** The in-game top-down RPG (tilemaps, walk cycles, collisions) is fully governed by `GameCanvas.tsx` and the original research-paper art assets. The UI kit here covers only the React SPA chrome *around* the canvas — we don't re-skin tilemap tiles.
- **No local font TTFs.** Press Start 2P and VT323 are both pulled from Google Fonts via `@import url(...)` at the top of `colors_and_type.css`. If you need offline/self-hosted fonts, download OFL copies from [Google Fonts](https://fonts.google.com/) and swap the `@import`.
- **Only 12 of 25 agent portraits/sprites** are imported (cast covers the base-3 + key named agents from the README). Import more from `TannedCung/Free_Guy → frontend_server/static_dirs/assets/characters/` if a design needs the full roster.
- **No product logo exists** in the codebase. The brand mark is text-only: "REVERIE PIXEL TOWN" set in Press Start 2P, all-caps, letterspaced ~0.06em, on the sky-blue header. If a logo-mark is ever needed (favicon, app icon), design one against this system — don't reuse the vite.svg placeholder that shipped with the repo.
