---
name: JobDevs
description: Verified SENA talent, traceable delivery. A light corporate dashboard with a black-and-neon tech twin.
colors:
  brand: "#00713f"
  brand-hover: "#00693a"
  brand-light: "#e6faf0"
  brand-neon: "#00e676"
  brand-neon-bright: "#69f0ae"
  brand-neon-dim: "#00c853"
  surface: "#ffffff"
  surface-alt: "#f7f8f7"
  border: "#e4e7e5"
  border-subtle: "#f0f2f0"
  ink-900: "#0b0f0c"
  ink-800: "#1a221d"
  ink-700: "#2d3830"
  ink-600: "#4b5563"
  ink-500: "#5f6673"
  ink-400: "#8d9890"
  ink-100: "#f1f4f2"
  oled-bg: "#000000"
  oled-card: "#0a0a0a"
  oled-border: "#1a1a1a"
  oled-fg-dim: "#a0a0a0"
  warning: "#d97706"
  warning-light: "#fffbeb"
  danger: "#dc2626"
  danger-light: "#fef2f2"
  info: "#0284c7"
  info-light: "#f0f9ff"
  gold: "#f59e0b"
typography:
  display:
    fontFamily: "'Inter Tight', -apple-system, BlinkMacSystemFont, sans-serif"
    fontSize: "clamp(2rem, 4vw, 3.5rem)"
    fontWeight: 700
    lineHeight: 1.1
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "24px"
    fontWeight: 700
    lineHeight: 1.3
  title:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "18px"
    fontWeight: 700
    lineHeight: 1.4
  card-title:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.4
  body-lg:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 600
    lineHeight: 1.3
  caption:
    fontFamily: "'Space Grotesk', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.4
  label:
    fontFamily: "'JetBrains Mono', monospace"
    fontSize: "0.7rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "0.1em"
rounded:
  xs: "4px"
  sm: "6px"
  md: "10px"
  lg: "14px"
  xl: "18px"
  dev: "8px"
  pill: "999px"
components:
  button-primary:
    backgroundColor: "{colors.brand}"
    textColor: "{colors.surface}"
    typography: "{typography.body}"
    rounded: "{rounded.md}"
    padding: "8px 16px"
  button-primary-hover:
    backgroundColor: "{colors.brand-neon}"
    textColor: "{colors.oled-bg}"
  card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-700}"
    rounded: "{rounded.lg}"
    padding: "20px"
  badge-success:
    backgroundColor: "{colors.brand-light}"
    textColor: "{colors.brand}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  badge-danger:
    backgroundColor: "{colors.danger-light}"
    textColor: "{colors.danger}"
    rounded: "{rounded.sm}"
    padding: "2px 8px"
  theme-toggle:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.ink-900}"
    typography: "{typography.label}"
    rounded: "0px"
    height: "38px"
---

# Design System: JobDevs

## Overview

**Creative North Star: "The Audit Ledger"**

JobDevs looks like a ledger that someone actually reconciled: white pages, hairline rules, dense but calm rows, and numbers in a deliberate typeface. Every status, hito and contract is a line of evidence, so the interface favors precision over decoration. The signature green is a signal, not a wash.

The system has two faces of one identity. The Empresa dashboard, the primary surface, is pure white with slate ink and a deep institutional green. The public landing and the Desarrollador and Administrador areas wear the twin: OLED black, `#0a0a0a` cards, `#1a1a1a` rules and neon green `#00e676`. The theme switches with `[data-theme="dark"]` on `<html>`, and both faces share token names and component shapes.

Technical texture comes from monospace uppercase micro-labels and square-cornered controls (the theme toggle is deliberately `border-radius: 0`). Everything else is softly rounded.

**Key Characteristics:**
- Light-first for Empresa; dark is a first-class twin, not an afterthought.
- Flat at rest: structure comes from 1px borders, not shadows.
- Neon green is rare and meaningful; the accessible deep green carries text and fills on white.
- Three typefaces with strict jobs: Space Grotesk body, Inter Tight display, JetBrains Mono labels.
- Spanish (Colombia) is the primary locale; English (`/en/`) must match it, so layouts tolerate longer strings.

## Colors

A near-neutral slate-and-white field with a single green accent, plus semantic amber, red and blue for state.

### Primary
- **Institutional Green** (#00713f): Primary buttons, links, active nav, success text. Passes AA on white (6.1:1).
- **Ledger Mint** (#e6faf0): Tinted background for success badges and active indicators.
- **Signal Neon** (#00e676): Brand accent on dark surfaces, hover fill on primary buttons, glows. On white it appears only as a hover fill with black text, never as text.

### Secondary
- **Neon Bright** (#69f0ae) and **Neon Dim** (#00c853): Hover and pressed neighbors of the neon accent in the dark twin.

### Neutral
- **Page White** (#ffffff) and **Paper Mist** (#f7f8f7): Page and card surface, and alternate band for tables and row hover.
- **Hairline** (#e4e7e5) and **Hairline Faint** (#f0f2f0): Card, input and divider borders; row separators.
- **Ink 900 to 400** (#0b0f0c, #1a221d, #2d3830, #4b5563, #5f6673, #8d9890): Titles, section heads, body, secondary text, metadata, placeholders (400 is disabled-only).
- **OLED Black** (#000000), **Card Black** (#0a0a0a), **Rule Black** (#1a1a1a), **Dim Gray** (#a0a0a0): The dark twin's page, card, border and secondary text.

### Semantic
- **Amber** (#d97706 on #fffbeb): action required, due soon.
- **Red** (#dc2626 on #fef2f2): errors, disputes, cancellations.
- **Sky** (#0284c7 on #f0f9ff): informational guidance.
- **Reputation Gold** (#f59e0b): stars and reputation badges only.

### Named Rules
**The Signal Rule.** Neon green marks live state and the single primary action. If a screen has more than a few neon moments, none of them is a signal.

**The Two-Greens Rule.** On white, use Institutional Green (#00713f) for text and fills. Neon on white fails contrast; it exists only as a hover fill paired with black text.

## Typography

**Display Font:** Inter Tight (with system sans fallback)
**Body Font:** Space Grotesk (with system sans fallback)
**Label/Mono Font:** JetBrains Mono

**Character:** A geometric grotesk for reading and a tight display face for big moments, with monospace as the ledger's stamp on metadata and controls.

### Hierarchy
- **Display** (700, clamp(2rem, 4vw, 3.5rem), 1.1, -0.02em, uppercase on landing): Landing section titles only.
- **Headline** (700, 24px, 1.3): Dashboard page titles.
- **Title** (700, 18px, 1.4): Section titles; card headings run 15px at 600.
- **Body** (400, 14px, 1.5): Default text in dashboards; cap prose near 65-75ch.
- **Caption** (400, 12px, 1.4): Metadata, dates, badges. This is the type floor; nothing in Empresa goes below 12px.
- **Label** (500, 0.7rem, 0.1em tracking, uppercase, mono): Kickers, toggles, micro-metadata. Badges run 12px at 500.

### Named Rules
**The Mono Stamp Rule.** Monospace is for metadata, kickers and controls, never for paragraphs.

**Signature Exception.** `"Segoe Script"` (with cursive fallback) is used solely for simulated handwritten signatures on digital contracts (`.contract-signature-script`), never for UI copy.

## Layout

Fixed sidebar (250px) with a 64px topbar in the Desarrollador and Administrador shells; Empresa uses the same sidebar-and-content pattern. Content sits on a KPI grid of cards followed by tables and lists, with 14px-radius cards as the containment unit. Rhythm is compact: 8, 16 and 20px steps dominate. Responsive breakpoints in use are 640, 768, 900, 1024 and 1080px; below 1024px the sidebar collapses and grids stack. Spanish and English strings must both fit without truncating status text.

## Elevation & Depth

Hybrid, flat-leaning. Surfaces are flat at rest; 1px hairlines carry structure. Shadows appear on hover, popovers and modals.

### Shadow Vocabulary
- **xs** (`0 1px 2px rgba(11,15,12,0.04)`): Resting small elements.
- **sm** (`0 1px 3px rgba(11,15,12,0.08), 0 1px 2px rgba(11,15,12,0.04)`): Cards on hover.
- **md** (`0 4px 8px -2px rgba(11,15,12,0.08)`): Dropdowns.
- **lg** (`0 10px 18px -4px rgba(11,15,12,0.10)`): Raised panels.
- **pop** (`0 20px 25px -5px rgba(11,15,12,0.12), 0 8px 10px -6px rgba(11,15,12,0.06)`): Modals and popovers.
- **Neon glow** (`0 4px 12px rgba(0,230,118,0.4)`): Primary button hover; in the dark twin, shadows are near-black and the developer area adds a faint green wash.

### Named Rules
**The Flat-By-Default Rule.** Cards at rest have a border and no shadow. Shadow is a response to hover, overlay or focus.

## Shapes

Soft rounded rectangles with a size ladder: 6px for tags and small buttons, 10px for inputs and standard buttons, 14px for cards and panels, 18px for modals, and 999px for pills and avatars. The Desarrollador area uses 8px and 6px. The one square-cornered exception is the technical theme toggle (0px radius), a deliberate nod to the landing's brutalist switch.

## Components

### Buttons
- **Shape:** 10px radius, 8px 16px padding, 13px at 600.
- **Primary:** Institutional Green fill, white text, 1px green border, with a small green shadow.
- **Hover / Focus:** Fills Signal Neon with black text, lifts 1px and gains a neon glow; active returns to rest. Transition 0.15s ease. Focus rings are 2px green with 2px offset (as on the theme toggle).
- **Danger:** Red variant (`.btn-corp-danger`) for destructive actions.

### Cards / KPI
- **Corner Style:** 14px.
- **Background:** White (light) or `#0a0a0a` (dark).
- **Border:** 1px hairline.
- **Internal Padding:** about 20px.

### Badges
- **Style:** 6px radius, tinted semantic background with matching text, 12px at 500.

### Navigation
- Sidebar on white with hairline divider and `#f1f4f2` hover (black with `#0a0a0a` hover in dark). Active item uses the green tint.

### Theme Toggle (signature)
- Square 38px-tall control with moon and sun icons always visible, mono uppercase label, translucent blurred background in dark, full inversion on hover.

## Do's and Don'ts

### Do:
- **Do** use `var(--corp-*)` tokens in Empresa and the shared `--accent*` aliases elsewhere; keep light and dark token names identical.
- **Do** use Institutional Green (#00713f) for text and fills on white.
- **Do** keep status colors paired with a label or icon so state is not color-only (WCAG 2.1 AA).
- **Do** keep both `es` and `en` strings in new UI.

### Don't:
- **Don't** put neon (#00e676) text on white; it fails contrast.
- **Don't** add shadows to cards at rest.
- **Don't** use monospace for body paragraphs.
- **Don't** use Reputation Gold for anything other than ratings.
- **Don't** invent adoption metrics, testimonials or SENA endorsement marks in UI copy.
