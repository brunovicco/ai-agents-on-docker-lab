"""Validate the Docker Agent configuration against the official docker-agent JSON schema.

Usage: python scripts/validate_agent.py SCHEMA_FILE [AGENT_FILE]

SCHEMA_FILE is agent-schema.json from https://github.com/docker/docker-agent. CI pins it to a
commit.
"""

import json
import sys
from pathlib import Path

import yaml
from jsonschema import validators


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    schema = json.loads(Path(sys.argv[1]).read_text())
    agent_file = Path(sys.argv[2] if len(sys.argv) == 3 else "lab/agent/solar-planner.yaml")
    validator = validators.validator_for(schema)(schema)
    config = yaml.safe_load(agent_file.read_text())
    errors = sorted(validator.iter_errors(config), key=lambda error: list(error.path))
    for error in errors:
        location = "/".join(str(part) for part in error.path) or "(root)"
        print(f"{agent_file}: {location}: {error.message}", file=sys.stderr)
    if errors:
        raise SystemExit(1)
    print(f"{agent_file}: valid Docker Agent configuration")


if __name__ == "__main__":
    main()
