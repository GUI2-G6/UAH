# UAH theming: tokens, appearance modes, and theme packs

## Appearance modes (today)

- **User preference** is stored in the browser as `localStorage` key `uah-theme-preference` with values: `light`, `dark`, or `system` (use OS `prefers-color-scheme` when set to `system` or when nothing is stored yet).
- **Resolved display mode** is applied as `document.documentElement.dataset.theme` with values **`light`** or **`dark`** only (never `system`), so all CSS is written against a concrete light or dark context.
- Implementation: [`../js/themePreference.js`](../js/themePreference.js). Inline boot scripts in the main app and landing `index.html` set `data-theme` before the first paint to limit flash of the wrong mode.

## Built-in theme packs (today)

A **theme pack** is a coordinated set of design tokens. The repository currently ships a single first-party pack, **`default`**, in two **modes**:

| Pack / mode | Primary source |
| --- | --- |
| `default` / `light` | [`uah-theme.css`](uah-theme.css) on `:root` |
| `default` / `dark` | [`uah-theme.css`](uah-theme.css) on `html[data-theme="dark"]` |

The **marketing (landing) site** adds extra tokens in [`../../landing/src/assets/styles/base.css`](../../landing/src/assets/styles/base.css) and section-level dark overrides in [`../../landing/src/assets/styles/sections-theme-dark.css`](../../landing/src/assets/styles/sections-theme-dark.css) so long-form marketing layouts stay legible in dark mode.

**Shell controls:** Segmented “Auto / Light / Dark” control styles live in [`theme-mode-control.css`](theme-mode-control.css).

## Variable contract (apps should use these)

Prefer **semantic** variables in components instead of ad hoc hex values:

- **Text:** `--color-text-primary`, `--color-text-secondary`, `--color-text-muted`
- **Surfaces:** `--color-surface`, `--color-surface-muted`, `--color-surface-hover` (and landing-only `--color-surface`, `--color-text` in `base.css` where the stack differs)
- **Brand:** `--color-primary-500` / `--600` / `--700` (main app); landing often uses `--color-primary` and `--color-primary-deep`
- **Borders and elevation:** `--border-color`, `--border-color-light`, `--shadow-card`, `--app-page-background`
- **App sidebar (Burger):** `--nav-sidebar-bg`, `--nav-sidebar-border`, `--nav-sidebar-hover`, `--nav-sidebar-label`, `--nav-sidebar-bar` (defined in the main app `App.css` with light/dark values)

## Custom theme packs (roadmap, not implemented)

**Goal:** Let users (or operators) load an extra token layer while keeping **accessibility and contrast** guarantees.

**Possible directions (choose later):**

- `data-theme-pack="<id>"` on `<html>`, with optional CSS file or `@layer` bundle registered by id.
- Client-only JSON or CSS import stored in `localStorage` (with file size and validation limits).
- Server-backed saved preferences once account-level settings exist.
- Contrast checking (manual checklist or automated) before a pack is accepted.

Until then, all UI should stay on the **`default` pack** and only switch **light / dark** via the preference API above.

## Related files

- Main app import: `frontend/src/App.css` imports `uah-theme.css` and `theme-mode-control.css`
- Landing import: `landing/src/main.js` imports `base.css`, `theme-mode-control.css`, `sections.css`, `sections-theme-dark.css`
- `THEME_STORAGE_KEY` and helpers: `shared/js/themePreference.js`
