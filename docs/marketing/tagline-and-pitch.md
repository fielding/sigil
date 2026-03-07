# Sigil — Tagline and Elevator Pitch

## Taglines (ranked)

1. **"Review intent, not just diffs."**
   — Direct. Sets up the core shift. Works as a standalone line on a README badge or site header.

2. **"Architecture you can diff."**
   — Punchy. Speaks to engineers who understand diffs but never thought of diffing architecture.

3. **"Your specs are dead. Sigil keeps them alive."**
   — Provocative. Hooks anyone who's written an ADR that nobody read again.

4. **"Intent-first engineering."**
   — Category-defining. Short enough for a badge or subtitle. Needs context to land.

**Recommended primary tagline:** "Review intent, not just diffs."
**Recommended subtitle:** "An open-source CLI that turns specs, ADRs, and constraints into a reviewable knowledge graph — in your Git repo."

## Elevator Pitch (30 seconds)

> Every engineering team writes specs and ADRs. Almost none of them survive first contact with the codebase. They rot in Notion, they drift from reality, and nobody reviews them in PRs.
>
> Sigil fixes this. It's a CLI that indexes your specs, ADRs, interfaces, and constraints into a knowledge graph — right in your Git repo. When you open a PR, Sigil posts an intent diff as a comment: what architectural decisions changed, what specs were affected, what constraints apply. Your team reviews intent first, code second.
>
> One file, zero platform dependencies, works with GitHub Actions today. You `sigil init`, write your specs in markdown, and your CI starts posting intent diffs on every PR.

## Extended Pitch (60 seconds, for blog posts / talks)

> Code review is broken — not because we review code badly, but because we review the wrong thing. A 4,000-line PR gets reviewed line by line. Nobody asks: "does this match the spec?" Because the spec is in Notion. Or it was never written. Or it was written six months ago and forgotten.
>
> Sigil is an intent-first engineering system. You define your architecture as structured artifacts in your repo: component registries, specs, ADRs, interface contracts, gate constraints. Sigil's CLI indexes these into a knowledge graph with typed relationships — "this component provides this API," "this spec is decided by this ADR," "this gate constrains this interface."
>
> When you open a PR, GitHub Actions runs `sigil diff` and posts the intent graph diff as a comment. Reviewers see what architectural intent changed before they look at a single line of code. That's the shift: review intent, then verify code.
>
> It's a Python CLI. Single file. One dependency (PyYAML). Works today with GitHub Actions. Interactive D3 viewer included. Gate enforcement is on the roadmap.
>
> If your team writes specs that nobody reads, or makes architectural decisions that nobody enforces, Sigil is the feedback loop you're missing.

## Social Bio (for GitHub, Twitter, etc.)

> Intent-first engineering system. CLI that indexes specs, ADRs, and constraints into a knowledge graph in your Git repo. Posts intent diffs on PRs via CI.

## Hashtags / Keywords

`#DevTools` `#ArchitectureAsCode` `#IntentFirstEngineering` `#OpenSource` `#DeveloperExperience`
