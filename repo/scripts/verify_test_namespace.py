"""Verify the launched namespace without touching any host credential path."""

import json
import os
import socket
from pathlib import Path

from test_isolation import fake_home_path, require_isolated_environment

root = require_isolated_environment()
home = fake_home_path()
network_refused = False
try:
    with socket.socket() as sock:
        sock.settimeout(1)
        sock.connect(("192.0.2.1", 443))
except OSError:
    network_refused = True
assert network_refused
assert not any(Path(p).exists() for p in ("/home", "/mnt", "/root", "/run/WSL"))
result = {
    "test_root": root.root,
    "fake_home": str(home),
    "network_refused": network_refused,
    "interfaces": socket.if_nameindex(),
    "environment_names": sorted(os.environ),
    "mountinfo": Path("/proc/self/mountinfo").read_text(encoding="utf-8"),
}
Path("/test-root/results/namespace.json").write_text(
    json.dumps(result, indent=2) + "\n", encoding="utf-8"
)
print("namespace checks passed")
