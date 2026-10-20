import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const frontendDirectory = resolve(scriptDirectory, "..");
const repositoryRoot = resolve(frontendDirectory, "..");
const windowsPython = join(repositoryRoot, ".venv", "Scripts", "python.exe");
const unixPython = join(repositoryRoot, ".venv", "bin", "python");
const python = existsSync(windowsPython) ? windowsPython : existsSync(unixPython) ? unixPython : "python";
const vite = join(frontendDirectory, "node_modules", "vite", "bin", "vite.js");

const environment = Object.fromEntries(
  Object.entries(process.env).filter(([key, value]) => !key.startsWith("=") && typeof value === "string"),
);
environment.OPENBLAS_NUM_THREADS ??= "1";

const backend = spawn(
  python,
  ["-m", "uvicorn", "plantaox.c3_aop_bcs.dashboard_backend:app", "--app-dir", join(repositoryRoot, "src"), "--host", "127.0.0.1", "--port", "4314"],
  { cwd: repositoryRoot, stdio: "inherit", env: environment },
);
const frontend = spawn(
  process.execPath,
  [vite, "--host", "127.0.0.1", "--port", "3000", "--strictPort"],
  { cwd: frontendDirectory, stdio: "inherit", env: environment },
);
const children = [backend, frontend];
let stopping = false;

function stop(code = 0) {
  if (stopping) return;
  stopping = true;
  for (const child of children) if (!child.killed) child.kill();
  process.exitCode = code;
}

for (const child of children) {
  child.on("error", (error) => { console.error(error.message); stop(1); });
  child.on("exit", (code) => { if (!stopping && code !== 0) stop(code ?? 1); });
}
for (const signal of ["SIGINT", "SIGTERM"]) process.on(signal, () => stop(0));
