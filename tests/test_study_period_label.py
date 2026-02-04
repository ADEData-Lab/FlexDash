"""
Guardrail tests to keep study-period labelling consistent.
"""

from pathlib import Path


FORBIDDEN = ["2024" + "-2025", "2024" + "\u2013" + "2025"]


def test_no_legacy_study_period_strings_in_repo():
    root = Path(__file__).parent.parent
    exts = {".py", ".js", ".html", ".yaml", ".yml", ".md", ".json"}
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in exts:
            continue
        # Skip generated outputs
        if "dashboard\\data" in str(path) or "data\\processed" in str(path):
            continue
        content = path.read_text(encoding="utf-8", errors="ignore")
        for bad in FORBIDDEN:
            assert bad not in content, f"Found legacy study period label {bad!r} in {path}"
