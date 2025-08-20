# 🌊 Windsurf UI Standards

This document defines UI/UX standards for Windsurf applications.  
It draws on **OSS community guidelines**, **Material Design**, and other modern UI best practices to ensure **clarity, consistency, and usability**.

---

## 1. Core Principles
- **Clarity**: UI should communicate intent without extra explanation.  
- **Consistency**: Shared design patterns across all views.  
- **Efficiency**: Minimize clicks, maximize discoverability.  
- **Accessibility**: All designs must meet **WCAG 2.1 AA** standards.  
- **Simplicity**: Remove unnecessary decoration; focus on function.  

---

## 2. Layout & Structure
- Use a **grid-based layout** (8px baseline grid recommended).  
- Keep **consistent spacing** between elements (multiples of 4px or 8px).  
- Apply **progressive disclosure**: show primary actions first, advanced settings later.  
- Ensure **responsive design** (desktop, tablet, mobile).  

---

## 3. Typography
- **Font**: Use a clean, legible sans-serif (e.g., Inter, Roboto, or system defaults).  
- **Hierarchy**:
  - H1: 24–32px, bold  
  - H2: 20–24px, semi-bold  
  - Body: 14–16px, regular  
- **Line height**: 1.4–1.6 for readability.  
- **Contrast**: Follow **WCAG AAA** contrast ratios for text on background.  
 - **Scalable text (required)**: All type must scale with user preferences (zoom / accessibility font size).  
   - Use relative units (rem/em/%), not hard-coded pixel sizes.  
   - Respect OS-level text scaling and app-level zoom controls.  
   - Provide an in-app font-size control with at least Small / Default / Large / Extra-Large presets (persisted per user).  
   - Ensure layouts reflow gracefully at 125%–200% scaling without truncation or overlap.  

---

## 4. Color & Theming
- **Primary color**: Chosen to represent Windsurf branding.  
- **Secondary color**: Used sparingly for accents or highlights.  
- **Neutral palette**: Grays for backgrounds, dividers, inactive states.  
- **Semantic colors**:
  - Success: Green (#28A745)  
  - Warning: Amber (#FFC107)  
  - Error: Red (#DC3545)  
  - Info: Blue (#17A2B8)  
- **Dark mode**: Provide light & dark themes. Ensure consistency in contrast.  

---

## 5. Components
### Buttons
- Primary button: filled, high-contrast.  
- Secondary button: outlined or subtle background.  
- Destructive button: red background, confirmation required.  

### Forms
- Inputs have clear labels, left-aligned.  
- Placeholder text **not a replacement** for labels.  
- Show validation feedback inline (e.g., ✅ / ❌).  

### Navigation
- Use a **top-level navigation bar** or sidebar with clear section grouping.  
- Provide **breadcrumbs** for deep navigation.  
- Keep **search globally accessible**.  

### Modals & Dialogs
- Use modals sparingly.  
- Always provide **clear exit options** (cancel, X).  
- Confirm destructive actions with **double confirmation** if irreversible.  

---

## 6. Accessibility Standards
- Follow **WCAG 2.1 AA**:
  - All interactive elements must be keyboard-accessible.  
  - Provide ARIA labels for screen readers.  
  - Maintain sufficient text/background contrast.  
- Avoid **color-only indicators**; use icons or text as well.  
- Ensure **focus states** are visible and distinct.  
 - Text scaling: verify that all text and key UI components remain usable at OS/app scaling levels up to 200%.  

---

## 7. Localization
- All **UI text must be soft-coded** to allow for localization.  
- Do not hardcode strings inside components or business logic.  
- Use a **resource file or i18n framework** (e.g., JSON, YAML, gettext, or industry-standard i18n libraries).  
- Best Practices:
  - Keep keys descriptive (e.g., `button.save_changes`).  
  - Avoid concatenating localized strings in code; use templates with placeholders.  
  - Provide context for translators when needed.  
  - Ensure fallback language support.  

---

## 8. Motion & Feedback
- Animations should be **subtle and purposeful**, not distracting.  
- Provide **instant feedback** for actions (button press, form submit).  
- Use **loading indicators** for delays > 300ms.  

---

## 9. Writing Style (UX Copy)
- **Concise, plain language**.  
- Avoid jargon unless domain-specific.  
- Use **sentence case** for UI text (e.g., "Settings", not "SETTINGS").  
- Prefer **action-oriented labels** (“Save Changes” > “Submit”).  

---

## 10. Example References
- [Material Design Guidelines](https://m3.material.io/)  
- [Human Interface Guidelines](https://developer.apple.com/design/human-interface-guidelines/)  
- [OSS Design Principles](https://opensource.design/)  
- [WCAG 2.1 Accessibility](https://www.w3.org/TR/WCAG21/)  

---

## 11. Governance
- All new UI components must be reviewed against this standard.  
- Proposals for exceptions must include reasoning and alternative solutions.  
- Maintain a **UI component library** to enforce consistency.  

---

✅ Following these standards ensures Windsurf maintains a **modern, clean, and highly usable UI** that balances **developer efficiency, user delight, accessibility, and localization readiness**.
