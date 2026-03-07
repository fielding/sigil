---
id: ADR-0005
status: accepted
---

# Human++ Integration

## Context

Sigil needed a visual identity for its viewer and a convention for annotating intent documents. The founder already maintained human++, a Base24 color scheme built around the thesis that "code is cheap, intent is scarce." The scheme provides 24 colors in three tiers (grayscale, loud accents, quiet accents) plus three annotation markers for human judgment in code.

!! Annotation markers are what make intent docs scannable. Without them, everything looks the same.

## Decision

Adopt human++ as the default color scheme and annotation system for all Sigil surfaces.

**Color palette:** All 24 Base24 colors from `palette.json`, applied via CSS variables (`--base00` through `--base17`). Dark background (base00: `#1a1c22`), muted syntax (base10-17), loud accents for diagnostics and human markers (base08-0F).

**Annotation markers:**

| Marker | Meaning | Color |
|--------|---------|-------|
| `!!` | Attention -- critical concern | base0F (lime `#bbff00`) |
| `??` | Uncertainty -- low confidence | base0E (purple `#9871fe`) |
| `>>` | Reference -- pointer to related context | base0C (cyan `#1ad0d6`) |

Keyword aliases are also recognized: FIXME/BUG/XXX map to `!!`, TODO/HACK map to `??`, NOTE/NB map to `>>`.

**Rendering:** Markers are post-processed after markdown-to-HTML conversion. Each marker becomes a styled `<span>` with colored background, bold text, and 4px border radius.

## Alternatives

1. **No theme** -- plain markdown rendering. Rejected: too bland, no visual distinction for human judgment markers.
2. **Custom theme** -- build a Sigil-specific palette. Rejected: unnecessary work when human++ already exists and the founder uses it everywhere.
3. **Configurable themes** -- let users pick their own Base16/24 scheme. Deferred: good idea for later, but premature for v1.

## Consequences

- Viewer has a strong visual identity out of the box
- Intent docs can use `!!`, `??`, `>>` markers that render meaningfully in the viewer
- VS Code users who install the human++ extension get consistent highlighting in both editor and viewer
- Tight coupling to one color scheme -- will need a theme system if we open-source

>> See [[SPEC-0003]] for how the viewer implements human++ rendering.

## Links

- For: [[SPEC-0003]]
- Belongs to: [[COMP-intent-system]]
