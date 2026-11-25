from pathlib import Path
text = Path("DEVELOPMENT.md").read_text(encoding="utf-8")
assert "python3 -m unittest discover -s src -p 'test_*.py'" in text
assert "The Checks workflow is the release list." in text
assert "python3 -m unittest scripts/test_backup.py" in text
assert "python3 -m unittest scripts/test_dns.py" in text
assert "python3 -m unittest scripts/test_guard.py" in text
assert "not in the Checks workflow" in text or "aren't in the Checks workflow" in text or "are not in the Checks workflow" in text
print("ok")
