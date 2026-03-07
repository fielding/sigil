# Sigil — Positioning Document

## One-Liner

Sigil is an open-source CLI that makes architectural intent reviewable, visible, and enforceable — directly in your Git repo.

## The Problem

Engineering teams have a review problem, and it isn't code review.

Code review catches syntax bugs and style issues. It does not catch architectural drift, forgotten constraints, or decisions that contradict last quarter's ADR. The "why" behind code changes lives in Slack threads, Notion pages, meeting recordings, and people's heads. When those people leave, the intent leaves with them.

**Specific pain points:**

- **Specs rot.** They're written in Notion or Google Docs, disconnected from the code they describe. Nobody updates them after the initial PR merges.
- **ADRs are write-only.** Teams adopt ADR templates, write a few, then forget they exist. There's no enforcement loop.
- **Code review is diff-centric.** Reviewers see 4,000 lines of code changes and try to infer whether they match the plan. They can't — the plan isn't in the PR.
- **Architecture is invisible.** Component boundaries, interface contracts, and dependency policies exist as tribal knowledge, not queryable structure.
- **AI-assisted development accelerates drift.** When AI generates code faster than humans can review intent, the gap between "what was planned" and "what shipped" widens faster than ever.

## Who Is Sigil For

### Primary: Engineering Leads and Architects

- Responsible for system design and architectural consistency
- Already write specs and ADRs (or wish their teams did)
- Frustrated that design docs disconnect from code the moment they're written
- Need a way to make architecture visible and reviewable without adding another platform

### Secondary: Platform and DevEx Teams

- Building internal developer platforms and CI pipelines
- Want to enforce architectural constraints without manual review bottlenecks
- Looking for lightweight, repo-native tooling that integrates with existing workflows

### Tertiary: Individual Contributors on Teams That Value Design

- Engineers who want to write better specs and understand system structure
- Tired of asking "why was this built this way?" and getting no answer

## What Sigil Is

**An intent-first engineering system.** Sigil provides:

1. **A repo schema** — Structured directories for components, specs, ADRs, interfaces, and gates. Intent lives in Git, next to the code it describes.
2. **A CLI** — `sigil index`, `sigil diff`, `sigil new`, `sigil lint`, `sigil fmt`, `sigil bootstrap`, `sigil init`. One file, zero platform dependencies.
3. **A knowledge graph** — Nodes (components, specs, ADRs, interfaces, gates) connected by typed edges (belongs_to, provides, depends_on, gated_by). Queryable. Diffable.
4. **A viewer** — Interactive D3 force graph that renders the shape of your system from intent artifacts.
5. **CI integration** — GitHub Actions workflow posts intent graph diffs as PR comments. Intent review becomes the default review surface.

## What Sigil Is NOT

- **Not a project management tool.** Sigil doesn't track tickets or sprints. It tracks architectural intent.
- **Not a documentation platform.** No hosted wiki, no WYSIWYG editor. Sigil is files in a repo.
- **Not a code analysis tool.** Sigil doesn't parse your source code. It indexes the intent documents you write about your code.
- **Not a governance platform (yet).** Gate enforcement is on the roadmap. Today, Sigil makes intent visible and reviewable. Tomorrow, it makes intent enforceable.

## Why Now

Three converging trends make Sigil's timing right:

1. **AI-assisted development is mainstream.** GitHub Copilot, Cursor, Claude Code — engineers generate code faster than ever. But faster code generation without intent tracking means faster architectural drift. Sigil provides the missing feedback loop.

2. **Platform engineering is mature enough to care about intent.** Teams have CI, IDP, and service catalogs. The next gap is: "does this service actually conform to the spec we agreed on?" Sigil fills that gap without requiring a new platform.

3. **ADR adoption has plateaued.** Teams tried ADRs. Most stopped maintaining them because there's no enforcement, no visibility, and no integration with the dev loop. Sigil makes ADRs part of the graph, part of CI, and part of review.

## Positioning Statement

**For** engineering teams who design before they build,
**Sigil** is an open-source CLI
**that** makes architectural intent reviewable, visible, and enforceable in Git.
**Unlike** ADR templates, Backstage docs, or scattered Notion pages,
**Sigil** turns specs, decisions, and constraints into a knowledge graph with CI integration — so your architecture is reviewed as carefully as your code.

## Key Messages

| Audience | Message |
|---|---|
| Engineering leads | "Your specs and ADRs are already dead. Sigil keeps them alive by making them part of your CI pipeline." |
| Platform teams | "Add intent enforcement to your IDP without building another platform. One CLI, zero dependencies." |
| ICs / developers | "See the shape of your system. Understand why things were built the way they were. Write specs that actually get reviewed." |
| Engineering managers | "AI writes code 10x faster now. Sigil makes sure it writes the right code — by making the plan reviewable." |

## Differentiators

| Capability | Sigil | ADR Tools | Backstage | Wiki/Docs |
|---|---|---|---|---|
| Lives in Git | Yes | Yes | No (plugin) | No |
| Knowledge graph | Yes | No | Partial (catalog) | No |
| Typed relationships | Yes | No | No | No |
| CI integration (PR comments) | Yes | No | No | No |
| Diffable architecture | Yes | No | No | No |
| Zero platform dependency | Yes | Yes | No (React app) | No |
| Interactive visualization | Yes | No | Yes | No |
| Gate enforcement (roadmap) | Planned | No | No | No |

## Voice Guidelines for Sigil Content

- **Technical, not corporate.** Sigil's audience writes code. Speak their language.
- **Opinionated, not preachy.** "Intent-first" is a stance. Own it without lecturing.
- **Concrete, not abstract.** Show the CLI output. Show the PR comment. Show the graph.
- **Understated confidence.** This is an open-source tool, not a funded startup. Let the work speak.
- **Acknowledge the problem honestly.** "Your ADRs are dead" resonates because it's true.
