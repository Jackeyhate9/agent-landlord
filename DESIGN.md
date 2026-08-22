---
name: Agent Landlord Broadcast System
description: A restrained AI-esports broadcast world built from tournament scoreboards, black-felt card tables, and engraved metal controls.
colors:
  arena-black: "#080A0C"
  table-black: "#101417"
  panel-steel: "#171D21"
  rail-line: "#303A40"
  broadcast-ivory: "#F4F1E8"
  muted-silver: "#A6B0B5"
  signal-amber: "#F3B43F"
  status-cyan: "#57D6DC"
  landlord-red: "#E0574F"
  verified-green: "#67C587"
typography:
  display:
    fontFamily: "Bahnschrift, DIN Alternate, Arial Narrow, sans-serif"
    fontSize: "clamp(2rem, 4.8vw, 5.25rem)"
    fontWeight: 700
    lineHeight: 0.92
    letterSpacing: "-0.025em"
  body:
    fontFamily: "Segoe UI Variable, Segoe UI, system-ui, sans-serif"
    fontSize: "1rem"
    fontWeight: 450
    lineHeight: 1.5
  label:
    fontFamily: "Bahnschrift, DIN Alternate, Arial Narrow, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 650
    lineHeight: 1.1
    letterSpacing: "0.08em"
rounded:
  control: "6px"
  panel: "12px"
  card: "9px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "24px"
  xl: "40px"
components:
  button-primary:
    backgroundColor: "{colors.signal-amber}"
    textColor: "{colors.arena-black}"
    rounded: "{rounded.control}"
    padding: "12px 18px"
  panel:
    backgroundColor: "{colors.panel-steel}"
    textColor: "{colors.broadcast-ivory}"
    rounded: "{rounded.panel}"
    padding: "16px"
---

# Design System: Agent Landlord Broadcast System

## Overview

**Creative North Star: "The Tournament Rail"**

Agent Landlord looks like a purpose-built broadcast object: the dark restraint of a televised poker table, the rigid information hierarchy of an esports scorebug, and the tactile economy of engraved production hardware. It is dark because operators and viewers use it for long stretches beside luminous video sources, not because “AI” implies neon. Public surfaces recede behind the match; Join and Admin turn the same language into dependable operating instruments.

**Key Characteristics:**

- Near-black fields with ivory type and two scarce signal colors.
- Rail-like frames, clipped labels, tabular figures, and crisp dividers.
- Large custom playing cards as the authored visual asset.
- Motion tied to named game events; no ambient decorative animation.

## Colors

The palette is a blackened steel broadcast chassis lifted by warm scoreboard amber, cool connectivity cyan, and semantic match colors.

### Primary

- **Signal Amber:** Reserved for the current turn, primary action, multiplier, and critical live emphasis.

### Secondary

- **Status Cyan:** Connectivity, LIVE POV, and informational state.
- **Landlord Red:** Landlord role, loss, destructive operations, and elimination.

### Neutral

- **Arena Black / Table Black:** Page and field planes.
- **Panel Steel / Rail Line:** Structural surfaces and separators.
- **Broadcast Ivory / Muted Silver:** Primary and secondary text.

**The Two-Signal Rule.** Amber and cyan must not compete in the same hierarchy; amber means act or watch now, cyan means connected or selected.

## Typography

**Display Font:** Bahnschrift (with DIN Alternate / Arial Narrow fallback)  
**Body Font:** Segoe UI Variable (with system UI fallback)  
**Label Font:** Bahnschrift

**Character:** Condensed display type recalls tournament graphics without dressing all prose as telemetry. Human-readable Chinese body copy stays in a native UI stack.

### Hierarchy

- **Display:** Dense match titles, rankings, and result slates only.
- **Headline:** Page and control-group titles.
- **Body:** Instructions, status explanations, and form content; keep long copy within 70 characters.
- **Label:** Short tournament labels and measurements; uppercase is reserved for truly short English terms.

**The Commentary Rule.** Strategy comments remain body copy; the interface never impersonates or exposes chain of thought.

## Layout

Public broadcast surfaces use a 16:9 composition with the table or ordered roster as the dominant field and a narrow scoreboard rail for secondary facts. Operate surfaces use a left command rail and a flexible workspace. Spacing follows 4/8/16/24/40px. Below 900px the composition becomes a single reading column, the table remains horizontally coherent, and nonessential ornamental labels collapse before content. OBS mode fills the viewport, removes navigation and scrolling, and preserves safe insets.

## Elevation & Depth

Depth comes from tonal planes, inset rails, and rare offset shadows under cards in motion. Panels do not combine border and ambient shadow. Overlays use a true dimming scrim only when focus must be protected.

**The Broadcast Plane Rule.** Static information lives flat; only cards, menus, and event slates may visibly rise above the table.

## Shapes

Controls use tight 6px corners, panels use 12px corners, and playing cards use 9px corners. Chamfered notches may mark scoreboards and live labels. Pills are limited to compact status chips. Borders are one physical pixel; decorative double outlines are prohibited.

## Components

### Buttons

- **Shape:** Compact broadcast control with a 6px radius.
- **Primary:** Amber on black for the next irreversible or workflow-advancing action.
- **Hover / Focus:** Lift luminance and show a high-contrast two-pixel focus ring; never rely on glow alone.
- **Danger:** Red only for destructive authenticated controls.

### Chips

- **Style:** Small solid or outlined status markers with text and icon/shape redundancy.
- **State:** LIVE/connected cyan, current/attention amber, landlord/destructive red, success green.

### Cards / Containers

- **Corner Style:** Restrained 12px panels or 9px playing cards.
- **Background:** Single tonal plane without glass blur.
- **Shadow Strategy:** Flat by default; playing cards carry an offset table shadow.
- **Border:** A divider or a shadow, never both as redundant decoration.

### Inputs / Fields

- **Style:** Black inset field, rail-line stroke, 6px radius, ivory value text.
- **Focus:** Cyan two-pixel outline plus brighter label.
- **Error / Disabled:** Error text names both the failure and recovery; disabled state retains readable contrast.

### Navigation

Navigation is a compact tournament switcher, visually subordinate to the live surface. Active location uses an amber baseline and `aria-current`; OBS mode removes it entirely.

### Playing Card

Cards are authored SVG-backed components with oversized corner ranks, suit marks, and broadcast-legible contrast. Jokers use distinct red/black vertical lettering; hidden cards use the arena monogram rather than borrowed artwork.

## Do's and Don'ts

### Do:

- **Do** make current turn, connectivity, role, and legal next action independently legible.
- **Do** use tabular numerals for Arena Token, stake, multiplier, queue position, and countdowns.
- **Do** tie sound and motion to explicit server events and respect reduced-motion preferences.
- **Do** treat empty, loading, reconnecting, timeout, and error states as first-class broadcast states.

### Don't:

- **Don't** use large gradients, noise, glass panels, or neon halos as atmosphere.
- **Don't** build the page from repeated equal cards; order and spatial position must carry meaning.
- **Don't** display unverified model labels as certification or public comments as private reasoning.
- **Don't** use sound as the sole signal for any game or admin event.
