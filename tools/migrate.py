#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import shutil
from pathlib import Path

# ================= 配置 =================
TEMPLATE_DIR = Path(__file__).parent.parent / "templates" / "basic"
BUSINESS_DIRS = ["src"]  # 不覆盖业务代码
REPORT_FILE = "docs/MIGRATION.md"

# ================= 工具函数 =================
def copy_files(src_dir: Path, dst_dir: Path, report: list, overwrite=False, skip_dirs=None):
    """增量或覆盖复制模板文件"""
    skip_dirs = skip_dirs or []
    for root, dirs, files in os.walk(src_dir):
        rel_root = Path(root).relative_to(src_dir)
        target_root = dst_dir / rel_root
        target_root.mkdir(parents=True, exist_ok=True)

        for f in files:
            src_file = Path(root) / f
            dst_file = target_root / f

            # 跳过业务代码目录
            if rel_root.parts and rel_root.parts[0] in skip_dirs and dst_file.exists():
                report.append(f"[SKIP] {dst_file} 业务文件，不覆盖")
                continue

            # 决定是否覆盖
            if dst_file.exists():
                if overwrite:
                    backup = dst_file.with_suffix(dst_file.suffix + ".bak")
                    shutil.copy2(dst_file, backup)
                    report.append(f"[INFO] 备份旧文件 {dst_file} → {backup}")
                else:
                    report.append(f"[INFO] {dst_file} 已存在，跳过")
                    continue

            shutil.copy2(src_file, dst_file)
            report.append(f"[OK] {'覆盖' if overwrite else '新增'}文件 {dst_file}")

def merge_dict_recursive(template: dict, project: dict, report: list, path=""):
    """递归合并模板 JSON 字段"""
    for key, value in template.items():
        full_path = f"{path}.{key}" if path else key
        if key not in project:
            project[key] = value
            report.append(f"[OK] plugin.json 新增字段 {full_path}，使用模板默认值")
        else:
            if isinstance(value, dict) and isinstance(project[key], dict):
                merge_dict_recursive(value, project[key], report, full_path)
            elif isinstance(value, list) and isinstance(project[key], list):
                if not project[key]:
                    project[key] = value
                    report.append(f"[OK] plugin.json 新增数组 {full_path}，使用模板默认值")

def merge_plugin_json(project_path: Path, report: list):
    """合并 plugin.json 并更新 scaffoldVersion"""
    plugin_json_path = project_path / "config/plugin.json"
    template_json_path = TEMPLATE_DIR / "config/plugin.json"

    if not plugin_json_path.exists() or not template_json_path.exists():
        report.append("[WARN] plugin.json 或模板 plugin.json 不存在")
        return

    with open(plugin_json_path, "r", encoding="utf-8") as f:
        project_data = json.load(f)
    with open(template_json_path, "r", encoding="utf-8") as f:
        template_data = json.load(f)

    merge_dict_recursive(template_data, project_data, report)

    old_version = project_data.get("scaffoldVersion", "0.0.0")
    project_data["scaffoldVersion"] = template_data.get("scaffoldVersion", "0.4.0")
    report.append(f"[INFO] scaffoldVersion 自动更新: {old_version} → {project_data['scaffoldVersion']}")

    with open(plugin_json_path, "w", encoding="utf-8") as f:
        json.dump(project_data, f, indent=2, ensure_ascii=False)

def create_assets_dir(project_path: Path, report: list):
    assets_dir = project_path / "assets" / "images"
    if not assets_dir.exists():
        assets_dir.mkdir(parents=True)
        report.append(f"[OK] 创建 assets/images 目录")
    else:
        report.append(f"[INFO] assets/images 已存在")

def generate_report(project_path: Path, report: list):
    docs_dir = project_path / "docs"
    docs_dir.mkdir(exist_ok=True)
    report_path = docs_dir / "MIGRATION.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# 迁移报告\n\n")
        f.write("请根据下面提示修改必填字段后再执行 build.py\n\n")
        for line in report:
            f.write(f"{line}\n")
    print(f"[OK] 迁移报告生成: {report_path}")

# ================= 主程序 =================
def main():
    if len(sys.argv) < 2:
        print("用法: python migrate.py <项目路径> [--skip-tools]")
        sys.exit(1)

    project_path = Path(sys.argv[1]).resolve()
    if not project_path.exists():
        print(f"[ERROR] 项目路径不存在: {project_path}")
        sys.exit(1)

    # 默认覆盖 tools，--skip-tools 可保留老工具
    overwrite_tools = True
    if "--skip-tools" in sys.argv:
        overwrite_tools = False

    report = []

    print(f"=== 迁移开始: {project_path} ===")

    # 1. tools 覆盖或跳过
    copy_files(TEMPLATE_DIR / "tools", project_path / "tools", report, overwrite=overwrite_tools)

    # 2. ma3lib、vendor、assets、demo 等目录增量复制
    for folder in ["ma3lib", "vendor", "assets", "demo"]:
        src_folder = TEMPLATE_DIR / folder
        if src_folder.exists():
            copy_files(src_folder, project_path / folder, report, overwrite=False, skip_dirs=BUSINESS_DIRS)

    # 3. plugin.json 增量合并并更新 scaffoldVersion
    merge_plugin_json(project_path, report)

    # 4. 中文迁移报告
    generate_report(project_path, report)

    print("=== 迁移完成 ===")
    print("请修改必填字段后，再执行 build.py 生成 Lua + XML")

if __name__ == "__main__":
    main()