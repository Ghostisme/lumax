/**
 * Monorepo: Next.js 只自动加载 `frontend/.env*`，不加载仓库根目录 `.env`。
 * 在 `import "./src/env.js"` 之前执行，用根目录中「尚未在 process.env 中出现」的键补全
 *（不覆盖已存在的键，故 `frontend/.env` / `.env.local` 仍优先）。
 */
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const rootEnvPath = path.join(__dirname, "..", ".env");

function parseLine(line) {
  const trimmed = line.trim();
  if (!trimmed || trimmed.startsWith("#")) {
    return null;
  }
  const eq = trimmed.indexOf("=");
  if (eq <= 0) {
    return null;
  }
  const key = trimmed.slice(0, eq).trim();
  let value = trimmed.slice(eq + 1).trim();
  if (
    (value.startsWith('"') && value.endsWith('"')) ||
    (value.startsWith("'") && value.endsWith("'"))
  ) {
    value = value.slice(1, -1);
  }
  return { key, value };
}

if (fs.existsSync(rootEnvPath)) {
  const text = fs.readFileSync(rootEnvPath, "utf8");
  for (const line of text.split("\n")) {
    const parsed = parseLine(line);
    if (!parsed) {
      continue;
    }
    if (process.env[parsed.key] === undefined) {
      process.env[parsed.key] = parsed.value;
    }
  }
}
