"""Prepare disposable repository metadata, then exec tests or a checker offline."""

import json
import os
import subprocess
import sys
from pathlib import Path

from test_isolation import require_isolated_environment

test_root = Path(require_isolated_environment().root)
subprocess.run(
    [
        "git",
        "-c",
        "core.hooksPath=/dev/null",
        "init",
        "--template=",
        "--initial-branch=isolated-fixture",
        ".",
    ],
    cwd=test_root / "repo",
    capture_output=True,
    check=True,
)
# A synthetic index/commit lets repository inventory tests inspect all copied
# source files. No history, remotes, credentials or hooks come from the host.
for arguments in (
    ["add", "--force", "--all", "--", "."],
    ["commit", "--quiet", "-m", "Disposable source fixture"],
):
    subprocess.run(
        [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "-c",
            "core.autocrlf=false",
            "-c",
            "commit.gpgsign=false",
            "-c",
            "user.name=Disposable Test",
            "-c",
            "user.email=test@invalid",
            *arguments,
        ],
        cwd=test_root / "repo",
        capture_output=True,
        check=True,
    )
if sys.argv[1:2] == ["--command-file"]:
    command_path = Path(sys.argv[2])
    require_isolated_environment().validate(command_path)
    command = json.loads(command_path.read_text(encoding="utf-8"))
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(value, str) and value for value in command)
    ):
        raise SystemExit("Expected a nonempty isolated command")
    os.execvp(command[0], command)
os.execv(sys.executable, [sys.executable, "-m", "pytest", *sys.argv[1:]])
