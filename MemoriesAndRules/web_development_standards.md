# Web Development Standards

These standards guide web UI work for AI Typing Trainer. They emphasize clean, modern, responsive design, AWS deployability, accessibility, and alignment with our Clean Architecture ethos.

## Principles
- Favor simple, readable code; keep components focused and composable.
- Prefer TypeScript + React with MUI for consistent theming and accessibility.
- Keep dependencies lean; avoid heavy UI kits beyond MUI unless justified.
- Treat UI as an adapter layer: no business logic in components.
- Enforce accessibility: semantic elements, ARIA where needed, focus states, keyboard navigation.

## Layout & Responsiveness
- Use responsive grids/flex; avoid fixed widths. Target mobile, tablet, desktop.
- Maintain a max content width (e.g., 1280px) with comfortable padding (16–24px).
- Provide sensible spacing scale (4/8/12/16/24) and consistent line heights.
- Use list-first layouts for data management screens (as in Keysets spec): left list, right details.

## Theming & Appearance
- Support light and dark modes; expose a toggle in the app shell.
- Define primary/secondary colors and neutrals; avoid arbitrary per-component colors.
- Typography: base font size scalable; allow user-controlled text-size step (e.g., 0, +2, +4 px).
- Avoid gradients/noise unless purposeful; keep contrast WCAG AA or better.

## Accessibility
- Ensure focus outlines are visible; no outline removal without replacement.
- Provide keyboard navigation for interactive elements; respect tab order.
- Use aria-label/aria-describedby for icon-only controls.
- Ensure color is not the only carrier of meaning.

## State & Data
- Keep state lifting minimal; prefer hooks and context for cross-cutting concerns (theme, text size, auth).
- No business rules in the UI; call use-case/adapters.
- Handle loading/error/empty states explicitly (spinners, banners, placeholders).

## Performance
- Code-split routes as they grow; defer heavy bundles.
- Avoid unnecessary re-renders (memoize where warranted, but favor clarity first).
- Optimize images/assets; use SVG for icons.

## Testing & Quality
- Lint: `ruff` for backend, `eslint`/`prettier` for frontend (when present).
- Type check TS/TSX; keep strict where feasible.
- Add component tests for critical flows; snapshot only for stable UI shells.

## AWS Hosting Notes
- Build as static assets (React) suitable for S3 + CloudFront; avoid server affinity.
- Keep environment configuration injectable via build-time env or runtime config JSON.
- Avoid hard-coding origins; allow env-based API roots.

## Key UX Defaults for AI Typing Trainer
- Provide a top-level light/dark toggle and text-size control in the shell.
- Use MUI containers with responsive breakpoints; prefer `Container maxWidth="xl"`.
- Buttons: medium/large hit targets (min height 40px), clear labels, disabled states evident.
- Tables/lists: striped/hover states optional but maintain contrast; show empty-state messaging.
- Forms: label every input; show inline validation messages; avoid silent failures.

## Delivery Checklist
- Light/dark mode toggle present and working.
- Text-size control present and working (applies globally to body/base typography).
- Responsive at 360px, 768px, 1024px, 1280px widths.
- No console errors/warnings in dev tools.
- Deployed bundle is static and cacheable; supports AWS S3 + CloudFront.
