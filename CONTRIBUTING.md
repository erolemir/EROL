# Contributing

Fork the repository and open a pull request against `main`. All files are owned
by @erolemir for review. Outside contributions require that owner's approval,
resolved review conversations and passing CI. New commits dismiss stale approvals.
Contributors are not granted direct push access. Do not change `stable` or release
tags: the release workflow generates those from validated `main` commits.

Contributions are licensed under AGPL-3.0-only, the same license as the project.
Preserve copyright and license notices. See [release and update rules](docs/releases.md).

Use Python 3.11+ in an isolated environment and Node.js 18+ for launcher changes.
Install `-e . -r requirements-dev.txt`, run
the tests, static checks, pack eval, adapter drift check and build listed in README.
Do not commit local memory, credentials, transcripts or generated user configuration.

Keep canonical core behavior independent of harnesses. Change adapters through their
generator and run `python scripts/check_adapter_drift.py --write`, then `--check`.
The same generator bundles canonical Python modules and the Node launcher into
the plugin. Never edit generated runtime copies directly. Run `npm test` for
launcher behavior and `npm pack --dry-run` to inspect the publication allowlist.
New skills need positive and negative routing fixtures, explicit verification guidance,
bounded context and security checks. Static routing tests are not behavior evals.

For lifecycle changes, add meaningful adversarial cases: replay, concurrency, scope,
stale evidence, revision drift, negative triggers or failure recovery. Update the
living plan and capability matrix with honest limitations and official source links.
Avoid superficial skill multiplication and unsupported harness settings.
