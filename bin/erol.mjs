#!/usr/bin/env node
/** Zero-dependency Node entrypoint for the bundled Python stdlib core. */
import { spawn, spawnSync } from 'node:child_process';
import { existsSync, realpathSync } from 'node:fs';
import { constants } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const LAUNCHER_PATH = fileURLToPath(import.meta.url);
const PYTHON_PROBE = 'import json,sys; print(json.dumps(list(sys.version_info[:3])))';
const PYTHON_BOOTSTRAP = 'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_module("erol",run_name="__main__",alter_sys=True)';
const MISSING_PYTHON = 'EROL requires Python 3.11 or newer. Install Python or set EROL_PYTHON to its executable path. No Python packages are required.\n';
const MISSING_RUNTIME = 'EROL could not find its bundled runtime. Reinstall the package or regenerate the plugin bundle.\n';
const LAUNCH_FAILED = 'EROL could not start its Python runtime. Check the Python installation and executable permissions.\n';

export function pythonCandidates(env = process.env, platform = process.platform) {
  if (env.EROL_PYTHON) return [{ command: env.EROL_PYTHON, prefix: [] }];
  return platform === 'win32'
    ? [{ command: 'py', prefix: ['-3'] }, { command: 'python', prefix: [] }]
    : [{ command: 'python3', prefix: [] }, { command: 'python', prefix: [] }];
}

export function findPython({ env = process.env, platform = process.platform, probe = spawnSync } = {}) {
  for (const candidate of pythonCandidates(env, platform)) {
    try {
      // Probe in Python isolated mode so repository json.py/site customization
      // cannot execute while we are merely checking the interpreter version.
      const result = probe(candidate.command, [...candidate.prefix, '-I', '-S', '-c', PYTHON_PROBE], {
        shell: false, windowsHide: true, encoding: 'utf8', timeout: 5000,
        maxBuffer: 8192, env, stdio: ['ignore', 'pipe', 'ignore'],
      });
      if (result.error || result.status !== 0) continue;
      const version = JSON.parse(result.stdout.trim());
      if (Array.isArray(version) && version.length === 3 && version.every(Number.isInteger)
          && (version[0] > 3 || (version[0] === 3 && version[1] >= 11))) {
        return candidate;
      }
    } catch {
      // Probe diagnostics can contain paths or environment secrets. Report only
      // the actionable capability message after every supported probe fails.
    }
  }
  return null;
}

export function runtimeRoot(launcherPath = LAUNCHER_PATH, exists = existsSync) {
  const parent = resolve(dirname(dirname(launcherPath)));
  for (const root of [join(parent, 'src'), join(parent, 'runtime')]) {
    if (exists(join(root, 'erol', '__main__.py'))) return root;
  }
  return null;
}

export async function runCli(args = process.argv.slice(2), options = {}) {
  const env = options.env ?? process.env;
  const cwd = options.cwd ?? process.cwd();
  const platform = options.platform ?? process.platform;
  const stderr = options.stderr ?? process.stderr;
  const signals = options.signals ?? process;
  const python = findPython({ env, platform, probe: options.probe ?? spawnSync });
  if (!python) {
    stderr.write(MISSING_PYTHON);
    return 1;
  }
  const root = runtimeRoot(options.launcherPath ?? LAUNCHER_PATH, options.exists ?? existsSync);
  if (!root) {
    stderr.write(MISSING_RUNTIME);
    return 1;
  }
  const childEnv = {
    ...env,
    PYTHONPATH: root,
    EROL_LAUNCHER: resolve(options.launcherPath ?? LAUNCHER_PATH),
    PYTHONUTF8: '1',
    PYTHONIOENCODING: 'utf-8',
  };
  const spawnChild = options.spawnChild ?? spawn;
  return new Promise((done) => {
    let child;
    try {
      // Isolated mode ignores ambient PYTHONPATH/PYTHONHOME/user-site settings.
      // -S disables site initialization; the stdlib-only core needs none. The
      // fixed bootstrap admits exactly our runtime via a separate argv value.
      child = spawnChild(python.command, [...python.prefix, '-I', '-S', '-X', 'utf8', '-c', PYTHON_BOOTSTRAP, root, ...args], {
        cwd, env: childEnv, stdio: 'inherit', shell: false, windowsHide: true,
      });
    } catch {
      stderr.write(LAUNCH_FAILED);
      done(1);
      return;
    }
    const handlers = new Map();
    let finished = false;
    const complete = (code) => {
      if (finished) return;
      finished = true;
      for (const [signal, handler] of handlers) signals.removeListener(signal, handler);
      done(code);
    };
    for (const signal of ['SIGINT', 'SIGTERM']) {
      const handler = () => {
        try { child.kill(signal); } catch { /* Process may already have exited. */ }
      };
      handlers.set(signal, handler);
      signals.on(signal, handler);
    }
    child.once('error', () => {
      stderr.write(LAUNCH_FAILED);
      complete(1);
    });
    child.once('close', (code, signal) => {
      complete(Number.isInteger(code) ? code : 128 + (constants.signals[signal] ?? 1));
    });
  });
}

let directlyInvoked = false;
try {
  directlyInvoked = Boolean(process.argv[1]) && realpathSync(resolve(process.argv[1])) === realpathSync(LAUNCHER_PATH);
} catch { /* Importing the module has no execution side effects. */ }
if (directlyInvoked) {
  try {
    process.exitCode = await runCli();
  } catch {
    process.stderr.write(LAUNCH_FAILED);
    process.exitCode = 1;
  }
}
