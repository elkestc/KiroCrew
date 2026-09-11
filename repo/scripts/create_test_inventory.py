"""Inventory source names only, using the native Git for this checkout."""

import argparse
import json
import stat
import subprocess
import tarfile
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--source", required=True)
parser.add_argument("--output", required=True)
parser.add_argument("--archive")
args = parser.parse_args()
original_root = Path(args.source)
if ".." in original_root.parts:
    raise SystemExit("Source path escapes checkout")
root = original_root.absolute()
checked = set()
for parent in (*reversed(root.parents), root):
    attributes = parent.lstat()
    if stat.S_ISLNK(attributes.st_mode) or getattr(attributes, "st_file_attributes", 0) & 0x400:
        raise SystemExit("Linked source path refused")
    checked.add(parent)
root = root.resolve(strict=True)
result = subprocess.run(
    ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
    cwd=root,
    capture_output=True,
    check=True,
)
names = [name.decode("utf-8") for name in result.stdout.split(b"\0") if name]
Path(args.output).write_text(json.dumps(names) + "\n", encoding="utf-8")
if args.archive:
    indexed = subprocess.run(
        ["git", "ls-files", "--stage", "-z"], cwd=root, capture_output=True, check=True
    )
    executable = {
        record.split(b"\t", 1)[1].decode("utf-8")
        for record in indexed.stdout.split(b"\0")
        if record.startswith(b"100755 ")
    }
    with tarfile.open(args.archive, "w") as archive:
        for name in names:
            relative = Path(name)
            if relative.is_absolute() or ".." in relative.parts:
                raise SystemExit("Source path escapes checkout")
            path = root / name
            for parent in (*reversed(path.parents), path):
                if parent in checked:
                    continue
                attributes = parent.lstat()
                if (
                    stat.S_ISLNK(attributes.st_mode)
                    or getattr(attributes, "st_file_attributes", 0) & 0x400
                ):
                    raise SystemExit("Linked source path refused")
                checked.add(parent)
            if not path.resolve(strict=True).is_relative_to(root):
                raise SystemExit("Resolved source path escapes checkout")
            if path.is_file():
                info = archive.gettarinfo(str(path), arcname=name)
                info.mode = 0o755 if name in executable else 0o644
                with path.open("rb") as stream:
                    archive.addfile(info, stream)
print(f"Inventoried {len(names)} source files")
