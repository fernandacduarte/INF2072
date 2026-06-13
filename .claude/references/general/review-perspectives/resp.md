---
designer_description: "When the reviewer is asked to look at what you built through responsive-design eyes, I'm the checklist that tells it what to watch for -- mobile-first progressive enhancement, breakpoint behaviour, fluid typography, touch-target sizing, responsive images and tables, container queries, and real-device verification across iOS/Android/non-Chromium browsers -- so the layout holds up from the narrowest phone to the widest desktop without horizontal scroll or hinge-collision."
tier: Deep-dive
---

# RESP — Responsive Design

## Essential

- [P0] Does this work correctly on mobile, tablet, and desktop breakpoints?
- [P0] Does the layout adapt without horizontal scrolling or content overflow?
- [P0] Does the implementation follow a mobile-first approach, progressively enhancing via min-width media queries rather than overriding desktop layouts?
- [P0] Are all interactive elements (swipe gestures, hover-dependent menus, drag handles) adapted for touch input with fallbacks and pointer-type detection?

## Deep-dive

- [P1] Are touch targets appropriately sized (min 44x44px)?
- [P1] Are breakpoint behaviors tested in E2E tests or visual regression tests?
- [P1] Are fluid typography scales (clamp()-based font sizes) used for readable text across the viewport continuum without abrupt jumps at breakpoints?
- [P1] Are responsive images served with srcset/sizes or the <picture> element for art direction, ensuring appropriate resolutions per breakpoint?
- [P1] Do data-heavy tables use a responsive pattern (horizontal scroll, card reflow, column prioritisation) that preserves readability on narrow viewports?
- [P1] Has the layout been verified on real devices across iOS Safari, Android Chrome, and at least one non-Chromium desktop browser?
- [P1] Are container queries used where component-level responsiveness is needed, avoiding fragile assumptions about the parent's viewport width?
- [P2] Are print stylesheets defined for content-heavy pages (discussions, exports)?
- [P2] Do print stylesheets strip non-essential UI (navigation, ads, interactive widgets) and apply appropriate page-break rules for multi-page content?
- [P2] Does the layout account for foldable and dual-screen devices by respecting the viewport segments API (env(viewport-segment-*)) to avoid content on the hinge?
- [P3] For HTML email, does the responsive approach degrade gracefully in clients that ignore media queries (Gmail app, Outlook desktop) via fluid-hybrid or spongy techniques?
