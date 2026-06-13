# DESIGN STANDARDS — fernanda-INF2072

> Research CLI project. No UI or visual design. Standards apply to CLI UX only.

---

## UX Patterns

### App Type

CLI research pipeline. No web or desktop UI.

### Interaction Patterns

- **CLI-first**: all configuration via command-line arguments; no interactive prompts during training
- **Fail fast**: validate arguments before starting expensive training
- **Progress visibility**: emit per-episode reward to stdout during training
- **Idempotent outputs**: run directories are timestamped to prevent overwrite

### Accessibility

N/A — terminal output only.

### Error Handling

- Invalid CLI args: print usage and exit with code 1
- Runtime errors during training: log to stderr and exit with code 1; partial outputs preserved for diagnosis

---

## Graphic / Visual Design

N/A — no visual design surface.

### Reward Plot Style (publication output)

- Format: PNG, 300 DPI
- Library: matplotlib
- Style: clean, minimal (no decorative gridlines)
- Colors: one distinct color per algorithm (consistent across all benchmark plots)
- Labels: algorithm name + mean ± std in legend
