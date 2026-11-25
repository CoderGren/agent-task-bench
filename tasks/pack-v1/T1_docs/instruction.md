The file DEVELOPMENT.md lists the test commands that CI runs, but it omits three local-only suites.

Add a short heading "Other script suites (not in CI)" and list these exact commands, each on its own line in a fenced code block:

python3 -m unittest scripts/test_backup.py
python3 -m unittest scripts/test_dns.py
python3 -m unittest scripts/test_guard.py

Add one sentence saying these suites are not in the Checks workflow. Do not change anything else in the file. Do not edit any other file.
