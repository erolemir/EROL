import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import test from 'node:test';
import vm from 'node:vm';

const source = await readFile(new URL('../../src/erol/panel.py', import.meta.url), 'utf8');
const script = source.match(/JS = """([\s\S]*?)"""/)[1];

class Element {
  constructor(tag) {
    this.tag = tag;
    this.children = [];
    this.value = '';
    this.text = '';
    this.classList = { toggle() {} };
  }
  set textContent(value) { this.text = String(value); this.children = []; }
  get textContent() { return this.text + this.children.map(c => c.textContent).join(' '); }
  set innerHTML(_) { throw new Error('Evidence must never be interpreted as HTML'); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; this.text = ''; }
}

test('panel filters, expands observed evidence, switches tabs and renders untrusted text literally', async () => {
  const elements = Object.fromEntries(
    ['stats', 'items', 'query', 'status', 'runs', 'jobs', 'benchmarks', 'connection']
      .map(id => [id, new Element('div')])
  );
  const data = {
    runs: [{ id: 'run-one', status: 'completed', phase: 'finalize', harness: 'codex',
      review_summary: '<img src=x onerror="steal()">',
      checks: [{ name: 'behavior', passed: true, evidence_type: 'runner_observed' }],
      source_access_receipts: [{ source_id: 'S1', status: 'accessed', evidence_type: 'runner_observed_source_access' }],
      cost_usd: null, usage: { input_tokens: 42 }, findings: [] }],
    jobs: [{ id: 'job-one', status: 'queued' }],
    benchmarks: [{ id: 'benchmark-one', status: 'completed', pairs: 1 }],
  };
  const context = vm.createContext({
    document: { getElementById: id => elements[id], createElement: tag => new Element(tag) },
    fetch: async () => ({ ok: true, json: async () => data }),
    setInterval() {},
  });
  vm.runInContext(script, context);
  await new Promise(resolve => setImmediate(resolve));
  assert.match(elements.connection.textContent, /Yerel/);
  assert.equal(elements.items.children.length, 1);
  elements.items.children[0].children[0].onclick();
  assert.match(elements.items.textContent, /runner_observed_source_access/);
  assert.match(elements.items.textContent, /<img src=x/);
  assert.match(elements.items.textContent, /input_tokens/);
  elements.status.value = 'needs_attention';
  elements.status.onchange();
  assert.match(elements.items.textContent, /kayıt yok/);
  elements.status.value = '';
  elements.jobs.onclick();
  assert.match(elements.items.textContent, /job-one/);
  elements.query.value = 'missing';
  elements.query.oninput();
  assert.match(elements.items.textContent, /kayıt yok/);
  elements.query.value = '';
  elements.benchmarks.onclick();
  assert.match(elements.items.textContent, /benchmark-one/);
});

test('panel reports an unavailable evidence endpoint without inventing state', async () => {
  const elements = Object.fromEntries(
    ['stats', 'items', 'query', 'status', 'runs', 'jobs', 'benchmarks', 'connection']
      .map(id => [id, new Element('div')])
  );
  vm.runInNewContext(script, {
    document: { getElementById: id => elements[id], createElement: tag => new Element(tag) },
    fetch: async () => ({ ok: false }), setInterval() {},
  });
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(elements.connection.textContent, 'Bağlantı bekleniyor');
  assert.equal(elements.items.children.length, 0);
});
