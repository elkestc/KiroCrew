# Upstream baseline

**Historical evidence only.** The host-connected Linux run caused the credential
incident. Do not repeat its launch procedure or repair scripts. Tests now require
the disposable offline launcher in [testing conventions](../system-specs/common/testing-conventions.md);
feature work remains subject to [the incident safety gate](security-incident.md).

## Provenance

- Upstream: https://github.com/kirodotdev/KiroCrew
- Fork: https://github.com/elkestc/KiroCrew
- Pinned commit: `395dc8df14610973b0753f5e88fa9bd8b08e1830`.
- Clone/fork date: 2026-09-11 JST.
- Source version: `0.7.0`; no upstream tag reference matched this SHA in
  `git ls-remote --tags upstream`.
- Tracking checkout: `G:\Projects\.agentic_development\KiroCrew-upstream`.
- Development worktree: `G:\Projects\.agentic_development\KiroCrew-subscriptions`.
- Branch: `feat/subscription-evaluation`; remotes `upstream` and `origin`.
- Filtered clone: `--filter=blob:none --single-branch --no-tags`.
- LICENSE, NOTICE and THIRD-PARTY-NOTICES retained unchanged.
- Source and lock hashes: [machine-readable provenance](provenance.json).
  Both Git blob and checkout-byte hashes are recorded because Windows checkout
  line endings can differ. No Python lockfile is tracked; resolved installed
  versions are captured in `windows-python-packages.json` outside the worktree.

The parent workspace was not a Git repository and contained the handoff.
The worktree was clean before installation. Runtime source is untouched during
baseline capture. An interrupted full clone left incomplete directories in the
parent workspace; they are not used for execution.

## Supported and observed environment

Source requires Python >=3.12 and Node >=22. Windows support has documented
feature limits. The Windows baseline uses Python 3.13.7 and Node 22.20.0.
WSL Ubuntu 24.04 provides Python 3.12.3, bubblewrap and working user namespaces;
Linux Node 22.20.0 is installed in disposable storage.

See [Windows support](../guides/windows-install.md) and
[testing conventions](../system-specs/common/testing-conventions.md).

## Baseline procedure

1. Create a dedicated worktree at the pinned SHA.
2. Create `.venv`, upgrade pip, and install `-e ".[voice]" --group dev`.
   The contributor page's `[dev]` example is stale; the pinned pyproject declares
   a PEP 735 dependency group.
3. Run `npm ci` in `website` and `website/electron`.
4. Run `npm run build` in `website` and stage its dist into the package.
5. Run retained Python tests with `-m "not integration"`, 16-worker ceiling,
   native loadgroup scheduling and 120-second per-test timeout.
6. Run frontend tests, format/import/lint/type checks and a wheel build.

Evaluation uses an explicit disposable `KIROCREW_HOME`, model downloads
disabled during unit tests, and telemetry off. No gateway/service is installed
or launched as part of the baseline. Browser integration tests need a bounded
gateway/browser experiment and are excluded from this first run.

## Results

Backend dependency installation succeeds. Frontend dependency installation and
postinstall complete, with an npm optional-directory cleanup warning and five
reported moderate advisories. Lockfiles are retained; no audit-fix mutation is
applied. Frontend TypeScript/Vite build succeeds.
The Python suite runs in the separate clean `KiroCrew-baseline` worktree at the
same SHA, with its own environment and the staged frontend build. The earlier
four-worker attempt in the development worktree was interrupted and is recorded
as aborted, not a passing baseline. The clean Windows run ended with an internal
error after worker timeouts; it is a failed, incomplete baseline.

| Check | Observed result | Evidence filename |
| --- | --- | --- |
| Frontend TypeScript/Vite build | PASS | `website-build.log` |
| Diff-scoped Black gate | PASS, zero changed source files | `black.log` |
| Explicit subprocess encoding gate | PASS | `subprocess-encoding.log` |
| isort check | PASS | `isort.log` |
| Flake8 | PASS | `flake8.log` |
| mypy | PASS, 1,391 source files | `mypy.log` |
| Wheel build | PASS | `wheel-build.log`, `wheels/` |
| Documentation lint | PASS with report-only upstream stale entries | `docs-lint.log` |
| Windows retained Python suite | Failed/incomplete: 115 failed, 48,864 passed, 1,717 skipped, 5 xfailed before abort | `clean-baseline-pytest.log`, `.xml` |
| Linux retained Python suite | FAIL: 94,015 passed, 42 failed, 644 skipped, 9 xfailed | `linux-baseline-pytest.log`, `.xml` |
| Frontend Vitest suite | PASS: 1,992 files; 31,497 passed, 1 expected failure, 3 skipped | `frontend-tests.log` |
| Windows Electron suite | FAIL: 1,831 passed, 2 failed, 5 skipped | `frontend-tests.log` |
| Linux Electron suite | PASS: 1,837 passed, 1 skipped | `linux-electron-tests.log` |

The wheel contains LICENSE, NOTICE, the frontend index and 2,377 frontend dist
files. Its SHA-256 and size are in the provenance record. A successful build
does not establish runtime or test acceptance.

The default Black gate is diff-scoped and reports no changed files; it is not
evidence that the whole upstream tree is uniformly formatted.

## Windows failure triage

The frontend portion of `npm test` passes; its subsequent Electron portion
fails only the two `dashboard:open-file` cases in `ipc-registrar.test.js`, where
`fs.symlinkSync` raises EPERM before the assertions can run. The Linux Electron
run passes with the same tests and pinned lockfile; only the unused desktop
binary download is disabled for these headless `node:test` cases. This confirms
the two Windows failures depend on host symlink capability.

The run collected 91,222 items but exited 3 after 21 minutes 15 seconds. Three
workers died and xdist exhausted the retained two-replacement ceiling before
raising an internal error. The timeout evidence includes onboarding import and
history-locking tests; the final controller error names an oversized skill-body
test. The ordinary failure summary was not emitted after this abort.

The retained JUnit report is summarized in `clean-baseline-pytest.summary.json`.
Many failures involve the host's CP932 default encoding, despite explicitly
UTF-8 subprocess output. Other failures include path/governance assumptions and
a config snapshot mismatch. These are baseline findings with no source changes;
they are not automatically waived or attributed to the provider work.

Recorded skips include POSIX/Linux-only ACP frame recording, known entries in
`test/windows-expected-failures.txt`, unavailable Windows symlink privileges,
and tests requiring POSIX Bash/jq. Exact reasons and counts are retained in the
JUnit summary; the marker exclusion also leaves live browser integration
unexecuted. The aborted run cannot account for every collected test.

Two representative CP932 failures pass with `PYTHONUTF8=1` on the unchanged
baseline: the CI test-root inventory and Auto Research brief update. Evidence:
`windows-utf8-reproduction.log` (2 passed). This establishes a configuration
remedy for those two cases only; it does not clear the aborted Windows suite.

To establish the target runtime baseline, the same commit was cloned into WSL's
Linux filesystem at `/tmp/kirocrew-evaluation-20260911/baseline`, with its own
Python 3.12 environment, the retained dependency groups and staged frontend.
`run-linux-baseline.sh` records the SHA, clean status before/after, JUnit output
and exit code. It keeps the native scheduling/timeout/replacement settings and
uses a 12-worker ceiling. Browser integration is the only explicit marker
exclusion. The run completed in 818.53 seconds with a clean source checkout.

## Critical Linux isolation finding

The selected suite was assumed safe from its native isolation fixtures, but
that assumption failed on this host. `/home/panda/.aws` is an existing symlink
to `/mnt/c/Users/panda/.aws`. Several native sensitive-path checks resolved that
link and did not reject the destination. Upstream tests use real `Path.home()`
credential paths expecting a denial; this exposed actual credential contents
in failure output. `TestSafeWriteFileNolink.test_refuses_a_blank_or_sensitive_path`
also overwrote the Windows credentials file with its one-character `x` fixture.

Further test execution was stopped. The exact sentinel overwrite was confirmed
and the prior profile text recovered from the earlier snapshot failure in the
same JUnit report. Readback matched that snapshot. The credential values were
redacted from the local log, JUnit file and summary; the metadata-only
`credential-repair-record.json` records the repair. The neighboring configuration
file retained its earlier modification time, and the credential directory
contained only its two existing files after repair. Because the value appeared
in tool output, the affected credential should be rotated by the owner.

This is a demonstrated `SAFETY_GAP`, not an environment-dependent skip or a green
baseline. Future test runs need OS isolation from the operator's credential
stores, independently of the security function being tested. The canonical-path
handling also needs a controlled synthetic regression before provider work.
Other Linux failures include unavailable CLI/Node lookup paths, missing timezone
aliases, and remaining focused assertions; they do not erase this isolation
finding.
