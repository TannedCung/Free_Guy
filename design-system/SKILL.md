---
name: reverie-pixel-town-design
description: Use this skill to generate well-branded interfaces and assets for Reverie Pixel Town, either for production or throwaway prototypes/mocks/etc. Contains essential design guidelines, colors, type, fonts, assets, and UI kit components for prototyping.
user-invocable: true
---

Read the README.md file within this skill, and explore the other available files.

If creating visual artifacts (slides, mocks, throwaway prototypes, etc), copy assets out and create static HTML files for the user to view. If working on production code, you can copy assets and read the rules here to become an expert in designing with this brand.

If the user invokes this skill without any other guidance, ask them what they want to build or design, ask some questions, and act as an expert designer who outputs HTML artifacts _or_ production code, depending on the need.

## Quick orientation

- `README.md` — full context: product, tone, visual foundations, iconography
- `colors_and_type.css` — drop-in tokens (CSS vars for color, type, spacing, borders, shadows, plus semantic classes `.t-h1`…`.t-dense`, `.surface-panel`, etc.)
- `assets/` — cover key art, 12 character portraits (32×32), 12 sprite sheets
- `preview/` — design-system spec cards
- `ui_kits/reverie_pixel_town/` — React (Babel/JSX) recreation of the SPA; crib from `Primitives.jsx` for buttons, panels, inputs, badges
- `reference/frontend/` — imported source from TannedCung/Free_Guy (original TSX + index.css)

## Non-negotiables

- Press Start 2P for all headings/UI (VT323 for dense log-style content)
- Everything uppercase with 0.03–0.06em tracking
- 0 border-radius; 2px or 3px hard borders; `Npx Npx 0 #9d4f5c` offset shadows (never blurred)
- Cream paper background (`#fffdf3`) with 20×20 sky+sun grid wash, never pure white
- No emoji, no decorative icons, no gradients, no scroll animations
