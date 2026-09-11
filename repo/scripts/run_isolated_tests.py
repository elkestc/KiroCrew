"""Linux-only offline test launcher. Copies source; never mounts a host home.

Prepare dependencies separately. This launcher performs no downloads, starts no
service, and runs no tests until bubblewrap has removed host mounts/networking.
Raw output stays in the disposable run directory; stdout contains status only.
"""

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--venv", required=True)
    parser.add_argument("--file-list", required=True)
    parser.add_argument("--archive")
    parser.add_argument("--tests-from")
    parser.add_argument("--quality-from")
    parser.add_argument("--command-from")
    parser.add_argument("--result-file")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("tests", nargs="*")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.quality_from, args.command_from, args.check)) > 1:
        parser.error("Select only one isolated command mode")
    if args.tests_from:
        args.tests.extend(json.loads(Path(args.tests_from).read_text(encoding="utf-8")))
    if sys.platform != "linux" or not shutil.which("bwrap"):
        raise SystemExit("Requires Linux bubblewrap; no host-test fallback")
    source = Path(args.source).resolve(strict=True)
    venv = Path(args.venv).resolve(strict=True)
    run = Path(tempfile.mkdtemp(prefix="kirocrew-offline-", dir="/tmp"))
    data = run / "data"
    repo = data / "repo"
    repo.mkdir(parents=True)
    for name in ("homes/collection/.aws", "tmp", "results", "etc"):
        (data / name).mkdir(parents=True)
    (data / "homes/collection/.aws/credentials").write_text(
        "[test-only]\naws_access_key_id=TEST_ONLY\naws_secret_access_key=TEST_ONLY\n",
        encoding="utf-8",
    )
    (data / "etc/passwd").write_text(
        f"test:x:{os.getuid()}:{os.getgid()}:Disposable:/test-root/homes/collection:/bin/sh\n",
        encoding="utf-8",
    )
    (data / "etc/group").write_text(f"test:x:{os.getgid()}:\n", encoding="utf-8")
    (data / "etc/hosts").write_text("127.0.0.1 localhost\n::1 localhost\n", encoding="utf-8")
    (data / "etc/nsswitch.conf").write_text(
        "passwd: files\ngroup: files\nhosts: files\n", encoding="utf-8"
    )
    # Re-exec tests use -E and scrub PYTHONPATH. Give this disposable source
    # snapshot an editable-install entry without touching the prepared venv.
    (data / "etc/offline-source.pth").write_text("/test-root/repo/src\n", encoding="utf-8")
    site_packages = list((venv / "lib").glob("python*/site-packages"))
    if len(site_packages) != 1:
        raise SystemExit("Expected exactly one prepared Python site-packages directory")
    editable_entries = list(site_packages[0].glob("__editable__.kirocrew-*.pth"))
    if len(editable_entries) != 1 or editable_entries[0].is_symlink():
        raise SystemExit("Expected one regular KiroCrew editable-install entry to replace")
    clean = {
        "PATH": "/usr/bin:/bin",
        "HOME": str(data / "homes/collection"),
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }
    listed = json.loads(Path(args.file_list).read_text(encoding="utf-8"))
    if args.archive:
        unpacked = run / "source"
        unpacked.mkdir()
        with tarfile.open(args.archive, "r") as archive:
            for member in archive:
                relative = Path(member.name)
                if not member.isfile() or relative.is_absolute() or ".." in relative.parts:
                    raise SystemExit("Source archive contains a non-regular or escaping member")
                archive.extract(member, unpacked, filter="data")
        source = unpacked
    inventory = {}
    checked_directories = {source}
    for raw in listed:
        if not raw:
            continue
        relative = Path(raw)
        original = source / relative
        if relative.is_absolute() or ".." in relative.parts:
            raise SystemExit("Source contains an escaping path; refused")
        for parent in reversed(original.parents):
            if parent == source or source in parent.parents:
                if parent not in checked_directories:
                    info = parent.lstat()
                    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
                        raise SystemExit("Source contains a linked directory; refused")
                    checked_directories.add(parent)
        info = original.lstat()
        if stat.S_ISLNK(info.st_mode):
            raise SystemExit("Source contains a linked file; refused")
        if not stat.S_ISREG(info.st_mode):
            continue
        destination = repo / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(original, destination)
        inventory[str(relative)] = hashlib.sha256(destination.read_bytes()).hexdigest()
    (run / "source-sha256.json").write_text(
        json.dumps(inventory, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    if args.quality_from:
        targets = json.loads(Path(args.quality_from).read_text(encoding="utf-8"))
        if any(path not in inventory or not path.endswith(".py") for path in targets):
            raise SystemExit("Quality target outside source inventory")
        (data / "results/quality-targets.json").write_text(json.dumps(targets), encoding="utf-8")
    if args.command_from:
        payload = json.loads(Path(args.command_from).read_text(encoding="utf-8"))
        if (
            not isinstance(payload, list)
            or not payload
            or not all(isinstance(value, str) and value for value in payload)
        ):
            raise SystemExit("Expected a nonempty command argument list")
        (data / "results/command.json").write_text(json.dumps(payload), encoding="utf-8")
    # All writable data belongs to this newly-created directory. Neither /home,
    # /root, /mnt, /run, a container socket, nor the source checkout is mounted.
    command = [
        "/usr/bin/bwrap",
        "--unshare-all",
        "--die-with-parent",
        "--new-session",
        "--cap-drop",
        "ALL",
        "--clearenv",
        "--ro-bind",
        "/usr",
        "/usr",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--ro-bind",
        str(venv),
        "/runtime/venv",
        "--bind",
        str(data),
        "/test-root",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--symlink",
        "/test-root/tmp",
        "/tmp",
        "--dir",
        "/etc",
    ]
    for name in ("passwd", "group", "hosts", "nsswitch.conf"):
        command += ["--ro-bind", str(data / "etc" / name), "/etc/" + name]
    command += [
        "--ro-bind",
        str(data / "etc/offline-source.pth"),
        "/runtime/venv/" + str(editable_entries[0].relative_to(venv)),
    ]
    # Debian's awk/which entries resolve through /etc/alternatives. Supply only
    # these vetted runtime aliases; never mount the host's /etc directory.
    command += ["--dir", "/etc/alternatives"]
    for name in ("awk", "nawk", "which"):
        target = (Path("/usr/bin") / name).resolve(strict=True)
        if not target.is_relative_to("/usr") or not target.is_file():
            raise SystemExit("Runtime utility resolves outside the read-only runtime")
        command += ["--symlink", str(target), "/etc/alternatives/" + name]
    environment = {
        "PATH": "/runtime/venv/bin:/usr/bin:/bin",
        "HOME": "/test-root/homes/collection",
        "USERPROFILE": "/test-root/homes/collection",
        "USER": "test",
        "LOGNAME": "test",
        "TMPDIR": "/test-root/tmp",
        "XDG_CONFIG_HOME": "/test-root/homes/collection/.config",
        "XDG_CACHE_HOME": "/test-root/homes/collection/.cache",
        "KIROCREW_HOME": "/test-root/homes/collection/.kiro/crew",
        "KIROCREW_TEST_ROOT": "/test-root",
        "KIROCREW_TELEMETRY": "0",
        "KIROCREW_SKIP_MODEL_DOWNLOAD": "1",
        "KIROCREW_MAX_TEST_WORKERS": str(args.workers),
        "PYTHONPATH": "/test-root/repo:/test-root/repo/src",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        "LANG": "C.UTF-8",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
    }
    for key, value in environment.items():
        command += ["--setenv", key, value]
    command += ["--remount-ro", "/", "--chdir", "/test-root/repo", "/runtime/venv/bin/python"]
    if args.quality_from:
        command += ["scripts/check_test_python.py"]
    elif args.command_from:
        command += [
            "scripts/start_test_run.py",
            "--command-file",
            "/test-root/results/command.json",
        ]
    elif args.check:
        command += ["scripts/verify_test_namespace.py"]
    else:
        command += [
            "scripts/start_test_run.py",
            "-q",
            "--color=no",
            "--tb=short",
            "--junitxml=/test-root/results/pytest.xml",
            *(args.tests or []),
        ]
    (run / "launch.json").write_text(
        json.dumps({"argv": command, "env": environment, "source_files": len(inventory)}, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "run": str(run),
                "state": "starting isolated namespace",
                "source_files": len(inventory),
            }
        ),
        flush=True,
    )
    with (data / "results/pytest.log").open("wb") as log:
        result = subprocess.run(
            command, env=clean, stdout=log, stderr=subprocess.STDOUT, check=False
        )
    (run / "exit.json").write_text(
        json.dumps({"exit_code": result.returncode}) + "\n", encoding="utf-8"
    )
    if args.result_file:
        with Path(args.result_file).open("x", encoding="utf-8") as report:
            json.dump({"run": str(run), "exit_code": result.returncode}, report)
            report.write("\n")
    print(json.dumps({"run": str(run), "exit_code": result.returncode}), flush=True)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
