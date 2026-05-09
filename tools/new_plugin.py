#!/usr/bin/env python3
"""Create a new MA3 Lua plugin project from a scaffold template."""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path
from typing import Dict, Sequence

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"


def snake_case(name: str) -> str:
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = re.sub(r"[^A-Za-z0-9]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("_")
    return name.lower() or "plugin"


def copy_template(src: Path, dst: Path, replacements: Dict[str, str]) -> None:
    if dst.exists():
        raise RuntimeError(f"Destination already exists: {dst}")

    for path in src.rglob("*"):
        rel = path.relative_to(src)
        target = dst / rel

        # Always create empty directories such as build/ and dist/.
        if path.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        target.parent.mkdir(parents=True, exist_ok=True)
        data = path.read_bytes()

        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError:
            target.write_bytes(data)
            continue

        for key, value in replacements.items():
            text = text.replace("{{" + key + "}}", value)
        target.write_text(text.replace("\r\n", "\n").replace("\r", "\n"), encoding="utf-8")


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a new MA3 Lua plugin project.")
    parser.add_argument("name", help="Plugin project name, e.g. DeskLock")
    parser.add_argument("--display-name", help="MA3 display name, defaults to name")
    parser.add_argument("--author", default="JL", help="Author name")
    parser.add_argument("--plugin-subdir", help="MA3 lib_plugins subdir, defaults to jl_<snake_name>")
    parser.add_argument("--template", default="basic", help="Template name")
    parser.add_argument("--output", default=".", help="Parent output directory")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    template_dir = TEMPLATES / args.template
    if not template_dir.exists():
        print(f"[ERROR] template not found: {template_dir}", file=sys.stderr)
        return 2

    plugin_name = args.name
    display_name = args.display_name or plugin_name
    plugin_subdir = args.plugin_subdir or f"jl_{snake_case(plugin_name)}"
    dst = Path(args.output).expanduser().resolve() / plugin_name

    replacements = {
        "PLUGIN_NAME": plugin_name,
        "DISPLAY_NAME": display_name,
        "AUTHOR": args.author,
        "PLUGIN_SUBDIR": plugin_subdir,
        "PLUGIN_SNAKE": snake_case(plugin_name),
    }

    try:
        copy_template(template_dir, dst, replacements)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2

    print(f"[OK] created {dst}")
    print("Next:")
    print(f"  cd {dst}")
    print("  python3 tools/build.py")
    print("  python3 tools/docgen.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
