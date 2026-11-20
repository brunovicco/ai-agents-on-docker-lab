"""Validate the sandbox kit descriptor against the official Docker Sandbox Kit v3 schema.

Usage: python scripts/validate_kit.py SPEC_DIR [KIT_FILE]

SPEC_DIR is a checkout of https://github.com/docker/sandbox-kit-spec. CI pins it to a commit.
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import validators
from referencing import Registry, Resource


def main() -> None:
    if len(sys.argv) not in (2, 3):
        raise SystemExit(__doc__)
    schema_dir = Path(sys.argv[1]) / "schema"
    kit_file = Path(sys.argv[2] if len(sys.argv) == 3 else "lab/solar-kit/solar-kit.yaml")

    def retrieve(uri: str) -> Resource[Any]:
        # Capability schemas are referenced by paths relative to the schema directory.
        relative = uri.split("schema/", 1)[-1].lstrip("./")
        path = (schema_dir / relative).resolve()
        if schema_dir.resolve() not in path.parents:
            raise ValueError(f"Schema reference outside the spec: {uri}")
        return Resource.from_contents(json.loads(path.read_text()))

    schema = json.loads((schema_dir / "kit.schema.json").read_text())
    validator = validators.validator_for(schema)(schema, registry=Registry(retrieve=retrieve))
    kit = yaml.safe_load(kit_file.read_text())
    errors = sorted(validator.iter_errors(kit), key=lambda error: list(error.path))
    for error in errors:
        location = "/".join(str(part) for part in error.path) or "(root)"
        print(f"{kit_file}: {location}: {error.message}", file=sys.stderr)
    if errors:
        raise SystemExit(1)
    print(f"{kit_file}: valid Docker Sandbox Kit v3 descriptor")


if __name__ == "__main__":
    main()
