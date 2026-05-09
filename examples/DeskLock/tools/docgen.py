#!/usr/bin/env python3
"""
MA3 Lua Plugin Scaffold Documentation Generator

Generate Markdown API documentation from Lua source comments.

Supported comment style:

    --- Short description.
    --- More detail.
    ---@param name string The user-facing name.
    ---@return boolean ok True on success.
    function M.foo(name)
    end

    --- Quote a value for MA3 command strings.
    ---@param value any
    ---@return string quoted
    function Cmd.quote(value)
    end

The script intentionally has no third-party Python dependencies.
"""

from __future__ import annotations

import argparse
import json
import dataclasses
import datetime as _dt
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


DEFAULT_ROOTS = ["src", "ma3lib", "vendor"]
DEFAULT_OUT = "docs/API.md"


@dataclasses.dataclass
class Annotation:
    tag: str
    value: str


@dataclasses.dataclass
class DocBlock:
    description: List[str]
    annotations: List[Annotation]
    start_line: int
    end_line: int

    def has_tag(self, *tags: str) -> bool:
        lookup = {t.lower().lstrip("@") for t in tags}
        for ann in self.annotations:
            if ann.tag.lower().lstrip("@") in lookup:
                return True
        return False

    def first_tag_value(self, *tags: str) -> Optional[str]:
        lookup = {t.lower().lstrip("@") for t in tags}
        for ann in self.annotations:
            if ann.tag.lower().lstrip("@") in lookup:
                return ann.value
        return None


@dataclasses.dataclass
class ParamDoc:
    name: str
    type_name: str = ""
    description: str = ""


@dataclasses.dataclass
class ReturnDoc:
    type_name: str = ""
    name: str = ""
    description: str = ""


@dataclasses.dataclass
class SymbolDoc:
    kind: str
    name: str
    signature: str
    line: int
    doc: Optional[DocBlock]
    params: List[ParamDoc]
    returns: List[ReturnDoc]
    visibility: str = "public"


@dataclasses.dataclass
class ModuleDoc:
    module_name: str
    file_path: Path
    rel_path: Path
    doc: Optional[DocBlock]
    symbols: List[SymbolDoc]


# function M.foo(a, b)
RE_FUNCTION_DECL = re.compile(
    r"^\s*function\s+([A-Za-z_][\w\.\:]*)(?:\s*)\(([^)]*)\)"
)

# local function foo(a, b)
RE_LOCAL_FUNCTION = re.compile(
    r"^\s*local\s+function\s+([A-Za-z_][\w]*)\s*\(([^)]*)\)"
)

# M.foo = function(a, b)
RE_ASSIGN_FUNCTION = re.compile(
    r"^\s*([A-Za-z_][\w\.\:]*)\s*=\s*function\s*\(([^)]*)\)"
)

# local M = {}
RE_LOCAL_TABLE = re.compile(r"^\s*local\s+([A-Za-z_][\w]*)\s*=\s*\{\s*\}\s*$")

# M.CONST = value / local CONST = value
RE_ASSIGN_VALUE = re.compile(
    r"^\s*(?:(local)\s+)?([A-Za-z_][\w]*(?:\.[A-Za-z_][\w]*)*)\s*=\s*(.+?)\s*$"
)

# return M
RE_RETURN_NAME = re.compile(r"^\s*return\s+([A-Za-z_][\w]*)\s*$")


class DocGenError(RuntimeError):
    pass


def normalize_newlines(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_lua_comment_prefix(line: str) -> Optional[str]:
    """Return text after a Lua doc comment prefix, or None."""
    stripped = line.lstrip()
    if stripped.startswith("---"):
        # Keep one optional leading space after ---.
        content = stripped[3:]
        if content.startswith(" "):
            content = content[1:]
        return content.rstrip()
    return None


def collect_doc_blocks(lines: Sequence[str]) -> dict[int, DocBlock]:
    """Map the first non-doc line after a doc block to the DocBlock."""
    blocks: dict[int, DocBlock] = {}
    current: List[Tuple[int, str]] = []

    for idx, line in enumerate(lines, start=1):
        content = strip_lua_comment_prefix(line)
        if content is not None:
            current.append((idx, content))
            continue

        if current:
            # Blank lines between a doc block and a declaration break the binding.
            if line.strip() == "":
                current = []
                continue

            description: List[str] = []
            annotations: List[Annotation] = []
            for _line_no, text in current:
                if text.startswith("@"):
                    parts = text[1:].split(None, 1)
                    tag = parts[0] if parts else ""
                    value = parts[1] if len(parts) > 1 else ""
                    annotations.append(Annotation(tag=tag, value=value.strip()))
                else:
                    description.append(text)

            blocks[idx] = DocBlock(
                description=trim_empty_edges(description),
                annotations=annotations,
                start_line=current[0][0],
                end_line=current[-1][0],
            )
            current = []

    return blocks


def trim_empty_edges(lines: List[str]) -> List[str]:
    while lines and lines[0].strip() == "":
        lines.pop(0)
    while lines and lines[-1].strip() == "":
        lines.pop()
    return lines


def parse_args_list(arg_text: str) -> List[str]:
    arg_text = arg_text.strip()
    if not arg_text:
        return []
    return [a.strip() for a in arg_text.split(",") if a.strip()]


def parse_param_annotation(value: str) -> ParamDoc:
    """
    Parse LuaLS/LuaCATS-like @param text.

    Examples:
        name string The value name
        value any
        opts table|nil Optional settings
        ... any Extra args
    """
    value = value.strip()
    if not value:
        return ParamDoc(name="")

    parts = value.split(None, 2)
    if len(parts) == 1:
        return ParamDoc(name=parts[0])
    if len(parts) == 2:
        return ParamDoc(name=parts[0], type_name=parts[1])
    return ParamDoc(name=parts[0], type_name=parts[1], description=parts[2])


def parse_return_annotation(value: str) -> ReturnDoc:
    """
    Parse @return text.

    Examples:
        boolean ok True on success
        string quoted
        nil
    """
    value = value.strip()
    if not value:
        return ReturnDoc()

    parts = value.split(None, 2)
    if len(parts) == 1:
        return ReturnDoc(type_name=parts[0])
    if len(parts) == 2:
        # Heuristic: second token can be a return name.
        return ReturnDoc(type_name=parts[0], name=parts[1])
    return ReturnDoc(type_name=parts[0], name=parts[1], description=parts[2])


def symbol_visibility(doc: Optional[DocBlock], declaration_name: str) -> str:
    if doc and doc.has_tag("private", "local"):
        return "private"
    if declaration_name.startswith("_") or "." in declaration_name and declaration_name.split(".")[-1].startswith("_"):
        return "private"
    return "public"


def build_signature(name: str, args: str) -> str:
    return f"{name}({', '.join(parse_args_list(args))})"


def infer_module_name(file_path: Path, project_root: Path, roots: Sequence[str]) -> str:
    rel = file_path.relative_to(project_root)
    without_suffix = rel.with_suffix("")
    return ".".join(without_suffix.parts)


def find_returned_local_table(lines: Sequence[str]) -> Optional[str]:
    for line in reversed(lines):
        m = RE_RETURN_NAME.match(line)
        if m:
            return m.group(1)
    return None


def module_doc_from_file(path: Path, project_root: Path, roots: Sequence[str]) -> ModuleDoc:
    rel = path.relative_to(project_root)
    text = normalize_newlines(path.read_text(encoding="utf-8", errors="replace"))
    lines = text.split("\n")
    blocks = collect_doc_blocks(lines)

    module_name = infer_module_name(path, project_root, roots)
    module_block: Optional[DocBlock] = None
    symbols: List[SymbolDoc] = []

    returned_table = find_returned_local_table(lines)

    for idx, line in enumerate(lines, start=1):
        doc = blocks.get(idx)
        stripped = line.strip()

        # A top-of-file doc block annotated as @module documents the module itself.
        if doc and doc.has_tag("module"):
            module_block = doc
            continue

        match = RE_FUNCTION_DECL.match(line)
        if match:
            name, args = match.groups()
            symbols.append(make_symbol("function", name, args, idx, doc))
            continue

        match = RE_LOCAL_FUNCTION.match(line)
        if match:
            name, args = match.groups()
            # local function may still be exported indirectly, but default private.
            sym = make_symbol("function", name, args, idx, doc)
            if not (doc and doc.has_tag("public")):
                sym.visibility = "private"
            symbols.append(sym)
            continue

        match = RE_ASSIGN_FUNCTION.match(line)
        if match:
            name, args = match.groups()
            symbols.append(make_symbol("function", name, args, idx, doc))
            continue

        # Constants / fields are only documented if they have a doc block.
        if doc:
            match = RE_ASSIGN_VALUE.match(line)
            if match:
                is_local, name, value = match.groups()
                # Avoid documenting local module table declarations unless explicitly @class/module.
                if RE_LOCAL_TABLE.match(line) and not doc.has_tag("class", "field", "type", "public"):
                    continue
                kind = "field" if doc.has_tag("field") else "value"
                signature = f"{name} = {value.strip()}"
                visibility = "private" if is_local and not doc.has_tag("public") else symbol_visibility(doc, name)
                symbols.append(SymbolDoc(kind=kind, name=name, signature=signature, line=idx, doc=doc, params=[], returns=[], visibility=visibility))
                continue

    if module_block is None:
        module_block = find_leading_module_doc(lines, blocks)

    return ModuleDoc(module_name=module_name, file_path=path, rel_path=rel, doc=module_block, symbols=symbols)


def find_leading_module_doc(lines: Sequence[str], blocks: dict[int, DocBlock]) -> Optional[DocBlock]:
    """Use a leading @class or plain module doc if it appears before the first real code."""
    for idx, line in enumerate(lines, start=1):
        if idx in blocks:
            block = blocks[idx]
            if block.has_tag("class", "module"):
                return block
            # If it is attached to a local table declaration at top, treat it as module doc.
            if RE_LOCAL_TABLE.match(line):
                return block
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        break
    return None


def make_symbol(kind: str, name: str, args: str, line: int, doc: Optional[DocBlock]) -> SymbolDoc:
    params: List[ParamDoc] = []
    returns: List[ReturnDoc] = []
    if doc:
        for ann in doc.annotations:
            tag = ann.tag.lower()
            if tag == "param":
                param = parse_param_annotation(ann.value)
                if param.name:
                    params.append(param)
            elif tag in {"return", "returns"}:
                returns.append(parse_return_annotation(ann.value))

    return SymbolDoc(
        kind=kind,
        name=name,
        signature=build_signature(name, args),
        line=line,
        doc=doc,
        params=params,
        returns=returns,
        visibility=symbol_visibility(doc, name),
    )


def find_lua_files(project_root: Path, roots: Sequence[str]) -> List[Path]:
    files: List[Path] = []
    for root_name in roots:
        root = project_root / root_name
        if not root.exists():
            continue
        if root.is_file() and root.suffix == ".lua":
            files.append(root)
            continue
        files.extend(sorted(root.rglob("*.lua")))
    return sorted(set(files))


def markdown_escape(text: str) -> str:
    return text.replace("|", "\\|")


def format_description(doc: Optional[DocBlock]) -> str:
    if not doc or not doc.description:
        return ""
    return "\n".join(doc.description).strip()


def format_annotation_table(symbol: SymbolDoc) -> List[str]:
    out: List[str] = []
    if symbol.params:
        out.append("\n**Parameters**\n")
        out.append("| Name | Type | Description |")
        out.append("|---|---|---|")
        for p in symbol.params:
            out.append(f"| `{markdown_escape(p.name)}` | `{markdown_escape(p.type_name)}` | {markdown_escape(p.description)} |")

    if symbol.returns:
        out.append("\n**Returns**\n")
        out.append("| Type | Name | Description |")
        out.append("|---|---|---|")
        for r in symbol.returns:
            out.append(f"| `{markdown_escape(r.type_name)}` | `{markdown_escape(r.name)}` | {markdown_escape(r.description)} |")

    extra_annotations = []
    if symbol.doc:
        for ann in symbol.doc.annotations:
            tag = ann.tag.lower()
            if tag not in {"param", "return", "returns", "private", "local", "public"}:
                extra_annotations.append(ann)
    if extra_annotations:
        out.append("\n**Annotations**\n")
        out.append("| Tag | Value |")
        out.append("|---|---|")
        for ann in extra_annotations:
            out.append(f"| `@{markdown_escape(ann.tag)}` | {markdown_escape(ann.value)} |")

    return out


def render_markdown(
    modules: Sequence[ModuleDoc],
    title: str,
    include_private: bool,
    project_root: Path,
) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines: List[str] = []
    lines.append(f"# {title}")
    lines.append("")
    lines.append(f"Generated: `{now}`")
    lines.append("")
    lines.append("> This file is generated from Lua source comments. Do not edit it directly.")
    lines.append("")

    total_symbols = sum(
        1 for m in modules for s in m.symbols if include_private or s.visibility != "private"
    )
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Modules: `{len(modules)}`")
    lines.append(f"- Symbols: `{total_symbols}`")
    lines.append("")

    lines.append("## Modules")
    lines.append("")
    for module in modules:
        anchor = module.module_name.lower().replace(".", "").replace("_", "")
        lines.append(f"- [`{module.module_name}`](#{slug(module.module_name)}) — `{module.rel_path.as_posix()}`")
    lines.append("")

    for module in modules:
        visible_symbols = [s for s in module.symbols if include_private or s.visibility != "private"]
        lines.append(f"## `{module.module_name}`")
        lines.append("")
        lines.append(f"File: `{module.rel_path.as_posix()}`")
        lines.append("")

        desc = format_description(module.doc)
        if desc:
            lines.append(desc)
            lines.append("")

        if not visible_symbols:
            lines.append("No documented public symbols found.")
            lines.append("")
            continue

        lines.append("| Symbol | Kind | Line | Description |")
        lines.append("|---|---:|---:|---|")
        for sym in visible_symbols:
            desc_line = ""
            if sym.doc and sym.doc.description:
                desc_line = sym.doc.description[0]
            lines.append(
                f"| [`{markdown_escape(sym.name)}`](#{slug(module.module_name + '-' + sym.name)}) | {sym.kind} | {sym.line} | {markdown_escape(desc_line)} |"
            )
        lines.append("")

        for sym in visible_symbols:
            lines.append(f"### `{sym.name}`")
            lines.append("")
            lines.append(f"Line: `{sym.line}`")
            if sym.visibility == "private":
                lines.append("")
                lines.append("Visibility: `private`")
            lines.append("")
            lines.append("```lua")
            lines.append(sym.signature)
            lines.append("```")
            lines.append("")

            desc = format_description(sym.doc)
            if desc:
                lines.append(desc)
                lines.append("")

            lines.extend(format_annotation_table(sym))
            lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def slug(text: str) -> str:
    text = text.strip().lower()
    # GitHub-like enough for our generated anchors.
    text = re.sub(r"[`'\"()]+", "", text)
    text = re.sub(r"[^a-z0-9_\-.\u4e00-\u9fff]+", "-", text)
    text = text.replace(".", "")
    text = text.strip("-")
    return text


def validate_docs(modules: Sequence[ModuleDoc], include_private: bool) -> List[str]:
    warnings: List[str] = []
    for module in modules:
        for sym in module.symbols:
            if sym.visibility == "private" and not include_private:
                continue
            if sym.doc is None or not sym.doc.description:
                warnings.append(f"{module.rel_path}:{sym.line}: public {sym.kind} `{sym.name}` is missing description")
    return warnings



def guess_default_title(project_root: Path) -> str:
    """Guess documentation title from config/plugin.json, fallback to directory name."""
    config_path = project_root / "config" / "plugin.json"
    if config_path.exists():
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
            name = data.get("displayName") or data.get("name")
            if name:
                return f"{name} API"
        except Exception:
            pass
    return f"{project_root.name} API"


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate Markdown docs from Lua source comments.")
    parser.add_argument("--project-root", default=".", help="Project root directory. Default: current directory.")
    parser.add_argument("--roots", nargs="+", default=DEFAULT_ROOTS, help="Lua source roots to scan. Default: src ma3lib vendor.")
    parser.add_argument("--out", default=DEFAULT_OUT, help="Output Markdown path. Default: docs/API.md.")
    parser.add_argument("--title", default=None, help="Markdown title. Default: read config/plugin.json or use project directory name.")
    parser.add_argument("--include-private", action="store_true", help="Include symbols tagged @private or local functions.")
    parser.add_argument("--check", action="store_true", help="Fail if documented public symbols are missing descriptions.")
    parser.add_argument("--list", action="store_true", help="Print discovered modules and symbols without writing docs.")
    parser.add_argument("--quiet", action="store_true", help="Do not print missing-description warnings.")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).expanduser().resolve()
    if not project_root.exists():
        raise DocGenError(f"Project root does not exist: {project_root}")

    title = args.title or guess_default_title(project_root)

    files = find_lua_files(project_root, args.roots)
    if not files:
        raise DocGenError(f"No Lua files found under roots: {', '.join(args.roots)}")

    modules = [module_doc_from_file(path, project_root, args.roots) for path in files]
    modules.sort(key=lambda m: m.module_name)

    if args.list:
        for module in modules:
            print(f"{module.module_name}  ({module.rel_path.as_posix()})")
            for sym in module.symbols:
                if args.include_private or sym.visibility != "private":
                    print(f"  - {sym.kind}: {sym.signature} line={sym.line} visibility={sym.visibility}")
        return 0

    warnings = validate_docs(modules, include_private=args.include_private)
    if not args.quiet:
        for warning in warnings:
            print(f"[WARN] {warning}", file=sys.stderr)

    if args.check and warnings:
        print(f"[ERROR] documentation check failed: {len(warnings)} warning(s)", file=sys.stderr)
        return 2

    markdown = render_markdown(
        modules=modules,
        title=title,
        include_private=args.include_private,
        project_root=project_root,
    )

    out_path = (project_root / args.out).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(markdown, encoding="utf-8")
    print(f"[OK] docs: {out_path}")
    print(f"[OK] modules: {len(modules)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DocGenError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise SystemExit(1)
