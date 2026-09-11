# Credential incident and safety gate

Status: **CLOSED — technical checks passed; owner confirmed R2 credential revocation.**
Date: 2026-09-11 JST.
Pinned upstream: `395dc8df14610973b0753f5e88fa9bd8b08e1830`.

The security fixes and technical verification are complete locally. The full
retained Python suite passed in the isolated environment. The owner subsequently
confirmed that the exposed R2 credential was revoked, completing the safety gate.
Feature work may resume with the isolation controls retained. Changes remain
uncommitted and unpushed.

## Root cause and affected paths

The incident report establishes this path chain. This remediation did not reopen,
stat or resolve the live credential store to reconstruct it.

| Operation | Original input | Expanded Linux path | WSL drive spelling | Windows target |
|---|---|---|---|---|
| Credential reads | `~/.aws/credentials` | `/home/panda/.aws/credentials` | `/mnt/c/Users/panda/.aws/credentials` | `C:\Users\panda\.aws\credentials` |
| Credential overwrite | home plus `.aws/credentials` | `/home/panda/.aws/credentials` | `/mnt/c/Users/panda/.aws/credentials` | `C:\Users\panda\.aws\credentials` |
| Additional failed read-refusal assertions | `~/.aws/config` | `/home/panda/.aws/config` | `/mnt/c/Users/panda/.aws/config` | `C:\Users\panda\.aws\config` |

At the pinned revision:

1. `test_file_change_snapshots.py` line 111 called `_safe_read_snapshot`, then
   `hooks.validate_file_path`, then `Path.read_text` on the returned path.
   `TestSnapshotWriteTarget` also read through the snapshot helper at line 150.
2. `hooks.py::validate_file_path` at line 2262 expanded the home and resolved
   links before its sensitive-path check at line 2397. Resolution discarded the
   lexical `.aws` identity. POSIX did not screen linked ancestors first.
3. `security/paths.py::_home_dir_targets_uncached` anchored sensitive directories
   beneath the home. The resolved Windows location fell outside those anchors,
   so the denylist allowed it.
4. `test_hooks_coverage.py::test_refuses_a_blank_or_sensitive_path` at line 1048
   called `safe_write_file_nolink` with the home-derived credential path, content
   `x`, and no `within_root`. `_pinned_replace` accepted the resolved target and
   reached its atomic replacement path. Leaf no-follow and descriptor identity
   checks established target identity, but did not authorize that target as test
   data.
5. Root fixtures redirected selected application paths rather than the complete
   home before collection. The old isolation check was a directory denylist and
   trusted a resolved temporary base. Failed assertions printed returned content.

The incident exposed a live Cloudflare R2 credential and overwrote its file.
Restoring the file did not undo the disclosure. The redacted evidence manifest
also identifies affected byte-read, prefix-read and snapshot-reconstruction tests.

## Remediation

`test_isolation.py::AllowedTestRoot` requires an explicit absolute, unlinked
test-data root. It rejects lexical escapes and parent traversal before filesystem
resolution; checks every linked/reparse component, root identity and filesystem
device; checks the current Linux mount table, including same-device bind mounts;
and independently checks the fully resolved destination. Internal links are
permitted only after each lexical destination passes the same boundary.
Descriptor-relative reads, writes, rename and unlink operations are checked using
their actual parent. Descriptor aliases to files must resolve inside the root.

The audit layer also permits read-only reopening of sealed anonymous memory that
this process created and registered by device/inode identity. Unregistered,
unsealed, foreign-process and writable aliases are refused. This preserves the
decoder's immutable execution snapshot without authorizing a filesystem escape.
The distinction follows the kernel's [anonymous-memory API](https://man7.org/linux/man-pages/man2/memfd_create.2.html)
and [file-sealing API](https://man7.org/linux/man-pages/man2/F_ADD_SEALS.2const.html).

Root `conftest.py` arms the boundary before test collection and capability probes.
A private, mandatory fake-home fixture provides disposable AWS credential/config
files and HOME, USERPROFILE, XDG and application-data paths. A module's existing
`fake_home` fixture cannot replace it. Test code uses explicit fake-home helpers;
an AST regression checks both collected test trees for executed `Path.home()`
calls. The launcher starts from an environment allowlist, and each test clears
cloud variables left by another test. Tests may supply synthetic values.

Application file helpers preserve the original sensitive-path check before
resolution, then check the resolved path as well. Caller-supplied `within_root`
limits are checked before open, with existing descriptor identity protections
retained. Refusal messages do not echo attacker-controlled paths or file contents.

The mandatory Linux launcher copies inventoried regular source files into a fresh
directory. Bubblewrap creates separate user, mount, PID and network namespaces,
drops capabilities, clears the environment and makes the namespace root read-only.
Writable test data resides under `/test-root`; system and Python runtimes are
read-only. `/proc` covers the isolated PID namespace and `/dev` is newly created.
There are no host-home, Windows drive or service-socket mounts. Read-only WSL
driver libraries under `/usr` are runtime mounts, not user-home mounts. Tests have
no outbound network route and perform no dependency downloads.

The source archive preserves executable modes from Git. The disposable copy gets
a synthetic Git index/commit, fake identity and no imported remotes, hooks or
history. A synthetic editable-install entry points child interpreters to the
copied package, without changing the prepared venv. Explicit runtime aliases and
fake OpenSSL configuration replace dependence on host account/configuration
files. CLI tests use fake availability and the actual mocked launch function.

The Python audit layer is defense in depth. The OS namespace is the boundary for
native code, subprocesses and filesystem races. No host-connected pytest fallback
is provided.

## Verification and evidence

All paths below are beneath
`G:\Projects\.agentic_development\evaluation-artifacts\2026-09-11\`.
Each proof directory contains launch arguments, exit status, source SHA-256
inventory and relevant JUnit/log/quality/namespace files.

| Proof | Result |
|---|---|
| `safe-test-proof/regression-v22` | 720 passed, zero skips/failures/errors; 37.35 seconds; includes the corrected ACP/cache tests and all current boundary regressions |
| `safe-test-proof/followup-v20` | 447 passed, 2 existing skips, zero failures/errors; 33.84 seconds; covers all 27 failures from the preceding full run |
| `safe-test-proof/namespace-v20` | PASS: only loopback visible, outbound connection refused, no host-home/drive mounts |
| `safe-test-proof/quality-v22` | PASS: isort/Black checks and Flake8 for 86 changed Python files, full source/test Flake8, mypy across 1,391 source files, documentation and subprocess-encoding gates |
| `safe-test-proof/full-v22` | **PASS: 93,874 passed, 850 skipped, 9 expected failures; zero failures/errors**; 1346.95 seconds; 16 workers |

Regressions exercise actual `.aws` symlink reads and writes outside an allowed
subtree and verify that the external disposable target's digest is unchanged.
They cover direct I/O, production snapshots/writes, descriptor-relative operations,
file descriptor aliases, lexical and resolved escapes, and a real subordinate
bind mount. Added memory-descriptor tests prove ownership and sealing are both
required. No live credential file participates in these tests. Junction/reparse
metadata is simulated on Linux; no native Windows host-connected junction test was
run. No frontend or live-service integration pass is claimed.

No failing test was disabled as remediation. The earlier full v9 run stopped at
about 77% with an xdist internal error. The guard now retains its own resolver and
mount-file reader and avoids Python 3.12's `ismount` call into a globally mocked
`realpath`; see the [CPython source](https://github.com/python/cpython/blob/v3.12.3/Lib/posixpath.py).
Full v19 completed with 93,840 passed, 27 failed, 851 skipped, 9 expected failures,
and no setup errors or worker crashes. Its failures led to the v20 corrections.
Full v20 completed with 93,869 passed, 3 failed, 852 skipped and 9 expected failures.
Those three ACP tests inherited another test's in-memory model advertisement
cache. Their fixture now supplies the empty initial cache its assertions require;
no model-selection implementation changed.
The full-run JUnit totals include extra reported phases; the pytest completion
line is used for run counts rather than treating XML phase totals as unique tests.

The inherited-lock regression still proves real exclusion and live-owner lookup.
In the isolated PID namespace, when the dead owner's lock row is filtered, it now
also verifies the actual inheriting process, stale recorded PID and honest
fallback diagnosis. Existing reported-owner assertions remain for visible rows.
Linux documents [PID-namespace filtering of lock records](https://www.man7.org/linux/man-pages/man5/proc_locks.5.html).

Docker/Ubuntu runtime availability was restored by the owner. Earlier WSL timeout
and Docker probe failures are historical. No WSL shutdown, distro termination,
Docker restart or unrelated process termination was issued by this remediation.
The prepared dependency set includes the already-installed `tzdata` 2026.3
package. No download occurred during tests.

## Secret scan, preservation and remaining exposure

The recursive Windows workspace/local-session scan covered **150,774 files**:
0 read errors, 2,739,455 candidate locations and 4,607 opaque files.
The WSL evaluation-directory scan covered **56,299 files**: 0 read errors,
545,479 candidates, 49 deliberately skipped links/store paths and 1,831 opaque
files. These are candidate counts, including digests/test literals, not counts of live
secrets or proof of absence. The reports emit locations with token-shaped names
redacted, rule IDs, byte offsets and SHA-256 fingerprints, never matching values
or snippets. Credential stores and links are not traversed. Compressed/encrypted
contents and service-side copies are outside the scan's assurance.

Reports: `incident-secret-scan.summary.json`, `incident-secret-scan.jsonl` and
`incident-wsl-secret-scan.jsonl`. The final source delta contains 108 changed/new
source and document files. Its recursive scan is recorded in
`incident-final-delta-scan-v22.jsonl`. Archived offline proof scans are recorded
in `incident-offline-proof-scan-v21.jsonl` and
`incident-offline-proof-scan-final.jsonl`. `security-gate-status.json` records
their counts, errors, hashes and current source hashes. Every changed Python
file matches the full-run source inventory; the report is finalized afterward.

`incident-evidence-manifest.json` preserves the names, sizes and SHA-256 hashes of
the original incident artifacts and affected test identifiers without reproducing
captured values. Those artifacts had already been locally redacted before this
response; the recorded hashes authenticate the current redacted bytes, not the
original unredacted content. Every archived proof rechecks those hashes, and all
remain unchanged. No service-side transcript was modified.

The owner initially reported replacement/revocation underway and no evidence of
Cloudflare misuse, then explicitly confirmed that the R2 credential was revoked.
This is owner confirmation; this remediation did not independently probe
Cloudflare or use the credential. Earlier chat/tool transcripts, local sessions
and backups may retain copies of the revoked credential. The technical checks
and revocation confirmation complete the safety gate. Test isolation and the
prohibition on accessing the affected host credential store remain in force.

## Reproduction

Use `scripts/create_test_inventory.py` to inventory/archive the current checkout
with native Git. In the restored Linux runtime, the final full-suite command is:

```sh
task_repo=/mnt/g/Projects/.agentic_development/KiroCrew-subscriptions
task_evidence=/mnt/g/Projects/.agentic_development/evaluation-artifacts/2026-09-11
python3 -I "$task_repo/scripts/run_isolated_tests.py" \
  --source "$task_repo" \
  --file-list "$task_evidence/isolated-source-files-v22.json" \
  --archive "$task_evidence/isolated-source-v22.tar" \
  --venv /tmp/kirocrew-evaluation-20260911/venv --workers 16
```

The launcher retains `-n auto --dist loadgroup --max-worker-restart=2` and
`-m "not integration"`. `--check` selects the namespace probe;
`--quality-from` selects an explicit JSON list of Python quality targets;
`--tests-from` selects a JSON list of diagnostic modules. Omitting selectors runs
the full retained suite. Regenerate the inventory/archive after code changes.
Historical host-connected baseline and repair launchers must not be reused.
