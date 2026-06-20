---
designer_description: "When the reviewer is asked to look at what you built through microinteractions eyes, I'm the checklist that tells it what to watch for -- hover/focus/active states, intermediate loading/skeleton/optimistic/error/empty frames, prefers-reduced-motion support, GPU-composited animations within frame budget, screen-reader-perceivable state changes, and purposeful feedback that matches the weight of the action -- so every interaction feels responsive and deliberate rather than blank or jarring."
tier: Deep-dive
---

# MICRO — Microinteractions

## Essential

- [P0] Are hover, focus, and active states defined for interactive elements?
- [P0] Is there a `prefers-reduced-motion` media query check to disable animations for users who need it?
- [P0] Are all intermediate states (loading, skeleton, optimistic, error, empty, partial) explicitly designed so the UI never shows a blank or broken frame?
- [P0] Are animations GPU-composited (transform/opacity only), avoiding layout thrashing and staying under 16 ms per frame on target low-end devices?
- [P0] Do animated or auto-updating elements expose appropriate ARIA live regions so screen-reader users perceive the state changes sighted users see?

## Deep-dive

- [P1] Are transitions and animations purposeful (guiding attention, confirming actions)?
- [P1] Is feedback immediate and proportional to the action (subtle for minor, prominent for destructive)?
- [P1] Are transition durations and easing functions defined as design tokens for consistency?
- [P1] Do animations follow natural motion principles (ease-in exits, ease-out entrances) and stay within 100-500 ms?
- [P1] Are gesture affordances (swipe, pinch, long-press) discoverable through progressive disclosure or coaching rather than trial-and-error?
- [P2] Are haptic patterns varied by feedback type (light tap for selection, double pulse for error, long press confirmation) rather than a single generic vibration?
- [P2] Do auditory cues (click, chime, alert) complement visual feedback without relying on sound alone, and are they mutable without losing information?
- [P2] Is contextual micro-copy (loading button labels, inline validation, toast confirmations) specific to the action rather than generic ("Done", "Error")?
- [P3] Do microinteractions include moments of delight (success animations, empty-state personality) that reinforce brand tone without slowing task completion?
- [P3] Are progress indicators, streaks, and reward animations calibrated to motivate without anxiety, and do they degrade gracefully when gamification is disabled?
