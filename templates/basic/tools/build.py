#!/usr/bin/env python3
"""
MA3 Lua Plugin Builder

Python-only bundler for grandMA3 Lua plugin projects.
It scans static require("module.name") calls, bundles source modules into
one Lua program, then generates a grandMA3 UserPlugin XML file.

Modes:
  installed: write XML + external Lua file. ComponentLua has FileName/FilePath/Installed="Yes".
  embedded:  write XML with ComponentLua/FileContent Base64 blocks. No external Lua required.
"""

from __future__ import annotations

import argparse
import base64
import datetime as _dt
import html
import json
import platform
import re
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Set, Tuple


REQUIRE_LITERAL_RE = re.compile(r"require\s*\(\s*(['\"])([A-Za-z0-9_./-]+)\1\s*\)")
REQUIRE_ANY_RE = re.compile(r"require\s*\(")
GMA3_DIR_RE = re.compile(r"gma3_(\d+)\.(\d+)\.(\d+)(?:\.(\d+))?$")
XML_RAW_BLOCK_SIZE = 1024


class BuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class ModuleInfo:
    name: str
    path: Path
    relpath: str
    code: str


@dataclass(frozen=True)
class ImageAsset:
    name: str
    file: Path
    relfile: str
    filename: str
    appearance_name: str
    image_mode: str
    use_as_plugin_appearance: bool
    back_r: int
    back_g: int
    back_b: int
    back_alpha: int


def project_root_from_config(config_path: Path) -> Path:
    config_path = config_path.resolve()
    if config_path.parent.name == "config":
        return config_path.parent.parent
    return config_path.parent


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BuildError(f"Config file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise BuildError(f"Invalid JSON in {path}: {exc}") from exc


def detect_default_ma3_root() -> Path:
    system = platform.system()
    if system == "Windows":
        return Path(r"C:\ProgramData\MALightingTechnology")
    if system == "Darwin":
        return Path("~/MALightingTechnology").expanduser()
    if system == "Linux":
        return Path("~/MALightingTechnology").expanduser()
    raise BuildError(f"Unsupported OS: {system}")


def _version_tuple(path: Path) -> Tuple[int, int, int, int]:
    match = GMA3_DIR_RE.match(path.name)
    if not match:
        raise ValueError(path.name)
    nums = [int(x) if x is not None else 0 for x in match.groups()]
    return tuple(nums)  # type: ignore[return-value]


def list_gma3_dirs(ma3_root: Path) -> List[Path]:
    if not ma3_root.exists():
        raise BuildError(
            f"MA3 root does not exist: {ma3_root}. "
            "Use --ma3-root or --local."
        )
    candidates: List[Tuple[Tuple[int, int, int, int], Path]] = []
    for p in ma3_root.glob("gma3_*"):
        if not p.is_dir():
            continue
        if not GMA3_DIR_RE.match(p.name):
            continue
        candidates.append((_version_tuple(p), p))
    if not candidates:
        raise BuildError(
            f"No gma3_* directory found in {ma3_root}. "
            "Use --ma3-root, --ma3-version, --out, or --local."
        )
    candidates.sort(reverse=True)
    return [p for _, p in candidates]


def find_latest_gma3_dir(ma3_root: Path) -> Path:
    return list_gma3_dirs(ma3_root)[0]


def ma3_plugin_library_dir(ma3_root: Path, config: dict) -> Path:
    """Return the MA3 user plugin library folder.

    grandMA3 imports user plugin XML/Lua from:
        <MA3 root>/gma3_library/datapools/plugins

    This is intentionally NOT the versioned internal resource folder
    gma3_x.y.z/shared/resource/lib_plugins. FilePath/FileName in a
    ComponentLua are resolved inside this user plugin library.
    """
    ma3 = config.get("ma3", {})
    subdir = ma3.get("pluginSubdir") or ma3.get("componentFilePath") or config.get("name", "Plugin")
    return ma3_root / "gma3_library" / "datapools" / "plugins" / str(subdir)


def resolve_ma3_base_dirs(config: dict, args: argparse.Namespace) -> List[Path]:
    if args.out:
        # --out is XML-first: it names the exact XML path. Its parent is the output folder.
        return [Path(args.out).expanduser().resolve().parent]

    ma3_root = Path(args.ma3_root).expanduser() if args.ma3_root else detect_default_ma3_root()
    if not ma3_root.exists():
        raise BuildError(
            f"MA3 root does not exist: {ma3_root}. "
            "Use --ma3-root or --local."
        )

    # Plugin XML/Lua library is shared across installed gma3 versions, so
    # --ma3-version and --all-versions are ignored for XML-first output.
    return [ma3_plugin_library_dir(ma3_root, config)]


def xml_filename(config: dict) -> str:
    ma3 = config.get("ma3", {})
    return str(ma3.get("xmlFile") or f"{config.get('name', 'Plugin')}.xml")


def lua_filename(config: dict) -> str:
    ma3 = config.get("ma3", {})
    return str(ma3.get("luaFile") or ma3.get("outputFile") or f"{config.get('name', 'Plugin')}.lua")


def module_to_relative_path(module: str) -> Path:
    if not module or module.startswith(".") or ".." in module.split("."):
        raise BuildError(f"Invalid module name: {module!r}")
    return Path(*module.split(".")).with_suffix(".lua")


def resolve_module_to_file(project_root: Path, source_roots: Sequence[str], module: str) -> Path:
    rel_path = module_to_relative_path(module)

    candidates = []
    for root in source_roots:
        candidate = project_root / root / rel_path
        candidates.append(candidate)
        if candidate.exists():
            return candidate

    # 兼容旧写法：require("src.xxx") / require("ma3lib.xxx") / require("vendor.xxx")
    root_name = module.split(".", 1)[0]
    if root_name in source_roots:
        legacy_path = project_root / module_to_relative_path(module)
        if legacy_path.exists():
            return legacy_path

    searched = "\n".join(f"  - {p}" for p in candidates)
    raise BuildError(
        f"Module {module!r} not found in sourceRoots {list(source_roots)!r}.\n"
        f"Searched:\n{searched}"
    )

def strip_lua_comments_for_require_scan(code: str) -> str:
    # Conservative scanner aid. It is not a full Lua parser, but prevents most
    # comment-only require(...) references from being bundled.
    code = re.sub(r"--\[\[.*?\]\]", "", code, flags=re.S)
    code = re.sub(r"--\[=.*?=\]", "", code, flags=re.S)
    cleaned_lines = []
    for line in code.splitlines():
        idx = line.find("--")
        if idx >= 0:
            line = line[:idx]
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def parse_requires(code: str, module_name: str) -> List[str]:
    cleaned = strip_lua_comments_for_require_scan(code)
    requires = [m.group(2) for m in REQUIRE_LITERAL_RE.finditer(cleaned)]

    for lineno, line in enumerate(cleaned.splitlines(), start=1):
        if REQUIRE_ANY_RE.search(line) and not REQUIRE_LITERAL_RE.search(line):
            raise BuildError(
                f"Unsupported dynamic require in {module_name} line {lineno}: {line.strip()}\n"
                "Use static require(\"module.name\") or add a static wrapper module."
            )

    seen: Set[str] = set()
    ordered: List[str] = []
    for dep in requires:
        if dep not in seen:
            ordered.append(dep)
            seen.add(dep)
    return ordered


def read_module(project_root: Path, source_roots: Sequence[str], module: str) -> ModuleInfo:
    path = resolve_module_to_file(project_root, source_roots, module)
    code = path.read_text(encoding="utf-8")
    relpath = path.relative_to(project_root).as_posix()
    return ModuleInfo(name=module, path=path, relpath=relpath, code=code)


def collect_modules(project_root: Path, config: dict) -> List[ModuleInfo]:
    entry_module = config.get("entryModule")
    if not entry_module:
        raise BuildError("config.entryModule is required")

    source_roots = config.get("sourceRoots") or ["src", "ma3lib", "vendor"]
    manual_deps = config.get("manualDependencies") or []
    external_deps = set(config.get("externalDependencies") or [])

    visited: Set[str] = set()
    ordered: List[ModuleInfo] = []

    def visit(module: str, stack: List[str]) -> None:
        if module in external_deps:
            return
        if module in visited:
            return
        if module in stack:
            raise BuildError("Circular dependency: " + " -> ".join(stack + [module]))

        info = read_module(project_root, source_roots, module)
        stack.append(module)
        for dep in parse_requires(info.code, module):
            visit(dep, stack)
        stack.pop()

        visited.add(module)
        ordered.append(info)

    visit(entry_module, [])
    for dep in manual_deps:
        visit(dep, [])

    return ordered


def header(config: dict, modules: Sequence[ModuleInfo], entry_mode: str) -> str:
    now = _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    source_roots = ", ".join(config.get("sourceRoots") or [])
    return "\n".join([
        "-- ============================================================",
        "-- Generated by MA3 Python Builder",
        f"-- Plugin: {config.get('name', '')}",
        f"-- Display Name: {config.get('displayName', '')}",
        f"-- Version: {config.get('version', '')}",
        f"-- Generated: {now}",
        "-- Do not edit this file directly.",
        f"-- Source roots: {source_roots}",
        f"-- Entry mode: {entry_mode}",
        f"-- Modules: {', '.join(m.name for m in modules)}",
        "-- ============================================================",
        "",
    ])


def bundle_lua(config: dict, modules: Sequence[ModuleInfo]) -> str:
    entry_module = config["entryModule"]
    bundle_cfg = config.get("bundle") or {}
    entry_mode = bundle_cfg.get("entryMode", "inline")
    if entry_mode not in {"inline", "preload"}:
        raise BuildError('bundle.entryMode must be either "inline" or "preload"')

    parts: List[str] = [header(config, modules, entry_mode)]

    # Do not depend on MA3 exposing Lua's package/require tables.
    # We provide a tiny lexical module loader and shadow `require`.
    parts.extend([
        'local __ma3_modules = {}',
        'local __ma3_cache = {}',
        'local function __ma3_require(name)',
        '    if __ma3_cache[name] ~= nil then',
        '        return __ma3_cache[name]',
        '    end',
        '    local loader = __ma3_modules[name]',
        '    if not loader then',
        '        error(\"module not found: \" .. tostring(name), 2)',
        '    end',
        '    local result = loader()',
        '    if result == nil then',
        '        result = true',
        '    end',
        '    __ma3_cache[name] = result',
        '    return result',
        'end',
        'local require = __ma3_require',
        '',
    ])

    for info in modules:
        if entry_mode == "inline" and info.name == entry_module:
            continue
        parts.append(f'__ma3_modules[{json.dumps(info.name)}] = function(...)')
        parts.append(f"-- source: {info.relpath}")
        parts.append(info.code.rstrip())
        parts.append("end")
        parts.append("")

    if entry_mode == "inline":
        entry_info = next((m for m in modules if m.name == entry_module), None)
        if not entry_info:
            raise BuildError(f"Entry module not found in module list: {entry_module}")
        parts.append("-- ============================================================")
        parts.append(f"-- Entry module inlined to preserve MA3 ComponentLua varargs: {entry_module}")
        parts.append(f"-- source: {entry_info.relpath}")
        parts.append("-- ============================================================")
        parts.append(entry_info.code.rstrip())
        parts.append("")
    else:
        parts.append(f"return require({json.dumps(entry_module)})")
        parts.append("")

    return "\n".join(parts)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    path.write_text(normalized, encoding="utf-8")


def local_lua_output_path(project_root: Path, config: dict) -> Path:
    local = config.get("localOutput")
    if local:
        return (project_root / local).resolve()
    return (project_root / "dist" / lua_filename(config)).resolve()


def local_xml_output_path(project_root: Path, config: dict) -> Path:
    xml_out = config.get("xmlOutput")
    if xml_out:
        return (project_root / xml_out).resolve()
    return (project_root / "dist" / xml_filename(config)).resolve()


def xml_escape_attr(value: object) -> str:
    return html.escape(str(value), quote=True)


def xml_attr_text(attrs: dict) -> str:
    return " ".join(
        f'{key}="{xml_escape_attr(value)}"'
        for key, value in attrs.items()
        if value is not None and str(value) != ""
    )


def base64_raw_blocks(raw: bytes) -> List[str]:
    # grandMA3 exports FileContent as 1024 raw-byte chunks.
    # Do NOT split the already encoded Base64 string: MA3 may treat
    # a short non-final block as end-of-file during import.
    chunks = [raw[i : i + XML_RAW_BLOCK_SIZE] for i in range(0, len(raw), XML_RAW_BLOCK_SIZE)] or [b""]
    return [base64.b64encode(chunk).decode("ascii") for chunk in chunks]


def base64_blocks(text: str) -> List[str]:
    return base64_raw_blocks(text.encode("utf-8"))


def filecontent_from_blocks(blocks: Sequence[str], indent: str = "        ") -> str:
    lines = [f'{indent}<FileContent Size="{len(blocks)}">']
    for block in blocks:
        lines.append(f'{indent}    <Block Base64="{block}" />')
    lines.append(f'{indent}</FileContent>')
    return "\n".join(lines)


def generate_component_filecontent(lua_code: str, indent: str = "        ") -> str:
    return filecontent_from_blocks(base64_blocks(lua_code), indent=indent)


def bool_from_config(value: object, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return default


def clamp_color(value: object, default: int) -> int:
    try:
        return max(0, min(255, int(value)))
    except (TypeError, ValueError):
        return default


def stable_guid(seed: str) -> str:
    value = uuid.uuid5(uuid.NAMESPACE_URL, "ma3-lua-plugin-scaffold:" + seed).hex.upper()
    return " ".join(value[i : i + 2] for i in range(0, len(value), 2))


def normalize_asset_image(project_root: Path, item: object, index: int, config: dict) -> ImageAsset:
    if isinstance(item, str):
        item = {"file": item}
    if not isinstance(item, dict):
        raise BuildError(f"assets.images[{index}] must be an object or string path")

    # 文件路径
    raw_file = item.get("file") or item.get("path")
    file_path = (project_root / str(raw_file)).resolve()
    if not file_path.exists() or not file_path.is_file():
        raise BuildError(f"Image asset not found: {file_path}")

    # 获取模板占位符实际值
    plugin_name = str(config.get("name") or "Plugin")
    display_name = str(config.get("displayName") or plugin_name)

    base_name = file_path.stem
    image_name = str(item.get("name") or f"{plugin_name}_{base_name}")
    appearance_name = str(item.get("appearanceName") or item.get("appearance") or image_name)

    # 替换占位符
    image_name = image_name.replace("exampleplugin", plugin_name).replace("exampleplugin", display_name)
    appearance_name = appearance_name.replace("exampleplugin", plugin_name).replace("exampleplugin", display_name)

    image_mode = str(item.get("imageMode") or "Crop")
    use_as_plugin_appearance = bool_from_config(
        item.get("useAsPluginAppearance", item.get("asPluginAppearance", item.get("pluginIcon"))),
        default=(index == 0),
    )
    back = item.get("backColor") if isinstance(item.get("backColor"), dict) else {}

    return ImageAsset(
        name=image_name,
        file=file_path,
        relfile=file_path.relative_to(project_root).as_posix(),
        filename=str(item.get("fileName") or file_path.name),
        appearance_name=appearance_name,
        image_mode=image_mode,
        use_as_plugin_appearance=use_as_plugin_appearance,
        back_r=clamp_color(item.get("backR", back.get("r", 0)), 0),
        back_g=clamp_color(item.get("backG", back.get("g", 0)), 0),
        back_b=clamp_color(item.get("backB", back.get("b", 0)), 0),
        back_alpha=clamp_color(item.get("backAlpha", back.get("alpha", 255)), 255),
    )
    if isinstance(item, str):
        item = {"file": item}
    if not isinstance(item, dict):
        raise BuildError(f"assets.images[{index}] must be an object or string path")

    raw_file = item.get("file") or item.get("path")
    if not raw_file:
        raise BuildError(f"assets.images[{index}] is missing file")
    file_path = (project_root / str(raw_file)).resolve()
    if not file_path.exists():
        raise BuildError(f"Image asset not found: {file_path}")
    if not file_path.is_file():
        raise BuildError(f"Image asset is not a file: {file_path}")

    plugin_name = str(config.get("name") or "Plugin")
    base_name = file_path.stem
    image_name = str(item.get("name") or f"{plugin_name}_{base_name}")
    appearance_name = str(item.get("appearanceName") or item.get("appearance") or image_name)
    image_mode = str(item.get("imageMode") or "Crop")
    use_as_plugin_appearance = bool_from_config(
        item.get("useAsPluginAppearance", item.get("asPluginAppearance", item.get("pluginIcon"))),
        default=(index == 0),
    )
    back = item.get("backColor") if isinstance(item.get("backColor"), dict) else {}
    return ImageAsset(
        name=image_name,
        file=file_path,
        relfile=file_path.relative_to(project_root).as_posix(),
        filename=str(item.get("fileName") or file_path.name),
        appearance_name=appearance_name,
        image_mode=image_mode,
        use_as_plugin_appearance=use_as_plugin_appearance,
        back_r=clamp_color(item.get("backR", back.get("r", 0)), 0),
        back_g=clamp_color(item.get("backG", back.get("g", 0)), 0),
        back_b=clamp_color(item.get("backB", back.get("b", 0)), 0),
        back_alpha=clamp_color(item.get("backAlpha", back.get("alpha", 255)), 255),
    )


def collect_image_assets(project_root: Path, config: dict) -> List[ImageAsset]:
    assets = config.get("assets") or {}
    images = assets.get("images") or []
    if not isinstance(images, list):
        raise BuildError("assets.images must be a list")
    return [normalize_asset_image(project_root, item, i, config) for i, item in enumerate(images)]


def generate_user_image_xml(asset: ImageAsset, indent: str = "                            ") -> str:
    blocks = base64_raw_blocks(asset.file.read_bytes())
    attrs = {
        "Name": asset.name,
        "Guid": stable_guid("image:" + asset.name + ":" + asset.relfile),
        "FileName": asset.filename,
        "AddAlpha": "No",
    }
    lines = [f'{indent}<UserImage {xml_attr_text(attrs)}>']
    lines.append(filecontent_from_blocks(blocks, indent=indent + "    "))
    lines.append(f'{indent}</UserImage>')
    return "\n".join(lines)


def generate_appearance_dependency_xml(asset: ImageAsset, indent: str = "        ") -> str:
    appearance_addr = f"ShowData.Appearances.&apos;{xml_escape_attr(asset.appearance_name)}&apos;"
    image_addr = f"ShowData.MediaPools.Images.&apos;{xml_escape_attr(asset.name)}&apos;"
    appearance_attrs = {
        "Name": asset.appearance_name,
        "Guid": stable_guid("appearance:" + asset.appearance_name),
        "Color": "1.0000000000,1.0000000000,1.0000000000,1.0000000000",
        "ImageMode": asset.image_mode,
        "BackR": asset.back_r,
        "BackG": asset.back_g,
        "BackB": asset.back_b,
        "BackAlpha": asset.back_alpha,
        "MediaFileName": "CUSTOM/" + asset.filename,
    }
    lines = [
        f'{indent}<Dependency Address="{appearance_addr}">',
        f'{indent}    <Appearance {xml_attr_text(appearance_attrs)}>',
        f'{indent}        <DependencyExport Size="1">',
        f'{indent}            <Dependency Address="{image_addr}">',
        generate_user_image_xml(asset, indent=indent + "                "),
        f'{indent}            </Dependency>',
        f'{indent}        </DependencyExport>',
        f'{indent}    </Appearance>',
        f'{indent}</Dependency>',
    ]
    return "\n".join(lines)


def generate_assets_dependency_export(image_assets: Sequence[ImageAsset], indent: str = "        ") -> str:
    if not image_assets:
        return ""
    lines = [f'{indent}<DependencyExport Size="{len(image_assets)}">']
    for asset in image_assets:
        lines.append(generate_appearance_dependency_xml(asset, indent=indent + "    "))
    lines.append(f'{indent}</DependencyExport>')
    return "\n".join(lines)


def plugin_appearance_name(image_assets: Sequence[ImageAsset]) -> str | None:
    for asset in image_assets:
        if asset.use_as_plugin_appearance:
            return asset.appearance_name
    return None


def generate_ma3_xml(config: dict, lua_code: str, xml_mode: str | None = None, image_assets: Sequence[ImageAsset] | None = None) -> str:
    ma3 = config.get("ma3", {})
    mode = (xml_mode or ma3.get("xmlMode") or ma3.get("outputMode") or "installed").lower()
    if mode not in {"installed", "embedded"}:
        raise BuildError('ma3.xmlMode must be either "installed" or "embedded"')

    data_version = ma3.get("dataVersion") or ma3.get("version") or "2.3.2.0"
    if data_version == "auto":
        # DataVersion is XML schema metadata, not the target gma3 directory selector.
        # Keep a stable modern default; override with ma3.dataVersion if needed.
        data_version = "2.3.2.0"

    plugin_name = ma3.get("pluginName") or config.get("displayName") or config.get("name") or "Plugin"
    component_name = ma3.get("componentName") or config.get("name") or plugin_name

    image_assets = list(image_assets or [])
    user_plugin_attrs = {
        "Name": plugin_name,
        "Version": config.get("version", "0.0.0.0"),
        "Author": config.get("author", ""),
        "Appearance": plugin_appearance_name(image_assets),
    }

    component_attrs = {"Name": component_name}
    if mode == "installed":
        component_attrs.update({
            "FileName": ma3.get("componentFileName") or lua_filename(config),
            "FilePath": ma3.get("componentFilePath") or ma3.get("pluginSubdir") or "",
            "Installed": "Yes" if ma3.get("installed", True) else "No",
        })

    lines: List[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!-- Generated by MA3 Python Builder. Do not edit manually. -->',
        f'<GMA3 DataVersion="{xml_escape_attr(data_version)}">',
        f'    <UserPlugin {xml_attr_text(user_plugin_attrs)}>',
    ]

    assets_xml = generate_assets_dependency_export(image_assets, indent="        ")
    if assets_xml:
        lines.append(assets_xml)

    lines.append(f'        <ComponentLua {xml_attr_text(component_attrs)}>')

    if mode == "embedded":
        lines.append(generate_component_filecontent(lua_code, indent="            "))
    else:
        # In installed mode the external .lua file is authoritative for fast ReloadAllPlugins.
        # The XML is still mandatory to define the UserPlugin/ComponentLua object.
        lines.append('            <!-- Installed="Yes": Lua source is loaded from FilePath/FileName. -->')

    lines.extend([
        '        </ComponentLua>',
        '    </UserPlugin>',
        '</GMA3>',
        '',
    ])
    return "\n".join(lines)



def decode_embedded_xml_file(xml_path: Path) -> str:
    text = xml_path.read_text(encoding="utf-8")
    blocks = re.findall(r'<Block\s+Base64="([^"]*)"\s*/?>', text)
    if not blocks:
        raise BuildError(f"No embedded FileContent Block found in {xml_path}")
    raw = b"".join(base64.b64decode(block) for block in blocks)
    return raw.decode("utf-8")


def validate_embedded_xml(xml_code: str, lua_code: str) -> List[str]:
    messages: List[str] = []
    blocks = re.findall(r'<Block\s+Base64="([^"]*)"\s*/?>', xml_code)
    declared = re.search(r'<FileContent\s+Size="(\d+)"', xml_code)
    if not blocks:
        raise BuildError("embedded XML has no FileContent Block")
    if declared and int(declared.group(1)) != len(blocks):
        raise BuildError(f"FileContent Size={declared.group(1)} but Block count={len(blocks)}")
    raw_chunks = [base64.b64decode(block) for block in blocks]
    for idx, chunk in enumerate(raw_chunks[:-1], start=1):
        if len(chunk) != XML_RAW_BLOCK_SIZE:
            raise BuildError(f"embedded XML block {idx} raw size is {len(chunk)}, expected {XML_RAW_BLOCK_SIZE}")
    decoded = b"".join(raw_chunks).decode("utf-8")
    if decoded != lua_code:
        raise BuildError("embedded XML decoded Lua does not match generated bundle")
    messages.append(f"embedded blocks: {len(blocks)}")
    messages.append(f"embedded lua bytes: {len(lua_code.encode('utf-8'))}")
    return messages


def validate_installed_xml(config: dict, xml_code: str) -> List[str]:
    ma3 = config.get("ma3", {})
    expected_file = str(ma3.get("componentFileName") or lua_filename(config))
    expected_path = str(ma3.get("componentFilePath") or ma3.get("pluginSubdir") or "")
    messages: List[str] = []
    component_match = re.search(r'<ComponentLua\b[^>]*>(.*?)</ComponentLua>', xml_code, flags=re.S)
    if component_match and "<FileContent" in component_match.group(1):
        raise BuildError("installed ComponentLua must not contain FileContent")
    for needle in [f'FileName="{xml_escape_attr(expected_file)}"', f'FilePath="{xml_escape_attr(expected_path)}"', 'Installed="Yes"']:
        if needle not in xml_code:
            raise BuildError(f"installed XML missing {needle}")
    messages.append(f"installed FilePath: {expected_path}")
    messages.append(f"installed FileName: {expected_file}")
    return messages


def validate_build(config: dict, lua_code: str, xml_code: str, mode: str) -> None:
    # Basic sanity: generated bundle should expose at least one MA3 function reference.
    if "return Main" not in lua_code and "return App.Main" not in lua_code and "return require" not in lua_code:
        # This is deliberately a warning, not hard error, because custom entry modules can return differently.
        print("[WARN] bundle does not contain a simple 'return Main' pattern; verify entry module returns a function")

    if mode == "embedded":
        messages = validate_embedded_xml(xml_code, lua_code)
    else:
        messages = validate_installed_xml(config, xml_code)

    print(f"[OK] validate mode: {mode}")
    for msg in messages:
        print(f"[OK] validate {msg}")

def effective_xml_mode(config: dict, args: argparse.Namespace) -> str:
    ma3 = config.get("ma3", {})
    mode = (args.xml_mode or ma3.get("xmlMode") or ma3.get("outputMode") or "installed").lower()
    if mode not in {"installed", "embedded"}:
        raise BuildError('XML mode must be either "installed" or "embedded"')
    return mode


def build(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser().resolve()
    config = read_json(config_path)
    project_root = project_root_from_config(config_path)

    modules = collect_modules(project_root, config)
    image_assets = collect_image_assets(project_root, config)
    lua_code = bundle_lua(config, modules)
    mode = effective_xml_mode(config, args)
    xml_code = generate_ma3_xml(config, lua_code, xml_mode=mode, image_assets=image_assets)

    local_lua_path = local_lua_output_path(project_root, config)
    local_xml_path = local_xml_output_path(project_root, config)
    write_text(local_lua_path, lua_code)
    write_text(local_xml_path, xml_code)
    print(f"[OK] local lua: {local_lua_path}")
    print(f"[OK] local xml: {local_xml_path}")
    print(f"[OK] xml mode: {mode}")
    if image_assets:
        print(f"[OK] assets images: {len(image_assets)}")
        for asset in image_assets:
            blocks = len(base64_raw_blocks(asset.file.read_bytes()))
            marker = " plugin-appearance" if asset.use_as_plugin_appearance else ""
            print(f"[OK] image: {asset.name} -> {asset.relfile}, appearance={asset.appearance_name}, blocks={blocks}{marker}")
    validate_build(config, lua_code, xml_code, mode)

    if args.local:
        return 0

    if args.out:
        xml_paths = [Path(args.out).expanduser().resolve()]
        base_dirs = [xml_paths[0].parent]
    else:
        base_dirs = resolve_ma3_base_dirs(config, args)
        xml_paths = [base / xml_filename(config) for base in base_dirs]

    for base_dir, xml_path in zip(base_dirs, xml_paths):
        write_text(xml_path, xml_code)
        print(f"[OK] ma3 xml: {xml_path}")

        if mode == "installed":
            lua_path = base_dir / lua_filename(config)
            write_text(lua_path, lua_code)
            print(f"[OK] ma3 lua: {lua_path}")

    return 0


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build MA3 Lua plugin into XML + optional external Lua.")
    parser.add_argument("--config", default="config/plugin.json", help="Path to plugin.json")
    parser.add_argument("--ma3-root", help="Override MA3 root directory, e.g. C:\\ProgramData\\MALightingTechnology")
    parser.add_argument("--ma3-version", help="Accepted for compatibility; XML/Lua output uses gma3_library/datapools/plugins")
    parser.add_argument("--out", help="Write MA3 output to this exact XML file path")
    parser.add_argument("--local", action="store_true", help="Only write local dist output; do not write to MA3 directory")
    parser.add_argument("--all-versions", action="store_true", help="Accepted for compatibility; XML/Lua output uses shared gma3_library")
    parser.add_argument("--xml-mode", choices=["installed", "embedded"], help="Override ma3.xmlMode")
    parser.add_argument("--decode", help="Decode an embedded XML FileContent to Lua and exit")
    parser.add_argument("--decode-out", help="Output path for --decode. Defaults to decoded_from_xml.lua next to XML")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    try:
        if args.decode:
            xml_path = Path(args.decode).expanduser().resolve()
            lua = decode_embedded_xml_file(xml_path)
            out = Path(args.decode_out).expanduser().resolve() if args.decode_out else xml_path.with_name("decoded_from_xml.lua")
            write_text(out, lua)
            print(f"[OK] decoded lua: {out}")
            return 0
        return build(args)
    except BuildError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
