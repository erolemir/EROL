# Releases and updates

The public repository is [erolemir/EROL](https://github.com/erolemir/EROL).
Contributions use forks and pull requests. CODEOWNERS requires @erolemir to approve
outside changes. All six OS/Python CI jobs must pass the `Quality gate` check.
New reviewable commits dismiss old approvals; review threads must be resolved.
Main cannot be force-pushed or deleted. Only the owner can bypass the review rule
through a pull request to merge their own work; passing CI is still required.
No contributors receive direct push access. Repository ownership still gives the
owner the ability to change these settings; no hosting setting can remove that authority.

After successful validation of the latest `main` push, the release workflow:

1. Selects a monotonic patch version from existing `vX.Y.Z` tags and the source
   version floor. A deliberate higher source major/minor version starts that series.
2. Regenerates the bundled runtime and manifests with the same package version.
3. Tests the versioned packages again and builds wheel, sdist and npm archive.
4. Publishes a new commit to `stable`, an immutable version tag, and GitHub release
   assets with checksums and `RELEASE.json` linking the exact validated source commit.

The bot never commits or pushes to `main`. `stable` is generated distribution code;
its version may be higher than the development version in `main`. Its history is
fast-forward only. Releases are serialized and superseded validation runs are skipped.
Fork PR workflows have read-only tokens. Publication requires a successful `push`
validation run from this repository's `main`, not a pull request run.
If publication fails, inspect the Actions run and rerun it after fixing the cause.
There is no npm/PyPI registry upload in this workflow.

Install from the moving `stable` ref to receive tested releases. A fixed `vX.Y.Z`
ref stays pinned. A marketplace registered from a local path stays local; GitHub
changes cannot refresh that checkout automatically.

```console
codex plugin marketplace add erolemir/EROL --ref stable
codex plugin add erol@erol
claude plugin marketplace add https://github.com/erolemir/EROL.git#stable
claude plugin install erol@erol
```

If a local `erol` marketplace already exists, remove only that marketplace before
adding the Git source. Claude removal uninstalls its EROL plugin, so reinstall it
afterward. EROL project memory is outside those plugin directories and is retained.

Manual refresh:

```console
codex plugin marketplace upgrade erol
codex plugin add erol@erol
claude plugin marketplace update erol
claude plugin update erol@erol
```

Claude has a native auto-update toggle: `/plugin` → Marketplaces → erol → Enable
auto-update. Third-party marketplaces default to auto-update off. Running sessions
retain their loaded versions; reload plugins where supported or start a new session.
See [Claude's update documentation](https://code.claude.com/docs/en/plugins/install#keep-plugins-updated)
and [Codex's marketplace commands](https://developers.openai.com/plugins/build/plugins).

For Windows, an optional updater runs those native refresh commands at login and
every six hours while the current user is signed in. It requires an already
installed Git marketplace, uses the user's ordinary permissions, and does not
change client authentication, execution policy or project memory. Run from this
checkout on **each** computer that should receive scheduled updates:

```powershell
./scripts/update-plugins.ps1 -Harness Both -Register
# Refresh now:
./scripts/update-plugins.ps1 -Harness Both
# Stop scheduled refreshes:
./scripts/update-plugins.ps1 -Unregister
```

The task is `EROL Plugin Updates`; its installed script and bounded logs are in
`%USERPROFILE%/.erol/updater`. This avoids application-specific AppData
virtualization hiding the script from Task Scheduler. Project databases remain
in the separate `~/.erol/state` directory. A failed refresh is recorded and retains the installed
version. The task cannot refresh a computer that is offline, signed out or missing
its native client. Registration saves discovered CLI paths as a fallback when
the login shell does not inherit the assistant's PATH; register again if those
executables move. Other platforms can use the native manual refresh or Claude's
auto-update setting. Updates become effective in a new/reloaded client session.

## License

EROL is AGPL-3.0-only. Anyone may use, copy, modify and redistribute it under that
license. Preserve required notices and provide source as required, including the
AGPL network-source provision for modified versions. It does not forbid copying
or guarantee exclusive ownership of ideas. This choice keeps covered derivatives
open while allowing community contributions. The full terms are in [LICENSE](../LICENSE).
