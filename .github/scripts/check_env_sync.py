#!/usr/bin/env python3
"""
Checks that all environment variables referenced in backend config
are documented in env example templates (dev and/or beta).

Parses config.py using AST to catch these patterns:
  - os.environ.get("KEY")
  - os.environ["KEY"]
  - os.getenv("KEY")
  - _env_bool("KEY", ...)
"""

import ast
import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent
CONFIG_FILE = REPO_ROOT / "backend" / "app" / "core" / "config.py"
ENV_EXAMPLES = {
    "dev": REPO_ROOT / "env-examples" / "dev" / ".env.example",
    "beta": REPO_ROOT / "env-examples" / "beta" / ".env.example",
}
# Order for --all-templates (stable, human-friendly).
_ALL_TEMPLATE_ORDER = ("dev", "beta")

# These are intentionally internal or auto-set — skip them
_SKIP = {
    "HOME", "PATH", "USER", "PWD", "SHELL",  # system vars
    "PYTHONPATH", "VIRTUAL_ENV",  # python runtime
}


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
            key = key[len("export ") :].strip()
        if key:
            keys.add(key)
    return keys


def check_template(template: str, suggest: bool) -> int:
    """Return 0 if template contains all config.py keys, else 1."""
    env_example = ENV_EXAMPLES[template]
    env_example_display = f"env-examples/{template}/.env.example"

    if not CONFIG_FILE.exists():
        print(f"ERROR: Config file not found: {CONFIG_FILE}")
        return 1

    if not env_example.exists():
        print(f"ERROR: {env_example_display} not found: {env_example}")
        return 1

    print(f"Scanning: {CONFIG_FILE}")
    print(f"Checking against: {env_example}")

    config_vars = extract_env_vars_from_config(CONFIG_FILE) - _SKIP
    example_keys = extract_keys_from_env_example(env_example)

    print(f"Vars found in config: {sorted(config_vars)}")

    missing = config_vars - example_keys

    if missing:
        print(f"ERROR: The following env vars are used in config.py but missing from {env_example_display}:\n")
        for key in sorted(missing):
            print(f"  - {key}")
        print(f"\nAdd them to {env_example_display} with a description before merging.")
        print("Run with --suggest to see placeholder lines you can copy.")
        if suggest:
            print(f"\nSuggested additions for {env_example_display}:")
            for key in sorted(missing):
                print(f"\n# TODO: Add description for {key}")
                print(f"{key}=")
        return 1

    print(f"OK: {env_example_display} is in sync ({len(config_vars)} env vars checked)")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check env example sync with backend config env usage.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--template",
        choices=sorted(ENV_EXAMPLES.keys()),
        help="Single template to validate (default: dev when --all-templates is not used).",
    )
    group.add_argument(
        "--all-templates",
        action="store_true",
        help="Validate env-examples/dev and env-examples/beta against config.py.",
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="Print suggested placeholder lines for missing keys.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.all_templates:
        templates = [name for name in _ALL_TEMPLATE_ORDER if name in ENV_EXAMPLES]
    else:
        templates = [args.template or "dev"]

    exit_code = 0
    for i, name in enumerate(templates):
        if len(templates) > 1:
            print(f"\n--- Template: {name} ({i + 1}/{len(templates)}) ---\n")
        rc = check_template(name, args.suggest)
        if rc != 0:
            exit_code = 1

    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
