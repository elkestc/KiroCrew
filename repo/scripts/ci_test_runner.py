"""Run CI pytest in the mandatory offline namespace and export named artifacts.

Dependency installation belongs to the preparation action. This wrapper copies
tracked source only, inherits no test environment and prints numeric results.
Raw test output stays in the disposable run directory.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


def regular_path(path: Path, *, root: Path, missing_leaf: bool = False) -> Path:
    """Check spelling and every link before resolving or reading file contents."""
    if not path.is_absolute() or ".." in path.parts or not path.is_relative_to(root):
        raise ValueError("Artifact path is outside the explicit root")
    for current in (*reversed(path.parents), path):
        try:
            info = current.lstat()
        except FileNotFoundError:
            if current == path and missing_leaf:
                return path
            raise
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise ValueError("Linked artifact path refused")
        if current != path and not stat.S_ISDIR(info.st_mode):
            raise ValueError("Artifact parent is not a directory")
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("Artifact must be a regular, unshared file")
    if not path.resolve(strict=True).is_relative_to(root.resolve(strict=True)):
        raise ValueError("Resolved artifact escapes its root")
    return path


def export_file(source: Path, destination: Path, *, source_root: Path, output_root: Path):
    regular_path(source, root=source_root)
    regular_path(destination, root=output_root, missing_leaf=True)
    # The child has exited. Still use no-follow descriptors and reject shared
    # inodes on both ends, so a test-created link never becomes a host read/write.
    nofollow = getattr(os, "O_NOFOLLOW", 0)
    source_fd = os.open(source, os.O_RDONLY | nofollow)
    try:
        source_info = os.fstat(source_fd)
        if not stat.S_ISREG(source_info.st_mode) or source_info.st_nlink != 1:
            raise ValueError("Unsafe artifact source")
        destination_fd = os.open(destination, os.O_WRONLY | os.O_CREAT | nofollow, 0o600)
        try:
            destination_info = os.fstat(destination_fd)
            if not stat.S_ISREG(destination_info.st_mode) or destination_info.st_nlink != 1:
                raise ValueError("Unsafe artifact destination")
            os.ftruncate(destination_fd, 0)
            while block := os.read(source_fd, 1024 * 1024):
                while block:
                    block = block[os.write(destination_fd, block) :]
        finally:
            os.close(destination_fd)
    finally:
        os.close(source_fd)


def junit_counts(path: Path, root: Path) -> dict[str, int]:
    regular_path(path, root=root)
    document = ET.parse(path).getroot()
    counts = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    for case in document.iter("testcase"):
        counts["tests"] += 1
        for kind in ("failure", "error", "skipped"):
            if case.find(kind) is not None:
                counts[{"failure": "failures", "error": "errors"}.get(kind, kind)] += 1
    counts["passed"] = counts["tests"] - sum(counts[k] for k in ("failures", "errors", "skipped"))
    return counts


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--venv", default=os.environ.get("KIROCREW_CI_TEST_VENV"))
    parser.add_argument("--source", default=str(Path(__file__).absolute().parent.parent))
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--coverage-out")
    parser.add_argument("--durations-out")
    parser.add_argument("--require-passed", type=int, default=1)
    parser.add_argument("--command", action="store_true", help="Run a checker self-test command")
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if sys.platform != "linux" or not args.venv:
        raise SystemExit("Requires the prepared Linux offline runtime; no host pytest fallback")
    if args.workers < 1 or args.require_passed < 1:
        parser.error("Worker and required-pass counts must be positive")
    if args.command and (args.coverage_out or args.durations_out):
        parser.error("Test artifact exports require pytest mode")
    source = Path(args.source).absolute()
    work = Path(tempfile.mkdtemp(prefix="kirocrew-ci-", dir="/tmp"))
    inventory = work / "source-files.json"
    result_file = work / "result.json"
    listed = subprocess.run(
        ["git", "ls-files", "--cached", "-z"],
        cwd=source,
        check=True,
        capture_output=True,
    )
    names = [name.decode("utf-8") for name in listed.stdout.split(b"\0") if name]
    for name in names:
        if ".git" in Path(name).parts:
            raise ValueError("Git metadata cannot be test source")
        regular_path(source / name, root=source)
    inventory.write_text(json.dumps(names) + "\n", encoding="utf-8")
    pytest_args = args.pytest_args
    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    # Pin the report location after user options; never export an arbitrary path
    # supplied by a test or let a different XML report stand in for this run.
    if args.command:
        if not pytest_args:
            parser.error("An isolated command must name an executable")
    else:
        pytest_args += ["--junitxml=/test-root/results/pytest.xml"]
    (work / "pytest-args.json").write_text(json.dumps(pytest_args), encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(source / "scripts/run_isolated_tests.py"),
            "--source",
            str(source),
            "--venv",
            args.venv,
            "--file-list",
            str(inventory),
            "--command-from" if args.command else "--tests-from",
            str(work / "pytest-args.json"),
            "--workers",
            str(args.workers),
            "--result-file",
            str(result_file),
        ],
        check=False,
    )
    if not result_file.is_file():
        return result.returncode or 1
    report = json.loads(result_file.read_text(encoding="utf-8"))
    run = Path(report["run"])
    if run.parent != Path("/tmp") or not run.name.startswith("kirocrew-offline-"):
        raise ValueError("Unexpected offline result root")
    status = result.returncode or int(report["exit_code"])
    counts = None
    if not args.command:
        try:
            counts = junit_counts(run / "data/results/pytest.xml", run)
            if counts["passed"] < args.require_passed or counts["errors"] or counts["failures"]:
                status = status or 1
        except (OSError, ValueError, ET.ParseError):
            status = status or 1
    # Failed suites may still provide diagnostic coverage. The exit code is
    # preserved; exporting an artifact never turns a failed suite green.
    for name, destination in (
        (".coverage", args.coverage_out),
        (".test_durations", args.durations_out),
    ):
        if destination:
            export_file(
                run / "data/repo" / name,
                source / destination,
                source_root=run,
                output_root=source,
            )
    summary = {"exit_code": status, "junit": counts, "run": str(run)}
    (work / "summary.json").write_text(json.dumps(summary) + "\n", encoding="utf-8")
    print(json.dumps(summary), flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
