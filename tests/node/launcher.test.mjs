import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { EventEmitter } from 'node:events';
import { existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, resolve } from 'node:path';
import test from 'node:test';
import { findPython, pythonCandidates, runCli, runtimeRoot } from '../../bin/erol.mjs';

const GOOD_PROBE = () => ({ status: 0, stdout: '[3,11,0]\n' });

function fakeOptions() {
  const messages = [];
  const child = new EventEmitter();
  const signals = new EventEmitter();
  const calls = [];
  child.kill = (signal) => { calls.push(['kill', signal]); return true; };
  return {
    env: {
      EROL_PYTHON: 'Python With Spaces/python', PYTHONPATH: '/existing/runtime',
      EROL_LAUNCHER: '/untrusted/inherited-launcher.mjs',
    },
    cwd: '/caller/project', launcherPath: '/package/bin/erol.mjs',
    probe: GOOD_PROBE, exists: () => true,
    stderr: { write: (message) => messages.push(message) }, signals,
    spawnChild: (...args) => { calls.push(args); return child; },
    child, calls, messages,
  };
}

test('platform probes are bounded and explicit executable paths never split into commands', () => {
  assert.deepEqual(pythonCandidates({}, 'win32'), [
    { command: 'py', prefix: ['-3'] }, { command: 'python', prefix: [] },
  ]);
  assert.deepEqual(pythonCandidates({}, 'linux'), [
    { command: 'python3', prefix: [] }, { command: 'python', prefix: [] },
  ]);
  assert.deepEqual(pythonCandidates({ EROL_PYTHON: '/space dir/python' }, 'linux'), [
    { command: '/space dir/python', prefix: [] },
  ]);
});

test('Python probe rejects old, failed, malformed, or unavailable executables without leaking errors', () => {
  const calls = [];
  const selected = findPython({ env: {}, platform: 'win32', probe: (command, args, options) => {
    calls.push({ command, args, options });
    return command === 'py' ? { status: 0, stdout: '[3,10,9]' } : GOOD_PROBE();
  } });
  assert.equal(selected.command, 'python');
  assert.equal(calls[0].args[0], '-3');
  assert.equal(calls[0].args[1], '-I');
  assert.equal(calls[0].args[2], '-S');
  assert.equal(calls[0].options.shell, false);
  assert.equal(calls[0].options.windowsHide, true);
  for (const result of [
    { status: 1, stdout: '[3,11,0]' }, { status: 0, stdout: 'not JSON' },
    { status: 0, stdout: '["3",11,0]' }, { error: new Error('private path'), status: 0 },
  ]) {
    assert.equal(findPython({ env: { EROL_PYTHON: 'explicit' }, probe: () => result }), null);
  }
  assert.equal(findPython({ env: {}, probe: () => { throw new Error('sensitive'); } }), null);
});

test('runtime discovery uses only package and copied-plugin siblings', () => {
  const packagePath = resolve('/package/bin/erol.mjs');
  assert.equal(runtimeRoot(packagePath, (p) => p === resolve('/package/src/erol/__main__.py')),
    resolve('/package/src'));
  const pluginPath = resolve('/plugin/scripts/erol.mjs');
  assert.equal(runtimeRoot(pluginPath, (p) => p === resolve('/plugin/runtime/erol/__main__.py')),
    resolve('/plugin/runtime'));
  assert.equal(runtimeRoot(packagePath, () => false), null);
});

test('launcher preserves argument boundaries, cwd, environment, and child exit status without a shell', async () => {
  const options = fakeOptions();
  const args = ['--task', 'quotes " ; & $(literal)', '--project', '/space dir/repo'];
  const running = runCli(args, options);
  const [command, forwarded, config] = options.calls[0];
  assert.equal(command, options.env.EROL_PYTHON);
  assert.deepEqual(forwarded.slice(0, 5), ['-I', '-S', '-X', 'utf8', '-c']);
  assert.match(forwarded[5], /runpy\.run_module\("erol"/);
  assert.equal(forwarded[6], resolve('/package/src'));
  assert.deepEqual(forwarded.slice(7), args);
  assert.equal(config.cwd, options.cwd);
  assert.equal(config.shell, false);
  assert.equal(config.stdio, 'inherit');
  assert.equal(config.windowsHide, true);
  assert.equal(config.env.PYTHONPATH, resolve('/package/src'));
  assert.equal(config.env.EROL_LAUNCHER, resolve('/package/bin/erol.mjs'));
  assert.equal(options.env.PYTHONPATH, '/existing/runtime');
  options.child.emit('close', 7, null);
  assert.equal(await running, 7);
  assert.equal(options.signals.listenerCount('SIGINT'), 0);
  assert.equal(options.signals.listenerCount('SIGTERM'), 0);
});

test('Windows py prefix is retained for the actual invocation', async () => {
  const options = { ...fakeOptions(), platform: 'win32', env: {} };
  const running = runCli(['--version'], options);
  assert.equal(options.calls[0][0], 'py');
  assert.deepEqual(options.calls[0][1].slice(0, 6), ['-3', '-I', '-S', '-X', 'utf8', '-c']);
  assert.equal(options.calls[0][1].at(-1), '--version');
  options.child.emit('close', 0, null);
  assert.equal(await running, 0);
});

test('capability errors are actionable and omit interpreter paths, raw args, and underlying errors', async () => {
  const options = fakeOptions();
  options.probe = () => ({ status: 1, stdout: 'sensitive probe output' });
  assert.equal(await runCli(['private-task-content'], options), 1);
  assert.equal(options.calls.length, 0);
  assert.match(options.messages.join(''), /Python 3\.11/);
  assert.doesNotMatch(options.messages.join(''), /private-task-content|sensitive|Python With Spaces/);

  const missing = { ...fakeOptions(), exists: () => false };
  assert.equal(await runCli(['private-task-content'], missing), 1);
  assert.match(missing.messages.join(''), /bundled runtime/);
});

test('spawn failures report a fixed message and clean up signal listeners', async () => {
  const options = fakeOptions();
  const running = runCli(['private-task-content'], options);
  options.child.emit('error', new Error('private-task-content and sensitive path'));
  options.child.emit('close', 1, null);
  assert.equal(await running, 1);
  assert.equal(options.signals.listenerCount('SIGINT'), 0);
  assert.equal(options.signals.listenerCount('SIGTERM'), 0);
  assert.match(options.messages.join(''), /could not start/);
  assert.doesNotMatch(options.messages.join(''), /private-task-content|sensitive/);

  const thrown = { ...fakeOptions(), spawnChild: () => { throw new Error('sensitive'); } };
  assert.equal(await runCli([], thrown), 1);
  assert.doesNotMatch(thrown.messages.join(''), /sensitive/);
});

test('signals are forwarded and signal termination returns a failure status', async () => {
  const options = fakeOptions();
  const running = runCli([], options);
  options.signals.emit('SIGTERM');
  assert.deepEqual(options.calls[1], ['kill', 'SIGTERM']);
  options.child.emit('close', null, 'SIGTERM');
  assert.equal(await running, 143);
  assert.equal(options.signals.listenerCount('SIGTERM'), 0);
});

test('real bundled CLI preserves cwd and quoted task data even with a conflicting project erol.py', (t) => {
  if (!findPython()) return t.skip('Python 3.11+ unavailable for real CLI smoke test');
  const directory = mkdtempSync(join(tmpdir(), 'erol-node-test-'));
  try {
    const project = join(directory, 'project with spaces');
    const home = join(directory, 'external state');
    mkdirSync(project);
    writeFileSync(join(project, 'erol.py'), 'raise RuntimeError("project module shadowed runtime")\n');
    writeFileSync(join(project, 'json.py'), 'raise RuntimeError("project module shadowed probe")\n');
    writeFileSync(join(project, 'sitecustomize.py'), 'raise RuntimeError("ambient site customization executed")\n');
    const hostileEnv = {
      ...process.env, PYTHONPATH: '.', PYTHONHOME: project, PYTHONUSERBASE: project,
      PYTHONSTARTUP: join(project, 'sitecustomize.py'), PYTHONINSPECT: '1',
    };
    const task = 'Handle "quoted" data ; & $(literal)\nTürkçe satır';
    const result = spawnSync(process.execPath, [resolve('bin/erol.mjs'), '--project', '.',
      '--home', home, 'plan', '--task', task], {
      cwd: project, env: hostileEnv, shell: false, encoding: 'utf8', timeout: 15000,
    });
    assert.equal(result.status, 0, result.stderr);
    assert.equal(result.stderr, '');
    const plan = JSON.parse(result.stdout);
    assert.equal(plan.task, task);
    assert.equal(plan.context.packet.task, task);
    assert.equal(plan.execution_supported, false);
    const setup = spawnSync(process.execPath, [resolve('bin/erol.mjs'), '--project', '.',
      '--home', home, 'setup', '--harness', 'codex', '--apply'], {
      cwd: project, env: hostileEnv, shell: false, encoding: 'utf8', timeout: 15000,
    });
    assert.equal(setup.status, 0, setup.stderr);
    assert.equal(setup.stderr, '');
    assert.equal(existsSync(join(project, '.agents', 'skills', 'erol', 'SKILL.md')), true);
    assert.match(readFileSync(join(project, 'AGENTS.md'), 'utf8'), /EROL:BEGIN/);
    const invalid = spawnSync(process.execPath, [resolve('bin/erol.mjs'), 'unknown-command'], {
      cwd: project, env: hostileEnv, shell: false, encoding: 'utf8', timeout: 15000,
    });
    assert.equal(invalid.status, 2);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test('npm metadata has zero dependencies and no install lifecycle hooks', () => {
  const manifest = JSON.parse(readFileSync(resolve('package.json'), 'utf8'));
  assert.equal(Object.keys(manifest.dependencies ?? {}).length, 0);
  assert.equal(Object.keys(manifest.devDependencies ?? {}).length, 0);
  for (const lifecycle of ['preinstall', 'install', 'postinstall', 'prepare', 'prepublishOnly']) {
    assert.equal(manifest.scripts?.[lifecycle], undefined);
  }
  assert.equal(manifest.bin.erol, 'bin/erol.mjs');
});
