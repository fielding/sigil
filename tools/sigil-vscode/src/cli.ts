import * as vscode from "vscode";
import { execFile } from "child_process";
import * as path from "path";
import * as fs from "fs";

export interface LintFinding {
  severity: "ERROR" | "WARN" | "INFO";
  nodeId: string;
  message: string;
}

export interface SearchNode {
  id: string;
  type: string;
  title: string;
  path: string;
  aliases: string[];
}

export interface ImpactResult {
  node: { id: string; type: string; title: string; path: string };
  rings: Array<{
    depth: number;
    nodes: Array<{
      id: string;
      type: string;
      edge_type: string;
      direction: string;
    }>;
  }>;
  summary: { total: number; by_type: Record<string, number> };
}

function getExecutable(): string {
  return vscode.workspace
    .getConfiguration("sigil")
    .get<string>("executable", "sigil");
}

function run(
  args: string[],
  cwd: string
): Promise<{ stdout: string; stderr: string; code: number }> {
  const exe = getExecutable();
  return new Promise((resolve) => {
    execFile(exe, args, { cwd, maxBuffer: 10 * 1024 * 1024 }, (err: Error | null, stdout: string, stderr: string) => {
      resolve({ stdout: stdout ?? "", stderr: stderr ?? "", code: err ? 1 : 0 });
    });
  });
}

export async function lint(cwd: string): Promise<LintFinding[]> {
  const { stdout } = await run(["lint"], cwd);
  const findings: LintFinding[] = [];
  const re = /^(ERROR|WARN|INFO)\s+([\w-]+):\s+(.+)$/gm;
  let m: RegExpExecArray | null;
  while ((m = re.exec(stdout)) !== null) {
    findings.push({
      severity: m[1] as LintFinding["severity"],
      nodeId: m[2],
      message: m[3],
    });
  }
  return findings;
}

export async function fmt(cwd: string): Promise<string> {
  const { stdout } = await run(["fmt"], cwd);
  return stdout;
}

export async function index(cwd: string): Promise<void> {
  await run(["index"], cwd);
}

export async function impact(
  nodeId: string,
  cwd: string
): Promise<ImpactResult | null> {
  const { stdout, code } = await run(["impact", nodeId, "--json"], cwd);
  if (code !== 0) {
    return null;
  }
  try {
    return JSON.parse(stdout);
  } catch {
    return null;
  }
}

export async function newNode(
  type: string,
  args: string[],
  cwd: string
): Promise<string> {
  const { stdout, stderr } = await run(["new", type, ...args], cwd);
  return stdout || stderr;
}

export function loadSearchIndex(cwd: string): SearchNode[] {
  const indexPath = path.join(cwd, ".intent", "index", "search.json");
  try {
    const data = JSON.parse(fs.readFileSync(indexPath, "utf-8"));
    return data.nodes ?? [];
  } catch {
    return [];
  }
}

export function findNodeFile(
  nodeId: string,
  cwd: string
): string | undefined {
  const nodes = loadSearchIndex(cwd);
  const node = nodes.find(
    (n) => n.id.toLowerCase() === nodeId.toLowerCase()
  );
  return node?.path ? path.join(cwd, node.path) : undefined;
}
