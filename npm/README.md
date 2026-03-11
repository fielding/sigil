# @fielding/sigil

Intent-first engineering CLI — structured decisions, enforced by code.

This is the npm wrapper for [sigil-cli](https://github.com/fielding/sigil). It delegates to a local Python installation.

## Quick Start

```bash
npx @fielding/sigil init
npx @fielding/sigil status
```

## Requirements

- Node.js 18+
- Python 3.11+ (must be on PATH)
- pyyaml (`pip install pyyaml`)

## What is Sigil?

Sigil is an intent-first code review system. Humans review intent (specs, ADRs, interfaces); machines verify code conforms to that intent via gates.

- **Specs** capture what you're building and why
- **ADRs** capture decisions and trade-offs
- **Gates** enforce constraints automatically
- **Interfaces** define contracts between components

## Prefer pip?

If you already have Python, `pip install sigil-cli` is the simpler path:

```bash
pip install sigil-cli
sigil init
```

## Install globally via npm

```bash
npm install -g @fielding/sigil
sigil status
```

## More info

See the [full documentation](https://github.com/fielding/sigil) on GitHub.
