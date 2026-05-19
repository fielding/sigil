#!/usr/bin/env node
import { copyFileSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = dirname(fileURLToPath(import.meta.url));
const repoRoot = resolve(scriptDir, "..");
const libDir = join(scriptDir, "lib");

function copyRequired(source, destination, label) {
  if (!existsSync(source)) {
    throw new Error(`${label} missing: ${source}`);
  }
  mkdirSync(dirname(destination), { recursive: true });
  copyFileSync(source, destination);
  console.log(`Copied ${label} to ${destination}`);
}

mkdirSync(libDir, { recursive: true });
copyRequired(
  join(repoRoot, "tools", "intent", "sigil.py"),
  join(libDir, "sigil.py"),
  "sigil.py",
);
copyRequired(
  join(repoRoot, "tools", "intent_viewer", "index.html"),
  join(libDir, "sigil_viewer.html"),
  "intent_viewer",
);

const demoSourceDir = join(repoRoot, "examples", "demo-app", ".intent", "index");
const demoDestDir = join(libDir, "demo_index");
rmSync(demoDestDir, { recursive: true, force: true });
mkdirSync(demoDestDir, { recursive: true });

if (!existsSync(demoSourceDir)) {
  console.warn(`Demo intent index not present at ${demoSourceDir}; packaged CLI will omit demo_index fixtures.`);
} else {
  const copied = readdirSync(demoSourceDir)
    .filter((name) => name.endsWith(".json"))
    .sort();
  for (const name of copied) {
    copyFileSync(join(demoSourceDir, name), join(demoDestDir, name));
  }
  console.log(`Copied ${copied.length} demo index JSON files to ${demoDestDir}`);
}
