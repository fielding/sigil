# Sigil — Intent System (VS Code Extension)

VS Code extension for [Sigil](https://github.com/fielding/sigil) intent-first engineering repos.

## Features

- **[[ID]] Autocomplete** — Type `[[` in markdown/YAML to get completions for all nodes (specs, ADRs, components, gates, interfaces)
- **Go to Definition** — Ctrl+click on `[[SPEC-0001]]` to jump to the source file
- **Unresolved Reference Warnings** — Inline diagnostics for wikilinks pointing to non-existent nodes
- **Quick Fix: Create Missing Node** — Code action to create a node from an unresolved `[[ID]]` reference
- **Lint on Save** — Runs `sigil lint` when intent documents are saved, surfaces findings as VS Code diagnostics
- **Format on Save** — Runs `sigil fmt` to normalize front matter and sections
- **Impact Preview** — Webview panel showing BFS blast radius for any node
- **Command Palette** — `Intent: New Spec`, `Intent: New ADR`, `Intent: New Component`, `Intent: New Gate`, `Intent: New Interface`, `Intent: Lint`, `Intent: Format`, `Intent: Rebuild Index`

## Requirements

- The `sigil` CLI must be installed and on your PATH (or configure `sigil.executable`)
- A `.intent/config.yaml` file must exist in the workspace root

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `sigil.executable` | `"sigil"` | Path to the sigil CLI |
| `sigil.lintOnSave` | `true` | Run lint on save |
| `sigil.fmtOnSave` | `true` | Run fmt on save |

## Development

```bash
cd tools/sigil-vscode
npm install
npm run compile
# Press F5 in VS Code to launch Extension Development Host
```

## Packaging

```bash
npx vsce package
```

This produces a `.vsix` file you can install via `code --install-extension sigil-intent-0.1.0.vsix`.
