#!/usr/bin/env python3
"""
Checks that all environment variables referenced in backend config
are documented in env-examples/dev/.env.example.

Parses config.py using AST to catch these patterns:
  - os.environ.get("KEY")
  - os.environ["KEY"]
  - os.getenv("KEY")
"""

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = REPO_ROOT / "backend" / "app" / "core" / "config.py"
ENV_EXAMPLE = REPO_ROOT / "env-examples" / "dev" / ".env.example"
ENV_EXAMPLE_DISPLAY = "env-examples/dev/.env.example"


def extract_env_vars_from_config(filepath: Path) -> set[str]:
    """Extract all env var names referenced in config.py via AST."""
    source = filepath.read_text(encoding="utf-8")
    tree = ast.parse(source)
    found = set()

    for node in ast.walk(tree):
        # os.environ.get("KEY") or os.environ.get("KEY", default)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in ("get",)
            and isinstance(node.func.value, ast.Attribute)
            and node.func.value.attr == "environ"
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "os"
        ):
            if node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str):
                    found.add(value)

        # os.environ["KEY"]
        if (
            isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Attribute)
            and node.value.attr == "environ"
            and isinstance(node.value.value, ast.Name)
            and node.value.value.id == "os"
            and isinstance(node.slice, ast.Constant)
        ):
            value = node.slice.value
            if isinstance(value, str):
                found.add(value)

        # os.getenv("KEY") or os.getenv("KEY", default)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "getenv"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
        ):
            if node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str):
                    found.add(value)

        # _env_bool("KEY", default)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_env_bool":
            if node.args and isinstance(node.args[0], ast.Constant):
                value = node.args[0].value
                if isinstance(value, str):
                    found.add(value)

    return found


def extract_keys_from_env_example(filepath: Path) -> set[str]:
    """Extract all documented variable names from env example template."""
    keys = set()
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key = line.split("=", 1)[0].strip()
        if key.startswith("export "):
            key = key[len("export "):].strip()
        if key:
            keys.add(key)
    return keys


def main():
    if not CONFIG_FILE.exists():
        print(f"❌ Config file not found: {CONFIG_FILE}")
        sys.exit(1)

    if not ENV_EXAMPLE.exists():
        print(f"❌ {ENV_EXAMPLE_DISPLAY} not found: {ENV_EXAMPLE}")
        sys.exit(1)

    print(f"📄 Scanning: {CONFIG_FILE}")
    print(f"📄 Checking against: {ENV_EXAMPLE}")

    config_vars = extract_env_vars_from_config(CONFIG_FILE)
    example_keys = extract_keys_from_env_example(ENV_EXAMPLE)

    print(f"🔍 Vars found in config: {sorted(config_vars)}")

    # These are intentionally internal or auto-set — skip them
    skip = {
        "HOME", "PATH", "USER", "PWD", "SHELL",  # system vars
        "PYTHONPATH", "VIRTUAL_ENV",               # python runtime
    }
    config_vars -= skip

    missing = config_vars - example_keys

    if missing:
        print(f"❌ The following env vars are used in config.py but missing from {ENV_EXAMPLE_DISPLAY}:\n")
        for key in sorted(missing):
            print(f"  - {key}")
        print(f"\nAdd them to {ENV_EXAMPLE_DISPLAY} with a description before merging.")
        print("Run with --suggest to see placeholder lines you can copy.")
        if "--suggest" in sys.argv:
            print(f"\nSuggested additions for {ENV_EXAMPLE_DISPLAY}:")
            for key in sorted(missing):
                print(f"\n# TODO: Add description for {key}")
                print(f"{key}=")
        sys.exit(1)
    else:
        print(f"✅ {ENV_EXAMPLE_DISPLAY} is in sync ({len(config_vars)} env vars checked)")
        sys.exit(0)


if __name__ == "__main__":
    main()