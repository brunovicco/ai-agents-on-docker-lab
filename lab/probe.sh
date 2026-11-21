#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
sbx env exec lab/sbxenv.yaml -- python3 -c '
from pathlib import Path
import errno
import tempfile
with tempfile.TemporaryFile(dir=".") as work:
    work.write(b"workspace-write")
try:
    handle = Path("/forecast/day.json").open("r+b")
except OSError as exc:
    if exc.errno not in (errno.EROFS, errno.EACCES, errno.EPERM):
        raise
else:
    handle.close()
    raise SystemExit("FAIL: forecast opened for writing")
if Path("/lab-src").exists():
    raise SystemExit("FAIL: repository source is mounted")
print("PASS: writable desk, read-only forecast, no repository source")
'
# The kit denies all runtime egress, including hosts that the global policy allows.
sbx policy check network --sandbox solar-dispatch github.com
