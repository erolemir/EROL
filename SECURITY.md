# Security policy

Report vulnerabilities privately using GitHub's
[Report a vulnerability](https://github.com/erolemir/EROL/security/advisories/new)
form. Include reproduction steps with synthetic inputs.
Do not post credentials or private project memory in public issues.

EROL stores local sanitized evidence outside the project. Before persistence it scans
structured credential fields, common keys/tokens/headers/private keys, credentialed
URLs and high-entropy values. Suspected secrets fail closed with no payload in error
output. Heuristics can miss unusual encodings and can reject benign examples. Sanitize
inputs before ingestion. No encryption at rest is provided; protect your user account,
disk and backups. Fresh POSIX project state uses private directories and database files.
Windows inherits the current user's filesystem ACLs; EROL does not rewrite ACLs.
Provider-prefixed credential labels such as AWS_SECRET_ACCESS_KEY and STRIPE_KEY
are rejected even for short or numeric values. Environment-variable references
are allowed; settings store names rather than API credential values.

Detected project root paths use a dedicated filesystem check: known credential
patterns scan the whole path, while entropy scans each path component. Combining
ordinary POSIX path components would otherwise resemble a long base64 secret.
All other metadata, arbitrary memory input and credential fields retain full-value
scanning. A credential encoded across path separators may evade entropy heuristics;
never put credentials in directory names or rely on heuristics as complete detection.

Memory is untrusted reference material. It cannot override higher-priority instructions.
Secret and unsafe-instruction scanners do not establish sandbox containment or complete
prompt-injection protection. Advisory plans do not execute scripts or model calls.
Explicit execution modes can run native tools, API workspace commands and checks.
Third-party skill installation and global auto-promotion are unsupported in this release.

SQLite writes are parameterized and lifecycle gates transactional. Inputs are bounded;
paths reject traversal, symlinks and Windows reparse points. Installer ownership is
tracked separately, backups are outside the repo, and user edits cause conflicts.
This is a trusted local-user tool, not safe against a malicious concurrent OS user
mutating the same directories during a filesystem operation.

Check manifests require external authorization bound to the original project root
and canonical contents; repository data cannot approve itself. Commands use a
small environment allowlist, with optional reviewed public names and no interpreter
startup injection variables. An optional executor argv prefix can invoke a separately
configured sandbox or OS account. Default commands still retain caller permissions;
approval, worktrees and environment minimization do not establish OS containment.
Manifest digests do not attest executable/source/dependency contents. See
[check authorization](docs/execution.md#check-authorization-and-command-environment).

The loopback panel authenticates evidence API reads with an ephemeral per-server
bearer before accessing storage. Keep its bootstrap fragment link private. Tokens
are removed from browser history and held in JavaScript memory; refreshing requires
the original link. This is HTTP access control, not same-account process isolation.

Caller-provided test/review reports remain local attestations: required fields,
reviewer independence, digests and blocking findings are checked, but the engine
cannot prove an external test ran. Execution modes separately record directly
observed command outputs; model reviews are still assertions rather than authenticated
human audits. Do not treat static checks as behavioral success or containment proof.

There is no remote telemetry. Explicitly configured native/API model execution sends
task context to the selected provider; native clients retain their own account/session
policies. API keys are read from configured environment variables. Research execution
can fetch public sources. These opt-in modes use the network during normal operation;
memory, credentials and raw conversations must not be copied into the repository.
