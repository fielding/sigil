# Sigil — Positioning Document

## One-Liner

Sigil is an open-source CLI for version-controlling architectural decisions — so product and engineering align on specs before a single line of code is written.

## The Problem

Engineering teams don't have a code review problem. They have a pre-code alignment problem.

Product describes what they want. Engineering says they can build it. Everyone leaves the meeting with a different picture of what "it" is. Specs rot in Notion. ADRs are written once and forgotten. Interface contracts exist in someone's head. Then code gets written against those fuzzy, undocumented assumptions — and two sprints later, someone asks "why is this built this way?" and nobody knows.

**Specific pain points:**

- **Specs rot.** Written in Notion or Google Docs, disconnected from the code they describe. Nobody updates them after the sprint starts.
- **ADRs are write-only.** Teams adopt ADR templates, write a few, then forget they exist. No enforcement loop, no visibility, no connection to anything.
- **Alignment gaps cause rework.** When product and engineering don't share a common picture of what was agreed, code gets built against the wrong assumptions. The review is too late — the code is already written.
- **Architecture is invisible.** Component boundaries, interface contracts, and dependency policies exist as tribal knowledge, not queryable structure.
- **AI-assisted development amplifies misalignment.** Code gets written faster than intent gets documented. The gap between "what was planned" and "what shipped" widens every sprint.

## Who Is Sigil For

### Primary: Engineering Leads and Architects

- Responsible for system design and architectural consistency
- Already write specs and ADRs (or wish their teams did)
- Frustrated that design docs disconnect from code the moment the sprint starts
- Need a way to make architecture visible and agreed-upon *before* sprints start

### Secondary: Product Managers Who Work Closely with Engineering

- Involved in writing specs, reviewing interfaces, and signing off on technical decisions
- Want a shared representation of "what we're building" that both product and engineering can read
- Currently use Notion/Confluence for specs — want those specs to actually matter

### Tertiary: Platform and DevEx Teams

- Building internal developer platforms and CI pipelines
- Want to enforce architectural constraints that were explicitly agreed on
- Looking for lightweight, repo-native tooling that integrates with existing workflows

## What Sigil Is

**A pre-code alignment system.** Sigil provides:

1. **A repo schema** — Structured directories for components, specs, ADRs, interfaces, and gates. Intent lives in Git, next to the code it will eventually describe.
2. **A CLI** — `sigil init`, `sigil new`, `sigil serve`, `sigil check`, `sigil why`. One file, zero platform dependencies.
3. **A knowledge graph** — Nodes (components, specs, ADRs, interfaces, gates) connected by typed edges. Queryable. Diffable. Visible before code is written.
4. **A viewer** — Interactive force graph showing the full picture of what the team has agreed to build. Gaps highlighted in red. Run `sigil serve` before a sprint, not after.
5. **Downstream enforcement** — Once specs are agreed, gates enforce them in CI. Code can't drift from what was decided.

## What Sigil Is NOT

- **Not a code review tool.** Sigil is pre-code, not post-code. By the time you're reviewing a PR, the alignment work should already be done.
- **Not a project management tool.** Sigil doesn't track tickets or sprints. It tracks architectural intent.
- **Not a documentation platform.** No hosted wiki, no WYSIWYG editor. Sigil is files in a repo.
- **Not a code analysis tool.** Sigil doesn't parse your source code. It indexes the intent documents you write about your code.

## Why Now

Three converging trends make Sigil's timing right:

1. **AI-assisted development means specs matter more, not less.** When AI generates code faster than humans can think through architecture, the plan has to be explicit and agreed-upon before the code starts. Sigil provides the pre-code alignment layer that makes AI-generated code trustworthy.

2. **Product and engineering are further apart than ever.** Remote teams, async work, faster release cycles — the informal alignment that used to happen in shared offices doesn't happen anymore. Sigil provides structure that replaces informal alignment.

3. **ADR adoption has plateaued.** Teams tried ADRs. Most stopped maintaining them because there's no enforcement, no visibility, and no integration with the dev loop. Sigil makes ADRs part of the graph, part of the pre-sprint review, and part of CI enforcement downstream.

## Positioning Statement

**For** engineering teams who design before they build,
**Sigil** is an open-source CLI
**that** turns specs, ADRs, and interface contracts into a queryable intent graph — so product and engineering can review the full picture before a sprint starts.
**Unlike** ADR templates, Backstage docs, or scattered Notion pages,
**Sigil** makes alignment happen in Git, not in Slack — and enforces it in CI once agreed.

## Key Messages

| Audience | Message |
|---|---|
| Engineering leads | "Your specs and ADRs are dead because nothing connects them. Sigil turns them into a graph your team reviews before writing code." |
| Product managers | "Stop finding out the code doesn't match the spec after the sprint. Sigil makes the spec the source of truth — before the sprint." |
| Platform teams | "Add spec-enforced constraints to your CI without building another platform. One CLI, zero dependencies." |
| ICs / developers | "See the shape of what you're supposed to build. Understand why things were decided. Write code with a map, not guesswork." |

## Differentiators

| Capability | Sigil | ADR Tools | Backstage | Wiki/Docs |
|---|---|---|---|---|
| Lives in Git | Yes | Yes | No (plugin) | No |
| Knowledge graph | Yes | No | Partial (catalog) | No |
| Typed relationships | Yes | No | No | No |
| Pre-code graph review | Yes | No | No | No |
| Diffable architecture | Yes | No | No | No |
| Zero platform dependency | Yes | Yes | No (React app) | No |
| Interactive visualization | Yes | No | Yes | No |
| CI gate enforcement | Yes | No | No | No |

## Voice Guidelines for Sigil Content

- **Technical, not corporate.** Sigil's audience writes code. Speak their language.
- **Opinionated, not preachy.** "Specs first" is a stance. Own it without lecturing.
- **Concrete, not abstract.** Show the graph. Show the `sigil serve` output. Show the gate failure.
- **Understated confidence.** This is an open-source tool, not a funded startup. Let the work speak.
- **Pre-code, always.** Every message should reinforce: Sigil lives before the code, not after it.
