"""Positive test-data boundary. The outer mount/network namespace is mandatory.

This audit hook is defense in depth, not a sandbox for hostile Python/native code.
The launcher exposes only disposable data and read-only runtime files; no home or
WSL host mounts exist in its namespace. No path or environment value is logged.
"""

from __future__ import annotations

import os
import pathlib
import re
import stat
import sys
import threading
from contextlib import contextmanager
from unittest.mock import patch

_REALPATH = os.path.realpath
_OPEN = open
_PLATFORM = sys.platform
_PURE_PATH = pathlib.PureWindowsPath if os.name == "nt" else pathlib.PurePosixPath


class TestRootViolation(PermissionError):
    """A test tried to access data outside its explicit root."""

    __test__ = False


def _inside(path: str, root: str) -> bool:
    try:
        return os.path.commonpath((path, root)) == root
    except ValueError:
        return False


def _mount_points():
    if _PLATFORM != "linux":
        return ()
    with _OPEN("/proc/self/mountinfo", encoding="utf-8") as stream:
        return tuple(
            re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), line.split()[4])
            for line in stream
        )


class AllowedTestRoot:
    """Validate lexical spelling BEFORE resolution, then the resolved target.

    Refuse linked/reparse components by default, and every subordinate mount.
    The collection floor permits internal links only after checking each lexical
    destination, without probing an external target to decide its accessibility.
    Actual test execution additionally requires an OS namespace without host data.
    """

    def __init__(self, root: str, *, allow_internal_links: bool = False):
        raw = os.fspath(root)
        if not os.path.isabs(raw) or ".." in _PURE_PATH(raw).parts:
            raise TestRootViolation("Test root must be an absolute unlinked directory")
        self.root = os.path.normpath(raw)
        self.allow_internal_links = allow_internal_links
        # Application tests replace os.path.realpath to simulate missing native
        # support. The I/O floor must retain its own resolver during that test.
        self._resolved_path = _REALPATH
        self.validate(self.root)
        self.identity = os.stat(self.root).st_dev, os.stat(self.root).st_ino

    def validate(self, path: str | os.PathLike[str], _hops: int = 0) -> str:
        if _hops > 40:
            raise TestRootViolation("Test path link chain is too long")
        raw = os.fsdecode(path)
        # No expanduser: a caller must supply a concrete test-owned path.
        if raw.startswith("~") or ".." in _PURE_PATH(raw).parts:
            raise TestRootViolation("Test path is not an explicit allowed path")
        lexical = os.path.abspath(raw)
        if not _inside(lexical, self.root):
            raise TestRootViolation("Lexical test path escapes allowed root")
        # ismount/st_dev alone miss same-filesystem bind mounts, including a
        # mount introduced after the boundary was created. Inspect the current
        # mount table before traversing any subordinate mount.
        for mounted in _mount_points():
            if mounted != self.root and _inside(mounted, self.root) and _inside(lexical, mounted):
                raise TestRootViolation("Mounted test path refused")
        cursor = _PURE_PATH(lexical).anchor
        root_seen = False
        root_device = None
        parts = _PURE_PATH(lexical).parts[1:]
        for index, part in enumerate(parts):
            cursor = os.path.join(cursor, part)
            try:
                info = os.lstat(cursor)
            except FileNotFoundError:
                break
            if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
                if self.allow_internal_links and root_seen:
                    # Read link metadata only; screen its lexical destination
                    # before any traversal of the next hop.
                    target = os.readlink(cursor)
                    target = os.path.normpath(os.path.join(os.path.dirname(cursor), target))
                    if not _inside(target, self.root):
                        raise TestRootViolation("Linked test path escapes allowed root")
                    return self.validate(os.path.join(target, *parts[index + 1 :]), _hops + 1)
                raise TestRootViolation("Linked or reparse test path refused")
            if str(cursor) == self.root:
                root_seen = True
                root_device = info.st_dev
                if hasattr(self, "identity") and (info.st_dev, info.st_ino) != self.identity:
                    raise TestRootViolation("Allowed test root identity changed")
            elif root_seen and (
                info.st_dev != root_device or (_PLATFORM != "linux" and os.path.ismount(cursor))
            ):
                # Linux's current mount table was screened above, including
                # same-device bind mounts. Avoid ismount's redundant realpath
                # traversal, which also sees application mocks on Python 3.12.
                raise TestRootViolation("Mounted test path refused")
        resolved = self._resolved_path(lexical)
        if not _inside(resolved, self.root):
            raise TestRootViolation("Resolved test path escapes allowed root")
        return resolved


_LOCAL = threading.local()
_BOUNDARY: AllowedTestRoot | None = None
_COLLECTION_HOME: str | None = None
_ORIGINAL_OPEN = os.open
_ORIGINAL_MEMFD_CREATE = getattr(os, "memfd_create", None)
_ORIGINAL_FSTAT = os.fstat
_OWNED_MEMFDS: set[tuple[int, int]] = set()
_READONLY_RUNTIME = ("/usr", "/lib", "/lib64", "/proc", "/runtime")
_DEVICE_FILES = frozenset(("/dev/null", "/dev/urandom", "/dev/random", "/dev/tty"))
_ETC_FILES = frozenset(
    (
        "/etc/passwd",
        "/etc/group",
        "/etc/hosts",
        "/etc/nsswitch.conf",
        "/etc/ld.so.cache",
        "/etc/localtime",
    )
)


def _at_path(path, directory_fd=None):
    candidate = os.fsdecode(path)
    if directory_fd not in (None, -1) and not os.path.isabs(candidate):
        candidate = os.path.join(os.readlink(f"/proc/self/fd/{directory_fd}"), candidate)
    return candidate


def _audit(event, args):
    if getattr(_LOCAL, "checking", False) or _BOUNDARY is None:
        return
    _LOCAL.checking = True
    try:
        if event == "open":
            if getattr(_LOCAL, "open_checked", False):
                return
            raw, mode, flags = args
            if isinstance(raw, int):
                # fdopen does not open a new path. Its descriptor came through open.
                return
            path = os.path.abspath(os.fsdecode(raw))
            writing = bool(
                flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND)
            )
            descriptor_path = re.fullmatch(r"/(?:dev/fd|proc/(?:self|[0-9]+)/fd)/[0-9]+", path)
            if descriptor_path:
                target = os.readlink(path)
                if target.startswith("/memfd:"):
                    import fcntl

                    descriptor = int(path.rsplit("/", 1)[1])
                    if path not in (
                        f"/dev/fd/{descriptor}",
                        f"/proc/self/fd/{descriptor}",
                        f"/proc/{os.getpid()}/fd/{descriptor}",
                    ):
                        raise TestRootViolation("Foreign anonymous descriptor refused")
                    info = _ORIGINAL_FSTAT(descriptor)
                    seals = fcntl.fcntl(descriptor, getattr(fcntl, "F_GET_SEALS", 1034))
                    if (
                        writing
                        or (info.st_dev, info.st_ino) not in _OWNED_MEMFDS
                        or seals & 0xF != 0xF
                    ):
                        raise TestRootViolation(
                            "Only owned sealed anonymous memory may be reopened"
                        )
                    # An immutable memfd created by this process is anonymous
                    # memory, not a path into a filesystem or credential store.
                    return
                if not os.path.isabs(target):
                    raise TestRootViolation("Descriptor does not name test-owned file data")
                _BOUNDARY.validate(target)
                return
            if not writing and flags & getattr(os, "O_DIRECTORY", 0):
                # Directory handles carry no file contents. Native pinned walks
                # inspect ancestry up to namespace root; subsequent openat calls
                # are checked with their actual directory descriptor below.
                return
            if path in _DEVICE_FILES:
                return
            if path == "/proc/self/oom_score_adj":
                # The child may bias its OWN OOM priority, never another PID's.
                return
            if not writing and (
                path in _ETC_FILES or any(_inside(path, root) for root in _READONLY_RUNTIME)
            ):
                return
            _BOUNDARY.validate(raw)
        elif event in ("os.remove", "os.rmdir"):
            # unlink/rmdir operate on the entry, never through a leaf symlink.
            candidate = _at_path(args[0], args[1])
            _BOUNDARY.validate(os.path.dirname(candidate) or ".")
        elif event in ("os.mkdir", "os.chmod", "os.truncate", "os.utime"):
            if not isinstance(args[0], int):
                index = {"os.mkdir": 2, "os.chmod": 2, "os.utime": 3}.get(event)
                descriptor = args[index] if index is not None else None
                _BOUNDARY.validate(_at_path(args[0], descriptor))
        elif event in ("os.rename", "os.link"):
            for index, (raw, descriptor) in enumerate(((args[0], args[2]), (args[1], args[3]))):
                candidate = _at_path(raw, descriptor)
                if (
                    event == "os.link"
                    and index == 0
                    and re.fullmatch(r"/proc/self/fd/[0-9]+", candidate)
                ):
                    # Publishing an O_TMPFILE inode is a link from its descriptor,
                    # not a read of proc data. Its actual origin must be test-owned.
                    candidate = os.readlink(candidate)
                _BOUNDARY.validate(os.path.dirname(candidate) or ".")
        elif event == "os.symlink":
            # Creating the link is safe; reading/writing THROUGH it is refused.
            _BOUNDARY.validate(_at_path(args[1], args[2]))
    finally:
        _LOCAL.checking = False


def _open_with_test_root(path, flags, mode=0o777, *, dir_fd=None):
    candidate = _at_path(path, dir_fd)
    _audit("open", (candidate, None, flags))
    previous = getattr(_LOCAL, "open_checked", False)
    _LOCAL.open_checked = True
    try:
        return _ORIGINAL_OPEN(path, flags, mode, dir_fd=dir_fd)
    finally:
        _LOCAL.open_checked = previous


def _memfd_with_test_root(name, flags=getattr(os, "MFD_CLOEXEC", 1)):
    assert _ORIGINAL_MEMFD_CREATE is not None
    descriptor = _ORIGINAL_MEMFD_CREATE(name, flags)
    info = _ORIGINAL_FSTAT(descriptor)
    _OWNED_MEMFDS.add((info.st_dev, info.st_ino))
    return descriptor


def require_isolated_environment() -> AllowedTestRoot:
    """Fail before collection unless the offline launcher established the floor."""
    global _BOUNDARY, _COLLECTION_HOME
    if _BOUNDARY is not None:
        return _BOUNDARY
    if sys.platform != "linux" or os.environ.get("KIROCREW_TEST_ROOT") != "/test-root":
        raise RuntimeError("Host-connected pytest is forbidden; use scripts/run_isolated_tests.py")
    if any(os.path.lexists(p) for p in ("/home", "/mnt", "/run/WSL", "/root")):
        raise RuntimeError("Host-home or WSL mount namespace is visible")
    # No non-loopback interface, default route, or credential-bearing inherited env.
    with open("/proc/net/dev", encoding="utf-8") as stream:
        interfaces = [line.split(":", 1)[0].strip() for line in stream if ":" in line]
    if interfaces != ["lo"]:
        raise RuntimeError("Offline network namespace is required")
    root = AllowedTestRoot("/test-root", allow_internal_links=True)
    root.validate(os.environ.get("HOME", ""))
    if not os.environ.get("HOME", "").startswith("/test-root/homes/"):
        raise RuntimeError("Disposable test home is required")
    for name in os.environ:
        if re.match(r"^(AWS_|AZURE_|GOOGLE_|GCP_|CLOUDFLARE_|R2_|OPENAI_|ANTHROPIC_)", name):
            raise RuntimeError("Inherited cloud environment is forbidden")
    _BOUNDARY = root
    _COLLECTION_HOME = os.environ["HOME"]
    sys.addaudithook(_audit)
    os.open = _open_with_test_root
    if _ORIGINAL_OPEN in os.supports_dir_fd:
        os.supports_dir_fd.add(_open_with_test_root)
    if _ORIGINAL_MEMFD_CREATE is not None:
        os.memfd_create = _memfd_with_test_root
    return root


def fake_home_path() -> pathlib.Path:
    """Explicit fake home, for tests; never consult the system user database."""
    root = require_isolated_environment()
    root.validate(os.environ["HOME"])
    return pathlib.Path(os.environ["HOME"])


def collection_home_path() -> pathlib.Path:
    """The disposable home used by immutable import-time identity anchors."""
    root = require_isolated_environment()
    assert _COLLECTION_HOME is not None
    return pathlib.Path(root.validate(_COLLECTION_HOME))


@contextmanager
def fake_home_context(home):
    """Keep environment and mocked home lookups on the same disposable path."""
    require_isolated_environment().validate(home)
    value = pathlib.Path(os.path.abspath(home))
    with (
        patch.dict(os.environ, _home_environment(value)),
        patch.object(pathlib.Path, "home", return_value=value),
    ):
        yield value


def set_fake_home(monkeypatch, home):
    """Fixture equivalent of fake_home_context, restored by its MonkeyPatch."""
    require_isolated_environment().validate(home)
    value = pathlib.Path(os.path.abspath(home))
    for name, setting in _home_environment(value).items():
        monkeypatch.setenv(name, setting)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: value))
    return value


def _home_environment(value):
    return {
        "HOME": str(value),
        "USERPROFILE": str(value),
        "HOMEPATH": str(value),
        "XDG_DATA_HOME": str(value / ".local" / "share"),
        "XDG_CONFIG_HOME": str(value / ".config"),
        "XDG_CACHE_HOME": str(value / ".cache"),
        "APPDATA": str(value / "AppData" / "Roaming"),
        "LOCALAPPDATA": str(value / "AppData" / "Local"),
    }
