# Improve the ClinicalBench Frontend UI

You are a UI engineer working on the ClinicalBench React frontend (`frontend/src/`). The app is a dark-themed, two-column dashboard for watching an AI agent solve clinical benchmark tasks in real time.

## Design system

| Token | Value |
|---|---|
| Accent / primary | `#0492bd` |
| Dark background | `#06252e` |
| Panel surface | `rgba(4, 14, 20, 0.88)` |
| Code surface | `rgba(2, 10, 14, 0.96)` |
| Body font | `"Ppneuemontreal Book", Arial, sans-serif` |
| UI font (labels, buttons, headings) | `Gilroy, Arial, sans-serif` |
| Border (default) | `1px solid rgba(4, 146, 189, 0.2)` |
| Border (active/focused) | `1px solid #0492bd` |

All new components must stay within this palette. Do **not** introduce new color values unless the user explicitly asks.

## Key files

- `frontend/src/App.jsx` — all React state and JSX
- `frontend/src/styles.css` — all CSS (no CSS-in-JS, no Tailwind)
- `frontend/index.html` — HTML shell (Gilroy and Ppneuemontreal loaded here via `<link>`)
- `frontend/package.json` — only React + Vite, no UI library

## How to use this skill

Run `/ui <description of what to change or add>` and Claude will:

1. Read the current `App.jsx` and `styles.css`.
2. Plan the minimal JSX + CSS changes needed.
3. Apply the edits, keeping the existing class naming convention (`camelCase` BEM-lite: `.panelHeader`, `.taskCard`, `.rewardValue`).
4. Verify no new dependencies are required (prefer native HTML/CSS).

## Common UI tasks

### Add a new stat card
Add a `<div className="statCard">` inside `.statGrid` in `App.jsx` and expose the value from state. No CSS change needed — the grid handles layout automatically.

### Add a loading skeleton
Replace an empty `<pre>` or `<div>` with a `<div className="skeleton" />` while `loading` is true. Add to `styles.css`:
```css
.skeleton {
  background: linear-gradient(90deg, rgba(4,146,189,0.08) 25%, rgba(4,146,189,0.18) 50%, rgba(4,146,189,0.08) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.4s infinite;
  border-radius: 4px;
  min-height: 1rem;
}
@keyframes shimmer { to { background-position: -200% 0; } }
```

### Add a new panel
Use the existing `.panel` + `.panelHeader` structure:
```jsx
<article className="panel myPanel">
  <div className="panelHeader">
    <h2>Panel Title</h2>
    <p>Subtitle</p>
  </div>
  {/* content */}
</article>
```
Add a specific height or `flex: 1` rule in CSS if needed.

### Add a reward sparkline / mini chart
Use an inline SVG `<polyline>` — no chart library needed. Map `steps` to x/y coordinates within a fixed viewBox.

### Animate a status pill
Add `transition: background 0.2s, border-color 0.2s` to `.statusPill` and toggle a class via state.

### Add a collapsible section
Use the native `<details>` / `<summary>` HTML elements styled with the panel border/background.

## Quality checklist before finishing

- [ ] No new npm packages added
- [ ] All new CSS classes are camelCase BEM-lite and in `styles.css`
- [ ] Dark background (#06252e) is preserved everywhere
- [ ] Accent color is only `#0492bd` (or its rgba derivatives)
- [ ] Responsive: new elements stack correctly on narrow screens (test via `.mainGrid` media query at 860 px)
- [ ] Disabled states respected on all new buttons
- [ ] No inline styles added to JSX (keep everything in `styles.css`)

## Usage

```
/ui add a sparkline chart showing reward over steps
/ui add skeleton loaders while the episode is starting
/ui show a final score summary card when the episode is done
/ui make the task cards animate in on first render
```
