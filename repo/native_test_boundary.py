"""Native OS checks for the disposable offline test launcher prototype.

The parent verifies the Windows container has no mounts and network mode none,
or applies the macOS default-deny profile. These checks fail closed before test
collection. They do not replace the parent OS boundary with a Python sandbox.
"""

import ctypes
import errno
import os
from pathlib import Path
import re
import socket
import sys


def verify_native_boundary():
    root = os.environ.get("KIROCREW_TEST_ROOT", "")
    if sys.platform == "win32":
        if root != "C:\\test-root":
            raise RuntimeError("Native test root is not launcher-owned")
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           r"SYSTEM\CurrentControlSet\Control") as key:
            value, kind = winreg.QueryValueEx(key, "ContainerType")
        if kind != winreg.REG_DWORD or not isinstance(value, int):
            raise RuntimeError("Windows container OS boundary is required")
        runtime = (str(Path(sys.base_prefix)), r"C:\Windows", r"C:\runtime")
    elif sys.platform == "darwin":
        if not re.fullmatch(r"/private/tmp/kct-[a-f0-9]{8}/test-root", root):
            raise RuntimeError("Native test root is not launcher-owned")
        library = ctypes.CDLL("/usr/lib/libsandbox.dylib")
        check = library.sandbox_check
        check.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int]
        check.restype = ctypes.c_int
        # Publicly used Darwin SPI: a null operation queries sandbox membership.
        if check(os.getpid(), None, 0) != 1:
            raise RuntimeError("macOS OS sandbox is required")
        runtime = ("/System", "/usr", "/bin", "/opt/homebrew",
                   "/Library/Developer/CommandLineTools", str(Path(sys.base_prefix)))
    else:
        raise RuntimeError("Unsupported native test boundary")
    # This is a newly created fake file outside the allowed root. Never probe a
    # credential path or a user profile to test whether the boundary holds.
    canary = os.environ.get("KIROCREW_TEST_HOST_CANARY", "")
    expected = str(Path(root).parent / "synthetic-host-sentinel")
    valid_canary = (re.fullmatch(r"C:\\kct-[a-f0-9]{8}\\synthetic-host-sentinel", canary)
                    if sys.platform == "win32" else canary == expected)
    if not valid_canary:
        raise RuntimeError("Synthetic host canary is required")
    for mode in ("rb", "r+b"):
        try:
            with open(canary, mode):
                pass
        except (PermissionError, FileNotFoundError):
            continue
        raise RuntimeError("Native host canary is accessible")
    try:
        with socket.socket() as connection:
            connection.settimeout(2)
            connection.connect(("192.0.2.1", 443))
    except OSError as error:
        if error.errno not in {
            errno.ENETUNREACH, errno.EHOSTUNREACH, errno.EPERM, errno.EACCES,
            errno.ENETDOWN, 10051, 10065, 10013, 10050,
        }:
            raise RuntimeError("Native offline network boundary was not proven") from None
    else:
        raise RuntimeError("Native offline network boundary is missing")
    return root, runtime
