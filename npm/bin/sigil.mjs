#!/usr/bin/env node

import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const scriptPath = resolve(__dirname, "..", "lib", "sigil.py");

// Find a suitable Python 3 interpreter
function findPython() {
  const candidates = ["python3", "python"];
  for (const cmd of candidates) {
    try {
      const version = execFileSync(cmd, ["--version"], {
        encoding: "utf-8",
        stdio: ["pipe", "pipe", "pipe"],
      }).trim();
      const match = version.match(/Python (\d+)\.(\d+)/);
      if (match && (parseInt(match[1]) > 3 || (parseInt(match[1]) === 3 && parseInt(match[2]) >= 11))) {
        return cmd;
      }
    } catch {
      // not found, try next
    }
  }
  return null;
}

// Check for pyyaml
function checkYaml(python) {
  try {
    execFileSync(python, ["-c", "import yaml"], {
      stdio: ["pipe", "pipe", "pipe"],
    });
    return true;
  } catch {
    return false;
  }
}

const python = findPython();

if (!python) {
  console.error("Error: Python 3.11+ is required but not found on PATH.");
  console.error("Install Python from https://python.org or via your package manager.");
  process.exit(1);
}

if (!checkYaml(python)) {
  console.error("Error: pyyaml is required. Install it with:");
  console.error(`  ${python} -m pip install pyyaml`);
  process.exit(1);
}

if (!existsSync(scriptPath)) {
  console.error("Error: sigil.py not found at", scriptPath);
  process.exit(1);
}

// Forward all args to the Python script
const args = process.argv.slice(2);

try {
  execFileSync(python, [scriptPath, ...args], {
    stdio: "inherit",
    env: { ...process.env, SIGIL_NPX: "1" },
  });
} catch (err) {
  process.exit(err.status ?? 1);
}
