---
id: ADR-0003
status: accepted
---

# Gate Model

## Context

If intent documents are the "what and why," gates are the "enforcement." We need a way to define constraints that are tied to intent nodes and can be run in CI.

## Decision

Gates are YAML files in `/gates/` with:

- An ID (`GATE-*`)
- An `applies_to` list referencing intent nodes
- An `enforced_by` block specifying how to check (command, builtin rule, or AI prompt)
- A `policy` block specifying warn vs. block behavior

Gate types include: command (run a script), builtin (framework-provided rules like spec-quality checks), and AI (LLM conformance check against a spec).

## Alternatives

1. **Hardcoded CI checks** — inflexible, not tied to intent graph
2. **Policy-as-code tools (OPA, Kyverno)** — powerful but separate from intent model
3. **No enforcement** — intent becomes aspirational documentation

## Consequences

- Gates make intent actionable, not just documentary
- CI becomes the enforcement layer, not human reviewers
- Gate YAML is simple enough for non-infra engineers to author
- Must be careful about gate proliferation; start with high-value checks

## Links

- For: [[SPEC-0001]]
