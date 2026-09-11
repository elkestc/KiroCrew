"""Real filesystem regressions for the credential symlink incident."""

import ast
import hashlib
import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_isolation import AllowedTestRoot, TestRootViolation, fake_home_context, fake_home_path


def _digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_platform_null_device_remains_available_without_file_access():
    with open(os.devnull, "wb") as stream:
        stream.write(b"DISPOSABLE_NULL_DEVICE_ONLY")
    with open(os.devnull, "rb") as stream:
        assert stream.read() == b""


def _directory_link(link, target):
    if sys.platform == "win32":
        subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            cwd=link.parent,
            capture_output=True,
            check=True,
            timeout=10,
        )
    else:
        link.symlink_to(target, target_is_directory=True)


@pytest.fixture
def escaping_aws(tmp_path):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()
    target = outside / "credentials"
    target.write_bytes(b"DISPOSABLE_SENTINEL_ONLY\n")
    _directory_link(allowed / ".aws", outside)
    return allowed, target


@pytest.mark.parametrize("operation", ["read", "write"])
def test_aws_link_cannot_read_or_write_external_target(escaping_aws, operation):
    allowed, target = escaping_aws
    before = _digest(target)
    boundary = AllowedTestRoot(str(allowed))
    with pytest.raises(TestRootViolation):
        path = Path(boundary.validate(allowed / ".aws" / "credentials"))
        if operation == "read":
            path.read_bytes()
        else:
            path.write_bytes(b"REPLACEMENT_TEST_SENTINEL")
    assert _digest(target) == before


@pytest.mark.parametrize("operation", ["read", "write"])
def test_global_io_floor_blocks_direct_aws_link_access(escaping_aws, operation, monkeypatch):
    import test_isolation

    allowed, target = escaping_aws
    before = _digest(target)
    with monkeypatch.context() as patch:
        patch.setattr(
            test_isolation, "_BOUNDARY", AllowedTestRoot(str(allowed), allow_internal_links=True)
        )
        with pytest.raises(TestRootViolation):
            if operation == "read":
                (allowed / ".aws" / "credentials").read_bytes()
            else:
                (allowed / ".aws" / "credentials").write_bytes(b"REPLACEMENT_TEST_SENTINEL")
    assert _digest(target) == before


def test_positive_root_holds_when_sensitive_denylist_misses(escaping_aws, monkeypatch):
    from kiro_crew import hooks

    allowed, target = escaping_aws
    before = _digest(target)
    monkeypatch.setattr(hooks, "is_sensitive_path", lambda _path: False)
    raw = str(allowed / ".aws" / "credentials")
    assert hooks.validate_file_path(raw, within_root=str(allowed)) is None
    assert hooks.safe_read_file_bytes_nolink(raw, within_root=str(allowed)) is None
    assert (
        hooks.safe_write_file_nolink(raw, "REPLACEMENT_TEST_SENTINEL", within_root=str(allowed))
        is False
    )
    assert _digest(target) == before


@pytest.mark.parametrize("operation", ["read", "write", "rename", "unlink"])
@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no openat directory descriptors")
def test_directory_descriptor_cannot_bypass_root(escaping_aws, monkeypatch, operation):
    import test_isolation

    allowed, target = escaping_aws
    before = _digest(target)
    descriptor = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(test_isolation, "_BOUNDARY", AllowedTestRoot(str(allowed)))
            with pytest.raises(TestRootViolation):
                if operation in ("read", "write"):
                    flags = os.O_RDONLY if operation == "read" else os.O_WRONLY | os.O_TRUNC
                    opened = os.open("credentials", flags, dir_fd=descriptor)
                    os.close(opened)
                elif operation == "rename":
                    os.rename(
                        "credentials", "changed", src_dir_fd=descriptor, dst_dir_fd=descriptor
                    )
                else:
                    os.unlink("credentials", dir_fd=descriptor)
    finally:
        os.close(descriptor)
    assert _digest(target) == before


def test_original_snapshot_and_write_shapes_use_fake_credentials(fake_home):
    from kiro_crew import hooks
    from kiro_crew.dashboard.chat_runner import _safe_read_snapshot

    target = fake_home / ".aws" / "credentials"
    before = _digest(target)
    assert _safe_read_snapshot("~/.aws/credentials") is None
    assert hooks.safe_write_file_nolink(str(target), "REPLACEMENT_TEST_SENTINEL") is False
    assert _digest(target) == before


@pytest.mark.parametrize(
    "prefix", ["/dev/fd"] if sys.platform == "darwin" else ["/dev/fd", "/proc/self/fd"]
)
@pytest.mark.parametrize("operation", ["read", "write"])
@pytest.mark.skipif(sys.platform == "win32", reason="Windows has no POSIX descriptor path aliases")
def test_descriptor_alias_cannot_escape_root(escaping_aws, monkeypatch, prefix, operation):
    import test_isolation

    allowed, target = escaping_aws
    before = _digest(target)
    descriptor = os.open(target, os.O_RDONLY)
    try:
        with monkeypatch.context() as patch:
            patch.setattr(test_isolation, "_BOUNDARY", AllowedTestRoot(str(allowed)))
            alias = Path(prefix) / str(descriptor)
            with pytest.raises(TestRootViolation):
                if operation == "read":
                    alias.read_bytes()
                else:
                    alias.write_bytes(b"DISPOSABLE_REPLACEMENT")
    finally:
        os.close(descriptor)
    assert _digest(target) == before


@pytest.mark.parametrize("prefix", ["/dev/fd", "/proc/self/fd"])
@pytest.mark.skipif(sys.platform != "linux", reason="Sealed memfd is a Linux-only API")
def test_owned_sealed_anonymous_memory_can_be_reopened_readonly(prefix):
    import fcntl

    descriptor = os.memfd_create("DISPOSABLE_ONLY", os.MFD_ALLOW_SEALING)
    try:
        os.write(descriptor, b"DISPOSABLE_MEMORY_ONLY")
        fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, 0xF)
        alias = Path(prefix) / str(descriptor)
        assert alias.read_bytes() == b"DISPOSABLE_MEMORY_ONLY"
        with pytest.raises(TestRootViolation):
            alias.write_bytes(b"DISPOSABLE_REPLACEMENT")
    finally:
        os.close(descriptor)


@pytest.mark.parametrize("owned", [False, True])
@pytest.mark.skipif(sys.platform != "linux", reason="Sealed memfd is a Linux-only API")
def test_anonymous_descriptor_requires_both_ownership_and_sealing(owned):
    import fcntl

    import test_isolation

    create = os.memfd_create if owned else test_isolation._ORIGINAL_MEMFD_CREATE
    descriptor = create("DISPOSABLE_ONLY", os.MFD_ALLOW_SEALING)
    try:
        os.write(descriptor, b"DISPOSABLE_MEMORY_ONLY")
        if not owned:
            fcntl.fcntl(descriptor, fcntl.F_ADD_SEALS, 0xF)
        with pytest.raises(TestRootViolation):
            Path(f"/proc/self/fd/{descriptor}").read_bytes()
        os.lseek(descriptor, 0, os.SEEK_SET)
        assert os.read(descriptor, 128) == b"DISPOSABLE_MEMORY_ONLY"
    finally:
        os.close(descriptor)


def test_original_lexical_aws_identity_survives_resolution(tmp_path):
    from kiro_crew import hooks
    from kiro_crew.dashboard.chat_runner import _safe_read_snapshot

    home = tmp_path / "fake-home"
    outside = tmp_path / "fake-windows-target"
    home.mkdir()
    outside.mkdir()
    target = outside / "credentials"
    target.write_bytes(b"DISPOSABLE_LINK_TARGET_ONLY\n")
    _directory_link(home / ".aws", outside)
    before = _digest(target)
    # Both sides are inside the outer disposable root. The production helper
    # must refuse the original credential spelling without relying on that floor
    # or on the caller supplying within_root.
    with fake_home_context(home):
        assert hooks.validate_file_path("~/.aws/credentials") is None
        assert _safe_read_snapshot("~/.aws/credentials") is None
        assert (
            hooks.safe_write_file_nolink(str(home / ".aws" / "credentials"), "TEST_ONLY") is False
        )
    assert _digest(target) == before


def test_lexical_outside_path_rejected_before_resolution(tmp_path, monkeypatch):
    boundary = AllowedTestRoot(str(tmp_path))

    def forbidden(_path):
        pytest.fail("Outside lexical path reached filesystem resolution")

    monkeypatch.setattr(boundary, "_resolved_path", forbidden)
    with pytest.raises(TestRootViolation):
        boundary.validate("/unmounted-external/credentials")


def test_resolved_escape_is_independently_rejected(tmp_path, monkeypatch):
    boundary = AllowedTestRoot(str(tmp_path))
    monkeypatch.setattr(boundary, "_resolved_path", lambda _path: "/unmounted-external/credentials")
    with pytest.raises(TestRootViolation):
        boundary.validate(tmp_path / "credentials")


def test_boundary_keeps_its_resolver_when_application_tests_mock_realpath(tmp_path, monkeypatch):
    target = tmp_path / "disposable"
    target.write_bytes(b"TEST_ONLY")
    boundary = AllowedTestRoot(str(tmp_path))

    def unavailable(*_args, **_kwargs):
        raise AssertionError("Application resolver is unavailable")

    monkeypatch.setattr(os.path, "realpath", unavailable)
    assert boundary.validate(target) == str(target)
    assert target.read_bytes() == b"TEST_ONLY"


def test_boundary_survives_application_open_and_platform_mocks(tmp_path, monkeypatch):
    import builtins

    target = tmp_path / "disposable"
    target.write_bytes(b"TEST_ONLY")
    boundary = AllowedTestRoot(str(tmp_path))
    with monkeypatch.context() as patch:
        patch.setattr(os, "name", "nt")
        patch.setattr(builtins, "open", lambda *_args, **_kwargs: object())
        assert boundary.validate(str(target)) == str(target)
    assert target.read_bytes() == b"TEST_ONLY"


def test_parent_traversal_is_rejected(tmp_path):
    boundary = AllowedTestRoot(str(tmp_path))
    with pytest.raises(TestRootViolation):
        boundary.validate(str(tmp_path) + "/../outside")


def test_junction_metadata_refused_before_resolution(tmp_path, monkeypatch):
    link = tmp_path / ".aws"
    link.mkdir()
    boundary = AllowedTestRoot(str(tmp_path))
    real_lstat = os.lstat

    def junction(path, *args, **kwargs):
        if os.fspath(path) == str(link):
            return SimpleNamespace(st_mode=0o40700, st_file_attributes=0x400)
        return real_lstat(path, *args, **kwargs)

    monkeypatch.setattr(os, "lstat", junction)
    with pytest.raises(TestRootViolation):
        boundary.validate(link / "credentials")


def test_subordinate_mount_refused(tmp_path, monkeypatch):
    mount = tmp_path / "wsl-drive"
    mount.mkdir()
    boundary = AllowedTestRoot(str(tmp_path))
    real_lstat = os.lstat

    def changed_device(path, *args, **kwargs):
        result = real_lstat(path, *args, **kwargs)
        if os.fspath(path) == str(mount):
            return SimpleNamespace(st_mode=result.st_mode, st_dev=result.st_dev + 1)
        return result

    monkeypatch.setattr(os, "lstat", changed_device)
    with pytest.raises(TestRootViolation):
        boundary.validate(mount / "credentials")


def test_same_filesystem_bind_mount_refused(tmp_path, monkeypatch):
    import test_isolation

    mount = tmp_path / ".aws"
    mount.mkdir()
    boundary = AllowedTestRoot(str(tmp_path))
    monkeypatch.setattr(test_isolation, "_mount_points", lambda: (str(mount),))
    with pytest.raises(TestRootViolation):
        boundary.validate(mount / "credentials")


@pytest.mark.parametrize("operation", ["read", "write"])
@pytest.mark.skipif(sys.platform != "linux", reason="Bind mounts require Linux mount namespaces")
def test_real_bind_mount_cannot_read_or_write_external_target(tmp_path, operation):
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    (allowed / ".aws").mkdir(parents=True)
    outside.mkdir()
    target = outside / "credentials"
    target.write_bytes(b"DISPOSABLE_BIND_SENTINEL\n")
    before = _digest(target)
    program = (
        "import sys; from pathlib import Path; "
        "from test_isolation import AllowedTestRoot, TestRootViolation\n"
        "try:\n"
        " p=Path(AllowedTestRoot(sys.argv[1]).validate(Path(sys.argv[1])/'.aws'/'credentials'))\n"
        " p.read_bytes() if sys.argv[2]=='read' else p.write_bytes(b'DISPOSABLE_REPLACEMENT')\n"
        "except TestRootViolation:\n"
        " sys.exit(0)\n"
        "sys.exit(3)\n"
    )
    result = subprocess.run(
        [
            "/usr/bin/bwrap",
            "--unshare-all",
            "--die-with-parent",
            "--new-session",
            "--ro-bind",
            "/",
            "/",
            "--bind",
            str(outside),
            str(allowed / ".aws"),
            "--proc",
            "/proc",
            "--cap-drop",
            "ALL",
            sys.executable,
            "-c",
            program,
            str(allowed),
            operation,
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0
    assert _digest(target) == before


def test_new_child_has_fake_home_and_no_cloud_environment(fake_home, tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,pathlib; from test_isolation import AllowedTestRoot; root=AllowedTestRoot(os.environ['KIROCREW_TEST_ROOT']); root.validate(os.environ['HOME']); assert pathlib.Path(os.environ['HOME'], '.aws', 'credentials').is_file(); assert not any(k.startswith(('AWS_', 'CLOUDFLARE_', 'R2_')) for k in os.environ)",
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0
    assert fake_home_path() == fake_home


@pytest.mark.xdist_group(name="tree_scan_test_home_access")
def test_test_code_never_calls_path_home():
    repo = Path(__file__).resolve().parents[1]
    paths = [repo / "conftest.py"]
    paths.extend((repo / "test").rglob("*.py"))
    paths.extend(
        path
        for path in (repo / "src/kiro_crew/apps/builtins").rglob("*.py")
        if "tests" in path.parts
    )
    violations = []
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        path_types = {"Path", "PosixPath", "WindowsPath"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "pathlib":
                path_types.update(
                    alias.asname or alias.name for alias in node.names if alias.name in path_types
                )
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "home"
            ):
                owner = node.func.value
                if (
                    isinstance(owner, ast.Name)
                    and owner.id in path_types
                    or isinstance(owner, ast.Attribute)
                    and owner.attr == "Path"
                ):
                    violations.append(f"{path.relative_to(repo)}:{node.lineno}")
    assert not violations
