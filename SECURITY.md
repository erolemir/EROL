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

Memory is untrusted reference material. It cannot override higher-priority instructions.
Secret and unsafe-instruction scanners do not establish sandbox containment or complete
prompt-injection protection. Generated scripts are never executed by the engine.
Third-party skill installation and global auto-promotion are unsupported in this release.

SQLite writes are parameterized and lifecycle gates transactional. Inputs are bounded;
paths reject traversal, symlinks and Windows reparse points. Installer ownership is
tracked separately, backups are outside the repo, and user edits cause conflicts.
This is a trusted local-user tool, not safe against a malicious concurrent OS user
mutating the same directories during a filesystem operation.

All test and behavior reports are caller-provided attestations. EROL checks required
fields, reviewer independence, digest consistency and blocking findings. It cannot
authenticate the reviewer or prove an external test actually ran. Production integration
must obtain evidence through its trusted harness/check runner.

No remote telemetry, prompt upload, model credentials or generated-command execution
are part of the runtime. Dev dependency installation and documentation research use
the network only during development, not normal EROL operation.
