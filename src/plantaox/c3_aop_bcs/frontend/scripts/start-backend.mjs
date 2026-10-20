import { existsSync } from "node:fs";
import { spawn } from "node:child_process";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const scriptDirectory = dirname(fileURLToPath(import.meta.url));
const repositoryRoot = resolve(scriptDirectory, "../../../../../");
const windowsPython = join(repositoryRoot, ".venv", "Scripts", "python.exe");
const unixPython = join(repositoryRoot, ".venv", "bin", "python");
const python = existsSync(windowsPython) ? windowsPython : existsSync(unixPython) ? unixPython : "python";
const port = process.env.C3_FRONTEND_PORT ?? "4313";

const child = spawn(python, [
  "-m", "uvicorn",
  "plantaox.c3_aop_bcs.dashboard_backend:app",
  "--app-dir", join(repositoryRoot, "src"),
  "--host", "127.0.0.1",
  "--port", port,
], {
  cwd: repositoryRoot,
  stdio: "inherit",
  env: { ...process.env, OPENBLAS_NUM_THREADS: process.env.OPENBLAS_NUM_THREADS ?? "1" },
});

child.on("error", (error) => {
  console.error(`Could not start the C3 backend with ${python}: ${error.message}`);
  process.exitCode = 1;
});

child.on("exit", (code, signal) => {
  if (signal) console.log(`C3 backend stopped by ${signal}.`);
  process.exitCode = code ?? 0;
});

for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
