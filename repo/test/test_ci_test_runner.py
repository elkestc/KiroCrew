"""CI must preserve test failures without exporting paths controlled by tests."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import make_dir_link
from scripts import ci_test_runner


@pytest.mark.parametrize("end", ["source", "destination"])
@pytest.mark.parametrize("kind", ["file-link", "parent-link", "hardlink"])
def test_export_rejects_linked_artifacts_without_changing_external_target(tmp_path, end, kind):
    allowed = tmp_path / "allowed"
    external = tmp_path / "external"
    allowed.mkdir()
    external.mkdir()
    sentinel = external / "sentinel"
    sentinel.write_bytes(b"DISPOSABLE_SENTINEL")
    incoming = allowed / "incoming"
    outgoing = allowed / "outgoing"
    incoming.write_bytes(b"DISPOSABLE_COVERAGE")
    attack = incoming if end == "source" else outgoing
    attack.unlink(missing_ok=True)
    if kind == "file-link":
        attack.symlink_to(sentinel)
    elif kind == "parent-link":
        attack.symlink_to(external, target_is_directory=True)
        attack = attack / "sentinel"
    else:
        attack.hardlink_to(sentinel)
    if end == "source":
        incoming = attack
    else:
        outgoing = attack
    with pytest.raises(ValueError):
        ci_test_runner.export_file(incoming, outgoing, source_root=allowed, output_root=allowed)
    assert sentinel.read_bytes() == b"DISPOSABLE_SENTINEL"


def test_export_copies_a_regular_artifact_and_truncates_old_output(tmp_path):
    incoming = tmp_path / "incoming"
    outgoing = tmp_path / "outgoing"
    incoming.write_bytes(b"NEW")
    outgoing.write_bytes(b"OLDER_LONGER")
    ci_test_runner.export_file(incoming, outgoing, source_root=tmp_path, output_root=tmp_path)
    assert outgoing.read_bytes() == b"NEW"


def test_export_rejects_lexical_escape_before_accessing_it(tmp_path, monkeypatch):
    def forbidden(_self):
        pytest.fail("An outside lexical path reached filesystem inspection")

    monkeypatch.setattr(Path, "lstat", forbidden)
    with pytest.raises(ValueError, match="explicit root"):
        ci_test_runner.regular_path(tmp_path.parent / "outside", root=tmp_path)


def test_junit_counts_do_not_include_captured_output(tmp_path, capsys):
    report = tmp_path / "report.xml"
    report.write_text(
        "<testsuites><testsuite><testcase/><testcase><skipped/></testcase>"
        "<testcase><failure>DISPOSABLE_DETAIL</failure></testcase>"
        "<testcase><error>DISPOSABLE_DETAIL</error></testcase>"
        "<system-out>DISPOSABLE_DETAIL</system-out></testsuite></testsuites>",
        encoding="utf-8",
    )
    assert ci_test_runner.junit_counts(report, tmp_path) == {
        "tests": 4,
        "passed": 1,
        "failures": 1,
        "errors": 1,
        "skipped": 1,
    }
    assert capsys.readouterr().out == ""


@pytest.mark.parametrize("status", [0, 1, 5])
@pytest.mark.parametrize("command_mode", [False, True])
def test_ci_forwards_shards_and_preserves_launcher_exit(
    tmp_path, monkeypatch, capsys, status, command_mode
):
    source = tmp_path / "source"
    source.mkdir()
    (source / "fixture.py").write_text("pass\n", encoding="utf-8")
    control = tmp_path / "control"
    control.mkdir()
    monkeypatch.setattr(ci_test_runner.tempfile, "mkdtemp", lambda **_kwargs: str(control))
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        if command[:2] == ["git", "ls-files"]:
            return SimpleNamespace(stdout=b"fixture.py\0", returncode=0)
        # No child is launched by this fixture. Missing reports cannot turn a
        # failure or empty collection into success.
        return subprocess.CompletedProcess(command, status)

    monkeypatch.setattr(ci_test_runner.subprocess, "run", run)
    arguments = ["--venv", "/runtime/venv", "--source", str(source)]
    if command_mode:
        arguments += ["--command"]
    payload = (
        ["python", "scripts/check_brand_name.py", "--test"]
        if command_mode
        else ["--splits", "4", "--group", "2"]
    )
    result = ci_test_runner.main([*arguments, "--", *payload])
    assert result == (status or 1)
    assert len(commands) == 2
    assert commands[1][1] == str(source / "scripts/run_isolated_tests.py")
    assert ("--command-from" if command_mode else "--tests-from") in commands[1]
    forwarded = json.loads((control / "pytest-args.json").read_text(encoding="utf-8"))
    if not command_mode:
        payload += ["--junitxml=/test-root/results/pytest.xml"]
    assert forwarded == payload
    assert capsys.readouterr().out == ""


def test_unprepared_platform_never_launches_pytest(monkeypatch):
    def forbidden(*_args, **_kwargs):
        pytest.fail("Unsupported platform attempted a child process")

    monkeypatch.setattr(ci_test_runner.sys, "platform", "win32")
    monkeypatch.setattr(ci_test_runner.subprocess, "run", forbidden)
    with pytest.raises(SystemExit, match="no host pytest fallback"):
        ci_test_runner.main(["--venv", "/runtime/venv"])


def test_source_archive_rejects_a_link_to_external_fake_credentials(tmp_path):
    source = tmp_path / "source"
    external = tmp_path / "external"
    source.mkdir()
    external.mkdir()
    sentinel = external / "credentials"
    sentinel.write_bytes(b"DISPOSABLE_SENTINEL")
    make_dir_link(source / ".aws", external)
    for arguments in (["init", "--quiet"], ["add", "--all"]):
        subprocess.run(["git", *arguments], cwd=source, check=True, capture_output=True)
    script = Path(__file__).parents[1] / "scripts/create_test_inventory.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--source",
            str(source),
            "--output",
            str(tmp_path / "inventory.json"),
            "--archive",
            str(tmp_path / "source.tar"),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert b"Linked source path refused" in result.stderr
    assert sentinel.read_bytes() == b"DISPOSABLE_SENTINEL"


def test_source_archive_rejects_linked_root_before_running_git(tmp_path):
    external = tmp_path / "external"
    external.mkdir()
    sentinel = external / "credentials"
    sentinel.write_bytes(b"DISPOSABLE_SENTINEL")
    source = tmp_path / "source"
    make_dir_link(source, external)
    script = Path(__file__).parents[1] / "scripts/create_test_inventory.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--source",
            str(source),
            "--output",
            str(tmp_path / "inventory.json"),
        ],
        cwd=tmp_path,
        capture_output=True,
        check=False,
    )
    # The target is deliberately not a Git repository: a Git error would mean
    # the linked root reached an external process before path screening.
    assert result.returncode != 0
    assert b"Linked source path refused" in result.stderr
    assert b"not a git repository" not in result.stderr
    assert sentinel.read_bytes() == b"DISPOSABLE_SENTINEL"
