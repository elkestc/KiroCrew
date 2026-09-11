"""Read-only recursive scan; output locations, rule IDs and SHA-256 only.

Never opens links/reparse points or credential stores. Reports candidates, not
confirmed credentials. Compressed/encrypted data needs a separate decoded scan.
"""

import argparse
import hashlib
import json
import math
import os
import re
import stat
from collections import Counter
from pathlib import Path

TOKEN = re.compile(rb"(?<![A-Za-z0-9_])[A-Za-z0-9_+/=#.-]{32,256}(?![A-Za-z0-9_])")
ASSIGNMENT = re.compile(
    rb"(?i)(?:aws_secret_access_key|aws_access_key_id|api[_-]?key|access[_-]?token|secret[_-]?key|password)[\"']?\s*[:=]\s*[\"']?([^\s\"'<>,;]{8,256})"
)
STORE_NAMES = {".aws", ".ssh", ".gnupg"}
OPAQUE_SUFFIXES = {".zip", ".gz", ".xz", ".7z", ".whl", ".pack", ".pdf"}


def fingerprint(value):
    return hashlib.sha256(value).hexdigest()


def safe_location(path):
    return re.sub(
        r"[A-Za-z0-9_+=#-]{32,}",
        lambda m: "[name-sha256:" + fingerprint(m[0].encode())[:16] + "]",
        str(path),
    )


def linked(path):
    info = os.lstat(path)
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def walk(root, skipped):
    for current, dirs, files in os.walk(root, followlinks=False):
        for name in list(dirs):
            candidate = Path(current) / name
            if name.casefold() in STORE_NAMES or linked(candidate):
                dirs.remove(name)
                skipped.append(
                    {"location": safe_location(candidate), "reason": "credential-store-or-link"}
                )
        for name in files:
            path = Path(current) / name
            if linked(path):
                skipped.append({"location": safe_location(path), "reason": "link"})
            else:
                yield path


def scan(path):
    seen = set()
    offset = 0
    overlap = b""
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            data = overlap + chunk
            base = offset - len(overlap)
            candidates = [
                (m.start(1), m[1], "credential-assignment") for m in ASSIGNMENT.finditer(data)
            ]
            for match in TOKEN.finditer(data):
                value = match[0]
                counts = Counter(value)
                entropy = -sum(n / len(value) * math.log2(n / len(value)) for n in counts.values())
                if entropy >= 4.2 or re.fullmatch(rb"[a-fA-F0-9]{32,64}", value):
                    candidates.append((match.start(), value, "token-or-digest"))
            for position, value, rule in candidates:
                key = base + position, rule
                if key not in seen:
                    seen.add(key)
                    yield {
                        "location": safe_location(path),
                        "byte_offset": key[0],
                        "rule": rule,
                        "sha256": fingerprint(value),
                    }
            offset += len(chunk)
            overlap = data[-512:]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output).absolute()
    skipped, opaque = [], []
    files = hits = errors = 0
    with output.open("x", encoding="utf-8") as report:
        for raw in args.root:
            root = Path(raw).absolute()
            if any(p.name.casefold() in STORE_NAMES for p in (root, *root.parents)):
                raise SystemExit("Credential-store scan root refused")
            if any(linked(p) for p in (root, *root.parents)):
                raise SystemExit("Scan root contains a link; refused")
            for path in walk(root, skipped):
                if path.absolute() == output:
                    continue
                files += 1
                if path.suffix.lower() in OPAQUE_SUFFIXES:
                    opaque.append(safe_location(path))
                try:
                    for finding in scan(path):
                        report.write(json.dumps(finding) + "\n")
                        hits += 1
                except OSError:
                    errors += 1
                    skipped.append({"location": safe_location(path), "reason": "unreadable"})
        summary = {
            "files_scanned": files,
            "candidate_locations": hits,
            "read_errors": errors,
            "skipped": skipped,
            "opaque_files": opaque,
            "claim": "candidate scan; no assertion that remaining transcripts or opaque files are secret-free",
        }
        report.write(json.dumps({"summary": summary}) + "\n")
    print(
        json.dumps(
            {
                "files_scanned": files,
                "candidate_locations": hits,
                "read_errors": errors,
                "skipped_count": len(skipped),
                "opaque_count": len(opaque),
                "report": str(output),
            }
        )
    )


if __name__ == "__main__":
    main()
