# Reverie Pixel Town — UI kit

Clickable multi-screen walkthrough of the React SPA. Flip through: landing → login → dashboard → characters → observe.

## Files

- `index.html` — entry; routes between screens via local state
- `Primitives.jsx` — `Button`, `NavLink`, `Panel`, `Input`, `StatusBadge`, `EmptyState`, `Link`
- `Header.jsx` — top bar with brand wordmark + nav + invite count
- `LandingPage.jsx` — public hero with 3-step callout + quick tester
- `LoginPage.jsx` — sign-in form + Google/GitHub OAuth rows
- `DashboardPage.jsx` — My simulations + My characters grids
- `CharactersPage.jsx` — detailed character cards with portrait
- `ObservePage.jsx` — live simulation view: cover art stands in for the Phaser map canvas, plus agent list + dialog log

## What it copies vs. what it stands in for

- **Copies exactly:** palette, borders, shadows, typography scale, button variants, card layouts, status pill colors, nav pattern, empty-state treatment, form styling, step-callout component. Imported directly from `reference/frontend/pages/*`.
- **Stands in:** the live Phaser canvas on the Observe screen is replaced with the repo's `cover.png` key art. The real app uses Phaser 3 to render a tilemap; re-skinning the game world is out of scope here.
- **Omitted:** Create Character form, Settings, Invites detail, Register form (shares the Login treatment). Easy to extend using the same primitives.

## How to add a new screen

1. Write `MyPage.jsx`, use the primitives in `Primitives.jsx`, end with `Object.assign(window, { MyPage })`.
2. Add `<script type="text/babel" src="MyPage.jsx"></script>` to `index.html`.
3. Add a route arm: `{route === '/my' && <MyPage ... />}`.
