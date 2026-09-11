"""Check an explicitly inventoried source copy without changing its bytes."""

import json
import subprocess
import sys
from pathlib import Path

targets = json.loads(Path("/test-root/results/quality-targets.json").read_text(encoding="utf-8"))
results = {}
for tool, args in (
    ("isort", ["--check-only"]),
    ("black", ["--check", "--target-version", "py310"]),
    ("flake8", []),
):
    result = subprocess.run([sys.executable, "-m", tool, *args, *targets], check=False)
    results[tool] = result.returncode
for label, command in (
    ("flake8_all", ["-m", "flake8", "src/kiro_crew", "test"]),
    ("mypy", ["-m", "mypy", "src/kiro_crew"]),
    ("docs", ["scripts/docs_lint.py"]),
    ("subprocess_encoding", ["scripts/check_subprocess_encoding.py"]),
):
    results[label] = subprocess.run([sys.executable, *command], check=False).returncode
Path("/test-root/results/quality.json").write_text(json.dumps(results) + "\n", encoding="utf-8")
raise SystemExit(int(any(results.values())))
