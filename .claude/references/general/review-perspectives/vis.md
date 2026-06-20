---
designer_description: "When the reviewer is asked to look at what you built through visual-design eyes, I'm the checklist that tells it what to watch for -- design-system consistency, spacing and typographic scale, semantic color tokens for light and dark themes, grid alignment, icon-family coherence, and pixel-perfect rendering across densities -- so the surface you ship feels like one designed product instead of a stitched-together patchwork."
tier: Deep-dive
---

# VIS -- Visual Design

## Essential

- [P0] Is the visual treatment consistent with the project's design system and CSS conventions?
- [P0] Does every visual element (logo usage, palette, typeface) align with brand guidelines, with deviations explicitly approved?
- [P0] Does the dark mode implementation use semantic color tokens (not hard-coded values) and pass contrast checks independently from the light theme?

## Deep-dive

- [P1] Are spacing, typography, and color usage following established patterns?
- [P1] Does it maintain visual hierarchy and readability?
- [P1] Is there a documented design token inventory (colors, spacing, typography) beyond the CSS framework config?
- [P1] Are icon sizes, weights, and spacing consistent across the application?
- [P1] Are typographic scales, line heights, letter-spacing, and font fallbacks defined systematically for readability across breakpoints?
- [P1] Do color combinations meet WCAG contrast, and is the palette built on a perceptually uniform model (OKLCH/CIELAB) to avoid hue shifts at different lightness levels?
- [P1] Is the layout built on a consistent grid with defined columns, gutters, and breakpoint behavior preventing alignment drift?
- [P1] Are design tokens structured in layers (global -> alias -> component) with a single source of truth feeding both design tools and code?
- [P2] Are icons drawn on a uniform pixel grid with consistent stroke widths and optical sizing so they read as one family?
- [P2] Do transitions and animations follow a unified easing/duration set, avoid layout thrashing, and respect `prefers-reduced-motion`?
- [P2] Have final renders been compared pixel-for-pixel against design specs at 1x/2x densities with sub-pixel rounding and asset crispness verified?
- [P2] Do data visualizations use colorblind-safe palettes, legible labels, appropriate chart types, and consistent visual encoding across all charts?
