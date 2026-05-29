import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const DEFAULT_API_URL = 'http://127.0.0.1:8000';
const DEFAULT_FRONTEND_HOST = '127.0.0.1';
const DEFAULT_FRONTEND_PORT = '3000';
const STARTUP_TIMEOUT_MS = 120_000;

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const defaultFrontendDir = path.resolve(scriptDir, '..');

function normalizeUrl(value) {
  return (value || DEFAULT_API_URL).replace(/\/+$/, '');
}

function resolvePython(repoRoot, platform) {
  const venvPython = platform === 'win32'
    ? path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
    : path.join(repoRoot, '.venv', 'bin', 'python');

  return existsSync(venvPython) ? venvPython : 'python';
}

function parseBackendTarget(apiUrl) {
  const parsed = new URL(apiUrl);
  return {
    host: parsed.hostname || '127.0.0.1',
    port: Number(parsed.port || (parsed.protocol === 'https:' ? 443 : 80)),
  };
}

export function createDevPlan({
  frontendDir = defaultFrontendDir,
  env = process.env,
  platform = process.platform,
  nodePath = process.execPath,
} = {}) {
  const repoRoot = path.resolve(frontendDir, '..');
  const apiUrl = normalizeUrl(env.NEXT_PUBLIC_DATAVERSE_API_URL);
  const nextBin = path.join(frontendDir, 'node_modules', 'next', 'dist', 'bin', 'next');

  return {
    apiUrl,
    backendTarget: parseBackendTarget(apiUrl),
    backend: {
      command: resolvePython(repoRoot, platform),
      args: [
        '-m',
        'uvicorn',
        'app.main:app',
        '--app-dir',
        'dataverse_backend',
        '--host',
        '127.0.0.1',
        '--port',
        '8000',
        '--reload',
        '--reload-dir',
        'dataverse_backend',
      ],
      cwd: repoRoot,
    },
    frontend: {
      command: nodePath,
      args: [
        nextBin,
        'dev',
        '--hostname',
        env.NEXT_FRONTEND_HOST || DEFAULT_FRONTEND_HOST,
        '--port',
        env.NEXT_FRONTEND_PORT || DEFAULT_FRONTEND_PORT,
      ],
      cwd: frontendDir,
    },
  };
}

function isPortOpen(host, port) {
  return new Promise((resolve) => {
    const socket = net.createConnection({ host, port });
    socket.setTimeout(1_000);
    socket.once('connect', () => {
      socket.destroy();
      resolve(true);
    });
    socket.once('timeout', () => {
      socket.destroy();
      resolve(false);
    });
    socket.once('error', () => resolve(false));
  });
}

async function waitForPort(host, port, timeoutMs) {
  const startedAt = Date.now();
  while (Date.now() - startedAt < timeoutMs) {
    if (await isPortOpen(host, port)) {
      return true;
    }
    await new Promise((resolve) => setTimeout(resolve, 1_000));
  }
  return false;
}

function startProcess(label, processPlan, env = process.env) {
  const child = spawn(processPlan.command, processPlan.args, {
    cwd: processPlan.cwd,
    env,
    stdio: 'inherit',
    shell: false,
    windowsHide: false,
  });

  child.once('exit', (code, signal) => {
    if (code !== 0 && signal !== 'SIGTERM') {
      console.error(`[dev] ${label} exited with code ${code ?? signal}`);
    }
  });

  return child;
}

export function isMainModule(moduleUrl, argvPath) {
  return Boolean(argvPath) && moduleUrl === pathToFileURL(argvPath).href;
}

export function shouldReuseBackend(env = process.env) {
  const value = String(env.DATAVERSE_REUSE_BACKEND || '').toLowerCase();
  return value === '1' || value === 'true';
}

async function main() {
  const plan = createDevPlan();
  const env = {
    ...process.env,
    NEXT_PUBLIC_DATAVERSE_API_URL: plan.apiUrl,
  };

  console.log(`[dev] Frontend API URL: ${plan.apiUrl}`);

  let backendProcess;
  const backendAlreadyRunning = await isPortOpen(plan.backendTarget.host, plan.backendTarget.port);
  if (backendAlreadyRunning) {
    if (!shouldReuseBackend(process.env)) {
      console.error(`[dev] Backend port ${plan.backendTarget.port} is already in use.`);
      console.error('[dev] Stop the existing backend so npm run dev can start a fresh reload-enabled backend.');
      console.error('[dev] To intentionally reuse an existing backend, set DATAVERSE_REUSE_BACKEND=1.');
      process.exit(1);
    }
    console.log(`[dev] Reusing existing backend on ${plan.apiUrl}`);
  } else {
    console.log('[dev] Starting FastAPI backend on http://127.0.0.1:8000');
    backendProcess = startProcess('backend', plan.backend, env);

    const backendReady = await waitForPort(
      plan.backendTarget.host,
      plan.backendTarget.port,
      STARTUP_TIMEOUT_MS,
    );

    if (!backendReady) {
      console.error('[dev] Backend did not become reachable within 120 seconds.');
      backendProcess.kill('SIGTERM');
      process.exit(1);
    }
  }

  console.log('[dev] Starting Next.js frontend on http://127.0.0.1:3000');
  const frontendProcess = startProcess('frontend', plan.frontend, env);

  const shutdown = (signal) => {
    frontendProcess.kill(signal);
    if (backendProcess) {
      backendProcess.kill(signal);
    }
  };

  process.once('SIGINT', shutdown);
  process.once('SIGTERM', shutdown);

  frontendProcess.once('exit', (code) => {
    if (backendProcess) {
      backendProcess.kill('SIGTERM');
    }
    process.exit(code ?? 0);
  });
}

if (isMainModule(import.meta.url, process.argv[1])) {
  main().catch((error) => {
    console.error('[dev] Failed to start full stack dev environment');
    console.error(error);
    process.exit(1);
  });
}
