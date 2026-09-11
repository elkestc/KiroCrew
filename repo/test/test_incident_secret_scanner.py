"""The incident scanner must report fingerprints without reproducing values."""

import hashlib
import json
import subprocess
import sys
from pathlib import Path


def test_recursive_scan_redacts_values_and_names_and_skips_stores_and_links(tmp_path):
    scanner = Path(__file__).resolve().parents[1] / "scripts/scan_incident_secrets.py"
    root = tmp_path / "scan-root"
    nested = root / "nested"
    nested.mkdir(parents=True)
    value = "SYNTHETIC_ONLY_abcdefghijklmnopqrstuvwxyz0123456789"
    file_name = "SYNTHETIC_NAME_abcdefghijklmnopqrstuvwxyz0123456789"
    (nested / file_name).write_text("api_key=" + value + "\n", encoding="utf-8")
    outside = tmp_path / "external-fake-data"
    outside.mkdir()
    target = outside / "sentinel"
    target.write_text("EXTERNAL_DISPOSABLE_ONLY", encoding="utf-8")
    (root / "linked").symlink_to(outside, target_is_directory=True)
    store = root / ".AWS"
    store.mkdir()
    (store / "credentials").write_text("FAKE_STORE_MUST_BE_SKIPPED", encoding="utf-8")
    report = tmp_path / "redacted.jsonl"
    result = subprocess.run(
        [sys.executable, str(scanner), "--root", str(root), "--output", str(report)],
        cwd=tmp_path,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode == 0
    encoded_report = report.read_text(encoding="utf-8")
    combined = result.stdout + result.stderr + encoded_report.encode("utf-8")
    for forbidden in (value, file_name, "EXTERNAL_DISPOSABLE_ONLY", "FAKE_STORE_MUST_BE_SKIPPED"):
        assert forbidden.encode("utf-8") not in combined
    records = [json.loads(line) for line in encoded_report.splitlines()]
    assert any(row.get("sha256") == hashlib.sha256(value.encode()).hexdigest() for row in records)
    summary = records[-1]["summary"]
    assert summary["files_scanned"] == 1
    assert len(summary["skipped"]) == 2
    assert summary["read_errors"] == 0
    assert target.read_text(encoding="utf-8") == "EXTERNAL_DISPOSABLE_ONLY"


def test_explicit_credential_store_root_is_refused_before_traversal(tmp_path):
    scanner = Path(__file__).resolve().parents[1] / "scripts/scan_incident_secrets.py"
    # The nonexistent store is deliberate: refusing it must not require walking
    # into a credential store or opening a credential file to classify the root.
    report = tmp_path / "refused.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(scanner),
            "--root",
            str(tmp_path / ".aws"),
            "--output",
            str(report),
        ],
        cwd=tmp_path,
        capture_output=True,
        timeout=15,
        check=False,
    )
    assert result.returncode != 0
    assert result.stderr.strip() == b"Credential-store scan root refused"
    assert not report.read_bytes()
