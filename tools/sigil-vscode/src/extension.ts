import * as vscode from "vscode";
import * as cli from "./cli";
import * as path from "path";

const WIKILINK_RE = /\[\[([^\]]*)/;
const WIKILINK_FULL_RE = /\[\[([A-Z][\w-]*(?:-\d+)?)\]\]/g;

let diagnosticCollection: vscode.DiagnosticCollection;
let searchNodes: cli.SearchNode[] = [];

export function activate(context: vscode.ExtensionContext) {
  const root = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  if (!root) {
    return;
  }

  diagnosticCollection =
    vscode.languages.createDiagnosticCollection("sigil");
  context.subscriptions.push(diagnosticCollection);

  // Load search index on activation
  refreshIndex(root);

  // --- Autocomplete for [[ID]] wikilinks ---
  const completionProvider = vscode.languages.registerCompletionItemProvider(
    [{ language: "markdown" }, { language: "yaml" }],
    {
      provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position
      ) {
        const lineText = document.lineAt(position).text;
        const textBefore = lineText.substring(0, position.character);
        const match = textBefore.match(WIKILINK_RE);
        if (!match) {
          return undefined;
        }

        const prefix = match[1].toLowerCase();
        return searchNodes
          .filter(
            (n) =>
              n.id.toLowerCase().includes(prefix) ||
              n.title.toLowerCase().includes(prefix)
          )
          .map((n) => {
            const item = new vscode.CompletionItem(
              n.id,
              vscode.CompletionItemKind.Reference
            );
            item.detail = n.title;
            item.documentation = `${n.type} — ${n.path}`;
            item.insertText = n.id;
            item.filterText = `[[${n.id}`;
            return item;
          });
      },
    },
    "[" // trigger on [
  );
  context.subscriptions.push(completionProvider);

  // --- Quick fix for unresolved wikilinks ---
  const codeActionProvider = vscode.languages.registerCodeActionsProvider(
    [{ language: "markdown" }],
    {
      provideCodeActions(
        document: vscode.TextDocument,
        _range: vscode.Range,
        context: vscode.CodeActionContext
      ) {
        const actions: vscode.CodeAction[] = [];
        for (const diag of context.diagnostics) {
          if (diag.source !== "sigil" || diag.code !== "unresolved-ref") {
            continue;
          }
          const nodeId = document.getText(diag.range);
          const action = new vscode.CodeAction(
            `Create missing node: ${nodeId}`,
            vscode.CodeActionKind.QuickFix
          );
          action.command = {
            command: "sigil.createMissing",
            title: "Create missing node",
            arguments: [nodeId, root],
          };
          action.diagnostics = [diag];
          action.isPreferred = true;
          actions.push(action);
        }
        return actions;
      },
    },
    { providedCodeActionKinds: [vscode.CodeActionKind.QuickFix] }
  );
  context.subscriptions.push(codeActionProvider);

  // --- Inline diagnostics for unresolved wikilinks ---
  const updateDiagnostics = (document: vscode.TextDocument) => {
    if (document.languageId !== "markdown") {
      return;
    }
    const relPath = vscode.workspace.asRelativePath(document.uri);
    if (
      !relPath.startsWith("intent/") &&
      !relPath.startsWith("interfaces/")
    ) {
      return;
    }

    const diags: vscode.Diagnostic[] = [];
    const knownIds = new Set(searchNodes.map((n) => n.id.toUpperCase()));
    const text = document.getText();
    let m: RegExpExecArray | null;
    const re = new RegExp(WIKILINK_FULL_RE.source, "g");
    while ((m = re.exec(text)) !== null) {
      const refId = m[1];
      if (!knownIds.has(refId.toUpperCase())) {
        const startPos = document.positionAt(m.index + 2); // skip [[
        const endPos = document.positionAt(m.index + 2 + refId.length);
        const diag = new vscode.Diagnostic(
          new vscode.Range(startPos, endPos),
          `Unresolved reference: ${refId}`,
          vscode.DiagnosticSeverity.Warning
        );
        diag.source = "sigil";
        diag.code = "unresolved-ref";
        diags.push(diag);
      }
    }
    diagnosticCollection.set(document.uri, diags);
  };

  // Update diagnostics on open and change
  context.subscriptions.push(
    vscode.workspace.onDidOpenTextDocument(updateDiagnostics)
  );
  context.subscriptions.push(
    vscode.workspace.onDidChangeTextDocument((e) =>
      updateDiagnostics(e.document)
    )
  );
  // Run on already-open documents
  vscode.workspace.textDocuments.forEach(updateDiagnostics);

  // --- On-save: fmt + lint ---
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (document) => {
      const relPath = vscode.workspace.asRelativePath(document.uri);
      const isIntent =
        relPath.startsWith("intent/") ||
        relPath.startsWith("components/") ||
        relPath.startsWith("interfaces/") ||
        relPath.startsWith("gates/");
      if (!isIntent) {
        return;
      }

      const config = vscode.workspace.getConfiguration("sigil");

      if (config.get<boolean>("fmtOnSave", true)) {
        await cli.fmt(root);
      }

      if (config.get<boolean>("lintOnSave", true)) {
        await runLintDiagnostics(root);
      }

      // Refresh search index after changes
      refreshIndex(root);
    })
  );

  // --- Commands ---

  // New Spec
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.newSpec", async () => {
      const component = await vscode.window.showInputBox({
        prompt: "Component slug (e.g. auth-service)",
      });
      if (!component) {
        return;
      }
      const title = await vscode.window.showInputBox({
        prompt: "Spec title",
      });
      if (!title) {
        return;
      }
      const output = await cli.newNode("spec", [component, title], root);
      vscode.window.showInformationMessage(output.trim());
      refreshIndex(root);
    })
  );

  // New ADR
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.newAdr", async () => {
      const component = await vscode.window.showInputBox({
        prompt: "Component slug",
      });
      if (!component) {
        return;
      }
      const title = await vscode.window.showInputBox({
        prompt: "ADR title",
      });
      if (!title) {
        return;
      }
      const output = await cli.newNode("adr", [component, title], root);
      vscode.window.showInformationMessage(output.trim());
      refreshIndex(root);
    })
  );

  // New Component
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.newComponent", async () => {
      const slug = await vscode.window.showInputBox({
        prompt: "Component slug",
      });
      if (!slug) {
        return;
      }
      const name = await vscode.window.showInputBox({
        prompt: "Display name (optional)",
      });
      const args = name ? [slug, name] : [slug];
      const output = await cli.newNode("component", args, root);
      vscode.window.showInformationMessage(output.trim());
      refreshIndex(root);
    })
  );

  // New Gate
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.newGate", async () => {
      const title = await vscode.window.showInputBox({
        prompt: "Gate title",
      });
      if (!title) {
        return;
      }
      const appliesTo = await vscode.window.showInputBox({
        prompt: "Applies to (comma-separated node IDs, optional)",
      });
      const args = appliesTo ? [title, "--applies-to", appliesTo] : [title];
      const output = await cli.newNode("gate", args, root);
      vscode.window.showInformationMessage(output.trim());
      refreshIndex(root);
    })
  );

  // New Interface
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.newInterface", async () => {
      const id = await vscode.window.showInputBox({
        prompt: "Interface ID (e.g. API-AUTH-V1)",
      });
      if (!id) {
        return;
      }
      const title = await vscode.window.showInputBox({
        prompt: "Interface title",
      });
      if (!title) {
        return;
      }
      const output = await cli.newNode("interface", [id, title], root);
      vscode.window.showInformationMessage(output.trim());
      refreshIndex(root);
    })
  );

  // Impact preview
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.impact", async () => {
      const nodeId = await pickNode("Select node for impact analysis");
      if (!nodeId) {
        return;
      }
      const result = await cli.impact(nodeId, root);
      if (!result) {
        vscode.window.showWarningMessage(
          `No impact data for ${nodeId}`
        );
        return;
      }
      const panel = vscode.window.createWebviewPanel(
        "sigilImpact",
        `Impact: ${result.node.id}`,
        vscode.ViewColumn.Beside,
        {}
      );
      panel.webview.html = renderImpactHtml(result);
    })
  );

  // Lint
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.lint", () =>
      runLintDiagnostics(root)
    )
  );

  // Format
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.fmt", async () => {
      const output = await cli.fmt(root);
      vscode.window.showInformationMessage(
        output.trim() || "Format complete"
      );
    })
  );

  // Rebuild index
  context.subscriptions.push(
    vscode.commands.registerCommand("sigil.index", async () => {
      await cli.index(root);
      refreshIndex(root);
      vscode.window.showInformationMessage("Sigil index rebuilt");
    })
  );

  // Create missing node (from quick fix)
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "sigil.createMissing",
      async (nodeId: string, cwd: string) => {
        const idUpper = nodeId.toUpperCase();
        let type: string;
        if (idUpper.startsWith("SPEC-")) {
          type = "spec";
        } else if (idUpper.startsWith("ADR-")) {
          type = "adr";
        } else if (idUpper.startsWith("GATE-")) {
          type = "gate";
        } else if (idUpper.startsWith("COMP-")) {
          type = "component";
        } else {
          type = await vscode.window.showQuickPick(
            ["spec", "adr", "component", "gate", "interface"],
            { placeHolder: `Type for ${nodeId}` }
          ) ?? "";
          if (!type) {
            return;
          }
        }

        if (type === "spec" || type === "adr") {
          const component = await vscode.window.showInputBox({
            prompt: "Component slug for this " + type,
          });
          if (!component) {
            return;
          }
          const title = await vscode.window.showInputBox({
            prompt: `${type} title`,
          });
          if (!title) {
            return;
          }
          await cli.newNode(type, [component, title], cwd);
        } else if (type === "component") {
          const slug = nodeId.replace(/^COMP-/i, "");
          await cli.newNode(
            "component",
            [slug, slug],
            cwd
          );
        } else if (type === "gate") {
          const title = await vscode.window.showInputBox({
            prompt: "Gate title",
          });
          if (!title) {
            return;
          }
          await cli.newNode("gate", [title], cwd);
        } else if (type === "interface") {
          const title = await vscode.window.showInputBox({
            prompt: "Interface title",
          });
          if (!title) {
            return;
          }
          await cli.newNode("interface", [nodeId, title], cwd);
        }

        refreshIndex(cwd);
        vscode.window.showInformationMessage(`Created ${nodeId}`);
      }
    )
  );

  // --- Wikilink definition provider (ctrl+click [[ID]]) ---
  const definitionProvider = vscode.languages.registerDefinitionProvider(
    [{ language: "markdown" }],
    {
      provideDefinition(
        document: vscode.TextDocument,
        position: vscode.Position
      ) {
        const range = document.getWordRangeAtPosition(
          position,
          /\[\[([A-Z][\w-]*(?:-\d+)?)\]\]/
        );
        if (!range) {
          return undefined;
        }
        const text = document.getText(range);
        const id = text.replace(/^\[\[|\]\]$/g, "");
        const filePath = cli.findNodeFile(id, root);
        if (!filePath) {
          return undefined;
        }
        return new vscode.Location(
          vscode.Uri.file(filePath),
          new vscode.Position(0, 0)
        );
      },
    }
  );
  context.subscriptions.push(definitionProvider);

  vscode.window.showInformationMessage("Sigil intent system activated");
}

function refreshIndex(root: string) {
  searchNodes = cli.loadSearchIndex(root);
}

async function runLintDiagnostics(root: string) {
  const findings = await cli.lint(root);

  // Group findings by node → file
  const byFile = new Map<string, vscode.Diagnostic[]>();

  for (const f of findings) {
    const filePath = cli.findNodeFile(f.nodeId, root);
    const uri = filePath ?? path.join(root, f.nodeId);

    const severity =
      f.severity === "ERROR"
        ? vscode.DiagnosticSeverity.Error
        : f.severity === "WARN"
          ? vscode.DiagnosticSeverity.Warning
          : vscode.DiagnosticSeverity.Information;

    const diag = new vscode.Diagnostic(
      new vscode.Range(0, 0, 0, 0),
      `${f.nodeId}: ${f.message}`,
      severity
    );
    diag.source = "sigil";

    const key = uri;
    if (!byFile.has(key)) {
      byFile.set(key, []);
    }
    byFile.get(key)!.push(diag);
  }

  diagnosticCollection.clear();
  for (const [filePath, diags] of byFile) {
    diagnosticCollection.set(vscode.Uri.file(filePath), diags);
  }

  const errors = findings.filter((f) => f.severity === "ERROR").length;
  const warns = findings.filter((f) => f.severity === "WARN").length;
  if (errors + warns === 0) {
    vscode.window.showInformationMessage("Sigil lint: all clear");
  } else {
    vscode.window.showWarningMessage(
      `Sigil lint: ${errors} error(s), ${warns} warning(s)`
    );
  }
}

async function pickNode(
  prompt: string
): Promise<string | undefined> {
  const items = searchNodes.map((n) => ({
    label: n.id,
    description: n.title,
    detail: `${n.type} — ${n.path}`,
  }));
  const picked = await vscode.window.showQuickPick(items, {
    placeHolder: prompt,
    matchOnDescription: true,
    matchOnDetail: true,
  });
  return picked?.label;
}

function renderImpactHtml(result: cli.ImpactResult): string {
  const rings = result.rings
    .map((ring) => {
      const nodes = ring.nodes
        .map(
          (n) =>
            `<li><strong>${n.id}</strong> <span class="type">${n.type}</span> <span class="edge">${n.direction === "out" ? "→" : "←"} ${n.edge_type}</span></li>`
        )
        .join("\n");
      return `<h3>Ring ${ring.depth} (${ring.nodes.length} nodes)</h3><ul>${nodes}</ul>`;
    })
    .join("\n");

  const summary = Object.entries(result.summary.by_type)
    .map(([t, c]) => `${t}: ${c}`)
    .join(", ");

  return `<!DOCTYPE html>
<html>
<head>
<style>
  body { font-family: var(--vscode-font-family); padding: 16px; color: var(--vscode-foreground); }
  h2 { border-bottom: 1px solid var(--vscode-panel-border); padding-bottom: 8px; }
  h3 { margin-top: 16px; }
  .type { color: var(--vscode-descriptionForeground); font-size: 0.9em; }
  .edge { color: var(--vscode-textLink-foreground); font-size: 0.9em; }
  .summary { margin-top: 16px; padding: 8px; background: var(--vscode-editor-inactiveSelectionBackground); border-radius: 4px; }
  ul { list-style: none; padding-left: 8px; }
  li { padding: 2px 0; }
</style>
</head>
<body>
  <h2>Impact: ${result.node.id} — ${result.node.title}</h2>
  <div class="summary">Total: ${result.summary.total} nodes (${summary})</div>
  ${rings}
</body>
</html>`;
}

export function deactivate() {}
