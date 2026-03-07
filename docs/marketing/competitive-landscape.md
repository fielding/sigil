# Sigil — Competitive Landscape

## Summary

Sigil occupies a new category: **intent-first engineering tooling**. No existing tool combines structured intent artifacts, a knowledge graph, typed relationships, and CI-native graph diffing in a single repo-native package. The closest alternatives each solve a piece of the problem.

## Detailed Comparison

### 1. ADR Tools (adr-tools, log4brains, MADR)

**What they do:** CLI tools for creating and managing Architectural Decision Records as markdown files in a repo.

**Where they overlap with Sigil:**
- Repo-native markdown artifacts
- CLI for scaffolding new documents
- Git-versioned decision history

**Where Sigil differentiates:**
- **Graph structure.** ADR tools treat decisions as a flat list. Sigil connects ADRs to components, specs, interfaces, and gates via typed edges. An ADR isn't just a document — it's a node in a queryable graph.
- **CI integration.** ADR tools don't post diffs on PRs. Sigil's `sigil diff` computes graph-level changes and posts them as PR comments.
- **Broader scope.** ADR tools only handle decisions. Sigil handles specs, components, interfaces, and gates — the full intent surface.
- **Visualization.** No ADR tool provides an interactive graph viewer.

**Our take:** ADR tools proved the category (decisions-as-code). Sigil extends it to the full intent surface with graph semantics and CI.

---

### 2. Backstage (Spotify)

**What it does:** An open-source developer portal platform. Service catalog, docs-as-code (TechDocs), plugin ecosystem, scaffolding templates.

**Where it overlaps with Sigil:**
- Service/component catalog
- Documentation co-located with services
- Scaffolding for new components

**Where Sigil differentiates:**
- **No platform to deploy.** Backstage is a React application that requires hosting, a database, auth, and ongoing maintenance. Sigil is a single Python file you run locally or in CI.
- **Graph semantics.** Backstage's catalog has entity relationships, but they're primarily for service discovery, not architectural intent. Sigil's typed edges (decided_by, gated_by, provides) capture why things exist, not just that they exist.
- **Diff-native.** Backstage has no concept of diffing architectural state across commits. Sigil was built for this.
- **Intent-first, not portal-first.** Backstage is a platform you visit. Sigil meets you in the PR, in the terminal, in your editor (soon).

**Our take:** Backstage is excellent for service discovery and developer portals. Sigil is complementary — it handles the intent layer that Backstage doesn't. A team could use both: Backstage for "what services exist" and Sigil for "why they're built this way."

---

### 3. Wikis and Doc Platforms (Notion, Confluence, Google Docs)

**What they do:** General-purpose documentation and knowledge management.

**Where they overlap with Sigil:**
- Specs and design docs are written here today
- Collaboration and commenting

**Where Sigil differentiates:**
- **In Git, not in a silo.** Docs in Notion are disconnected from the codebase. They can't be diffed across commits, linted in CI, or linked to specific components with typed edges.
- **Structured, not freeform.** Wikis let you write anything. Sigil enforces structure: required sections, valid statuses, explicit relationships. Structure enables automation.
- **Reviewable in PRs.** You can't put a Notion page in a PR comment. Sigil's intent diffs are native to the code review workflow.
- **No rot.** Wiki docs rot because there's no feedback loop. Sigil's CI integration creates the feedback loop — if you change intent, the diff shows up in the PR.

**Our take:** Wikis are where specs go to die. Sigil is where they stay alive. We're not replacing Notion for general docs — we're replacing it specifically for architectural intent.

---

### 4. Architecture-as-Code Tools (Structurizr, C4 model tools, Diagrams-as-code)

**What they do:** Define software architecture using code (DSLs, YAML, or Python) and generate diagrams.

**Where they overlap with Sigil:**
- Architecture defined in repo
- Visual output from code/config inputs
- Component-level modeling

**Where Sigil differentiates:**
- **Intent, not just structure.** Architecture-as-code tools model what the system looks like. Sigil models why it's built that way — the specs, decisions, and constraints behind the structure.
- **Review workflow.** These tools generate diagrams. Sigil generates PR comments. The output is designed for the code review loop, not a documentation site.
- **Broader artifact types.** Architecture tools model components and relationships. Sigil also models specs, ADRs, interface contracts, and gate constraints.

**Our take:** Architecture-as-code is the right instinct (define structure in repo). Sigil goes further: define intent in repo, with enforcement.

---

### 5. RFC/Design Doc Templates (Google's design doc template, Uber's RFCs)

**What they do:** Standardized templates for writing design documents, typically stored in Google Docs or a wiki.

**Where they overlap with Sigil:**
- Structured design documents
- Sections for context, goals, alternatives, decisions

**Where Sigil differentiates:**
- **Not just a template — a system.** Templates give you structure. Sigil gives you structure + indexing + graph + diff + lint + CI. The template is step one; Sigil is the whole lifecycle.
- **Repo-native.** RFC templates live in docs. Sigil specs live in Git, versioned with the code.
- **Queryable relationships.** An RFC might mention a service. A Sigil spec has a typed `belongs_to` edge to a component. That's the difference between text and data.

**Our take:** Every team should have design doc templates. Sigil makes them operational.

---

## Competitive Matrix

| Capability | Sigil | ADR Tools | Backstage | Wikis | Arch-as-Code |
|---|---|---|---|---|---|
| Repo-native artifacts | Yes | Yes | Partial | No | Yes |
| Knowledge graph | Yes | No | Partial | No | Partial |
| Typed relationships | Yes | No | Limited | No | Yes |
| CI integration (PR diffs) | Yes | No | No | No | No |
| Interactive viewer | Yes | No | Yes | N/A | Yes |
| Lint / validation | Yes | No | Yes | No | Partial |
| Scaffolding CLI | Yes | Yes | Yes | No | No |
| Zero platform dependency | Yes | Yes | No | No | Mostly |
| Covers full intent surface | Yes | Decisions only | Catalog only | Freeform | Structure only |
| Gate enforcement | Roadmap | No | No | No | No |

## Positioning Relative to Alternatives

**We are NOT replacing:** Backstage, Notion, your wiki, or your diagramming tool.

**We ARE replacing:** The gap between "we wrote a spec" and "the spec actually matters in code review." Sigil is the missing feedback loop between design documents and the development workflow.

**Adjacent, not competitive:** Sigil can coexist with all of the above. Use Notion for meeting notes. Use Backstage for your service catalog. Use Structurizr for diagrams. Use Sigil for the intent that governs all of it — and make that intent reviewable in every PR.
