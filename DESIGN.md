---
name: SmartAttend
description: Editorial restraint in near-monochrome, with one atmospheric gradient carrying the brand's single moment of real color.
colors:
  ink: "#101114"
  muted: "#6b6f76"
  faint: "#9a9ea5"
  line: "#ebebee"
  bg: "#ffffff"
  wash: "#f6f6f7"
  grad-1: "#a9c6e6"
  grad-2: "#f3c969"
  grad-3: "#ef8a3c"
  grad-4: "#cf4d2a"
  ember: "#d9642f"
  ember-tint: "#fbeee3"
  green: "#1f9d5c"
  green-tint: "#e7f7ee"
  red: "#c73b3b"
  red-tint: "#fbecec"
typography:
  display:
    fontFamily: "Syne, IBM Plex Sans, sans-serif"
    fontSize: "clamp(2.1rem, 4.2vw, 3.375rem)"
    fontWeight: 800
    lineHeight: 1.06
    letterSpacing: "-0.02em"
  headline:
    fontFamily: "IBM Plex Sans, Segoe UI, sans-serif"
    fontSize: "21px"
    fontWeight: 800
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  body:
    fontFamily: "IBM Plex Sans, Segoe UI, sans-serif"
    fontSize: "12px"
    fontWeight: 400
    lineHeight: 1.55
  numeral:
    fontFamily: "IBM Plex Mono, ui-monospace, monospace"
    fontSize: "25px"
    fontWeight: 700
    letterSpacing: "-0.01em"
rounded:
  sm: "10px"
  md: "14px"
  lg: "20px"
  pill: "999px"
spacing:
  sm: "8px"
  md: "14px"
  lg: "20px"
  xl: "36px"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0 20px"
  button-primary-hover:
    backgroundColor: "#2a2a30"
    textColor: "#ffffff"
    rounded: "{rounded.pill}"
    padding: "0 20px"
  button-outline:
    backgroundColor: "#ffffff"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    padding: "0 20px"
---

# Design System: SmartAttend

## Overview

**Creative North Star: "One Gradient, Held in Reserve"**

This world is user-pinned, replacing an earlier "banking hall" direction the user found too generic on sight. The reference: a near-monochrome interface — white, black, quiet gray — that spends almost the entire surface in restraint, then cashes that restraint in on exactly one moment: a soft, blurred, multi-hue gradient (cool blue through gold through orange to ember) behind a solid white wordmark. Everywhere else, color is earned, not decorated with.

The system is disciplined about *where* it gets to be loud. The login hero is the one full Persuade-mode moment — first thing a visitor sees, and the only place all four gradient hues appear together. Every Operate surface after that (dashboard, tables, forms, the roster) drops back to ink-on-white with a single warm ember accent, because a task screen fighting its own decoration is a task screen that failed its job. The live-session "Now Serving" panel is the one Operate-mode exception allowed a little theater — a dark plate with an ember countdown and a chase-light pulse — because that screen's entire job *is* a countdown; the theater serves the task there rather than competing with it.

**Key Characteristics:**
- Near-monochrome ink/white/gray base; the four-stop gradient exists in exactly one place (the login hero).
- Two-typeface system: Syne (unusual, confident, wide geometric proportions) for a handful of genuine headline moments only; IBM Plex Sans for everything else, so the display face stays rare enough to still register as a choice.
- Numerals — countdowns, matric numbers, stat values — always set in IBM Plex Mono.
- No kicker/eyebrow labels above headings, anywhere.
- Pills, not rectangles, for every button and status chip.

## Colors

### Primary (reserved: the gradient)
- **Atmosphere Blue → Ember** (`#a9c6e6` → `#f3c969` → `#ef8a3c` → `#cf4d2a`): the one place this system spends real color — a soft blurred radial-mesh background, used only behind the login hero's centered white wordmark. Never appears as text, never repeats elsewhere at full strength.
- **Ember** (`#d9642f`) alone: the gradient's warm end, extracted as the system's single ongoing accent — active/focus states, the countdown numeral, chase-light pulses, small brand touches (the logo mark's accent letter).

### Neutral
- **Ink** (`#101114`): primary text, primary buttons, the sidebar's active-nav weight.
- **Muted** (`#6b6f76`) / **Faint** (`#9a9ea5`): secondary and tertiary text — true grays, appropriate here because the base system itself is neutral (the "tint from the hue" rule applies to text sitting on a colored surface; ink-on-white earns plain gray).
- **Wash** (`#f6f6f7`): the one step off white, for hover states and quiet nested surfaces (inputs, the sidebar's active-item background).
- **Line** (`#ebebee`): hairline dividers, barely-there until a boundary is actually needed.

### Semantic
- **Green** (`#1f9d5c` on `#e7f7ee`): present/success status only — deliberately desaturated so it never competes with ember as "the" accent.
- **Red** (`#c73b3b` on `#fbecec`): errors and flagged attempts.

### Named Rules
**The One Gradient Rule.** The full four-stop gradient appears in exactly one place: the login hero background. Nowhere else in the system may combine more than two of its stops at once. Reuse the ember accent alone wherever "brand color" is needed elsewhere.

## Typography

**Display Font:** Syne (with IBM Plex Sans, sans-serif fallback) — reserved for the login h1, the dashboard/portal welcome headline, and the wordmark.
**Body/UI Font:** IBM Plex Sans (with Segoe UI fallback) — everything else: page titles, card headings, forms, tables, buttons.
**Numeral Font:** IBM Plex Mono — anywhere a number is read at a glance rather than as prose.

**Character:** Syne's unusually wide, confident geometric letterforms give the handful of headline moments real presence without the interface adopting a "personality font" everywhere — the rarity is what keeps it feeling like a choice rather than a theme. IBM Plex Sans carries everything else precisely because it recedes.

### Hierarchy
- **Display** (800, Syne, `clamp(2.1rem, 4.2vw, 3.375rem)`, -0.02em): login h1, welcome/portal-hero h2, the logo wordmark only.
- **Headline** (800, IBM Plex Sans, 20–23px, -0.025em to -0.03em): page titles, modal titles, workspace headers.
- **Title** (700, IBM Plex Sans, 13–16px): card and section headings.
- **Body** (400, IBM Plex Sans, 11–13px, 1.5–1.55): prose and labels.
- **Numeral** (700, IBM Plex Mono, tabular): countdowns, stat values, matric numbers.

### Named Rules
**The Rarity Rule.** Syne is used in four places total across the entire app (logo, login h1, welcome h2, portal-hero h2). Adding a fifth without removing one is a drift signal, not a style choice — the display face's whole job is to stay rare enough to still register.

## Layout

Same functional shell as before the redesign: a 254px fixed sidebar plus a fluid main column, collapsing to an off-canvas drawer under 760px. 36px of page padding on desktop, 18px on mobile. The login page is the one full-bleed exception — a split gradient-hero panel beside a plain white form panel, stacking on mobile.

## Elevation & Depth

Flat-by-default, soft-when-raised: most surfaces sit directly on white or wash with no border at all, relying on a barely-there `shadow-sm` for separation. Modals and the live-session QR card step up to `shadow-md`/`shadow-lg`. No surface combines a border with a shadow — one elevation signal per element, never both.

### Shadow Vocabulary
- **shadow-sm** (`0 1px 3px rgba(16,17,20,.06), 0 1px 2px rgba(16,17,20,.04)`): default card/panel rest state.
- **shadow-md** (`0 8px 24px rgba(16,17,20,.08)`): the QR ticket card, hover states.
- **shadow-lg** (`0 30px 70px rgba(16,17,20,.22)`): modals.

### Named Rules
**The One Signal Rule.** A card is either bordered or shadowed, never both. This system chose shadow-only for every floating surface (cards, panels, the QR ticket); borders are reserved for flush dividers (the sidebar's right edge, the header's bottom edge) that aren't meant to look raised at all.

## Shapes

Pills for every button and status chip (999px radius) — a deliberate break from the earlier ticket-world's sharper geometry, matching the reference's rounded, friendly control language. Cards and panels sit at 14–20px radius, generous enough to feel soft without losing edges. Inputs at 10px.

## Components

### Buttons
- **Primary:** full pill, ink background, white text, `shadow-sm` at rest → `shadow-md` on hover, darkens to `#2a2a30` on hover.
- **Outline:** full pill, white background, 1px hairline border, ink text.
- **Disabled:** 45–50% opacity, no shadow, no hover response.

### Cards / Panels
- **Shape:** 14px radius, shadow-only elevation, no border (see Elevation).
- **Stat tiles:** tone lives entirely in the icon badge's tinted background — no side-stripe accent (explicitly removed during the first pass after the mechanical detector flagged it as a recognized AI-slop tell).

### The Now Serving panel (signature component, carried over)
A dark ink plate inside the live-session modal holding an IBM Plex Mono countdown and a 12-segment chase-light bar that empties in ember as the QR's rotation window runs out — the one authored motion signature in the system. The QR itself sits in a plain white, shadow-only rounded card (no border, no decorative edge treatment) directly above it.

### Inputs / Fields
- **Style:** 1px hairline border, 10px radius, wash background.
- **Focus:** `outline-color` shifts to ink; global `:focus-visible` uses a 2px ember outline for keyboard navigation.
- **Error:** red text on red-tint background.

### Navigation
- **Style:** white sidebar, single right-hand hairline divider (no fill color). Nav items sit in muted gray at rest, shift to ink + a quiet wash background on hover/active — no color-block active state, matching the reference's understated list treatment.
- **Mobile:** off-canvas drawer sliding from the left, scrim behind it.

### Login Hero (signature moment)
The one full-strength expression of the gradient: a radial-mesh blend of all four brand hues behind a centered white logo lockup, darkening toward its lower edge where feature callouts sit as quiet, solid (non-blurred) dark chips — deliberately not glass/backdrop-blur, which the first pass at this component used and which the craft floor flags as decoration without a specific purpose.

## Do's and Don'ts

### Do:
- **Do** keep the gradient to the login hero only; reuse ember alone anywhere else "brand color" is needed.
- **Do** keep numerals in IBM Plex Mono everywhere they're read at a glance.
- **Do** use Syne only for the four named headline moments — check the Rarity Rule before adding a fifth.

### Don't:
- **Don't** add a kicker/eyebrow label above any heading.
- **Don't** combine a border and a shadow on the same card — pick one.
- **Don't** use backdrop-filter/glass effects as decoration; the login feature chips are solid, not glassy, on purpose.
- **Don't** add a colored side-stripe to a card for accent — tint an icon badge or background instead.
