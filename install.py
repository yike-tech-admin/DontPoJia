#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
install.py — 安装 refuse-cracking 安全护栏

把本仓库中的两份资产安装到目标机器：

  1. SKILL.md   →  <base>/.agents/skills/refuse-cracking/SKILL.md
  2. AGENTS.md  →  <base>/AGENTS.md   （已存在则注入带标记的区块）

幂等设计：
  * SKILL.md  内容完全一致      → 跳过（unchanged）
  * SKILL.md  内容不一致        → 备份旧文件后更新（updated）
  * AGENTS.md 不存在            → 创建
  * AGENTS.md 已存在但无标记    → 注入区块（默认置顶，可用 --position bottom 改为追加到末尾）
  * AGENTS.md 已存在且有标记    → 原位替换区块内容（不重复追加）

安全设计：
  * 任何写入前都会对目标文件做 .bak 备份
  * --dry-run 只打印计划，不落盘
  * 默认只写目标文件，不删除、不覆盖其他内容

用法：
  python install.py                       # 安装到全局（~/.agents）+ 当前目录项目
  python install.py --dry-run             # 只看计划
  python install.py --scope project       # 只装项目级（当前目录）
  python install.py --scope global        # 只装全局
  python install.py --project /path/to/p  # 指定项目目录
  python install.py --position bottom     # AGENTS.md 区块追加到末尾而非置顶
  python install.py --no-skill            # 跳过 SKILL.md
  python install.py --no-agents           # 跳过 AGENTS.md
  python install.py --uninstall           # 移除本工具注入的区块与 skill（只动自己标记过的内容）
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
SKILL_SRC = REPO_ROOT / "SKILL.md"
AGENTS_SRC = REPO_ROOT / "AGENTS.md"

SKILL_REL = Path(".agents") / "skills" / "refuse-cracking" / "SKILL.md"
AGENTS_REL = Path("AGENTS.md")

BLOCK_BEGIN = "<!-- BEGIN refuse-cracking (managed by install.py) -->"
BLOCK_END = "<!-- END refuse-cracking (managed by install.py) -->"
BLOCK_TITLE = "破解护栏规则（由 refuse-cracking 安装器注入）"


# --------------------------------------------------------------------------
# 基础工具
# --------------------------------------------------------------------------
def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def backup(path: Path) -> Path | None:
    """备份目标文件，返回备份路径；文件不存在时返回 None。"""
    if not path.exists():
        return None
    bak = path.with_name(path.name + ".bak")
    shutil.copy2(path, bak)
    return bak


def demote_headings(text: str) -> str:
    """
    把 Markdown 标题整体降一级，使注入到别的 AGENTS.md 后层级不冲突，
    并把顶层 H1 换成区块标题。
    """
    lines = text.splitlines()
    out: list[str] = []
    first_h1_replaced = False
    for line in lines:
        if line.startswith("#") and not line.startswith("####"):
            hashes, rest = line.split(" ", 1) if " " in line else (line, "")
            if len(hashes) == 1 and not first_h1_replaced:
                first_h1_replaced = True
                out.append(f"## {BLOCK_TITLE}")
                continue
            out.append("#" + line)
        else:
            out.append(line)
    return "\n".join(out)


def build_block(source: str) -> str:
    """把 AGENTS.md 源文件包装成可注入的标记区块（标题降一级，避免与宿主文件层级冲突）。"""
    body = demote_headings(source.strip())
    return f"{BLOCK_BEGIN}\n\n{body}\n\n{BLOCK_END}"


def strip_block(text: str) -> str:
    """从文本中移除受管区块（含其后的空行），返回剩余内容。"""
    start = text.find(BLOCK_BEGIN)
    if start == -1:
        return text
    end = text.find(BLOCK_END, start)
    if end == -1:
        # 区块不完整（手工改坏了）——只砍到 BEGIN 之前，避免误删正文
        return text[:start].rstrip() + "\n"
    tail = text[end + len(BLOCK_END):]
    return text[:start].rstrip() + "\n\n" + tail.lstrip("\n")


# --------------------------------------------------------------------------
# 安装动作
# --------------------------------------------------------------------------
def install_skill(base: Path, dry_run: bool, quiet: bool = False) -> str:
    """安装 SKILL.md 到 <base>/.agents/skills/refuse-cracking/"""
    if not SKILL_SRC.exists():
        return "skipped(source-missing)"
    target = base / SKILL_REL
    new_content = read_text(SKILL_SRC)

    if target.exists() and read_text(target) == new_content:
        return "unchanged"

    if dry_run:
        return "would-update" if target.exists() else "would-create"

    if target.exists():
        backup(target)
        write_text(target, new_content)
        return "updated"

    write_text(target, new_content)
    return "created"


def install_agents(base: Path, dry_run: bool, position: str = "top") -> str:
    """把 AGENTS.md 注入到 <base>/AGENTS.md（已存在则用标记区块注入/替换）。"""
    if not AGENTS_SRC.exists():
        return "skipped(source-missing)"
    target = base / AGENTS_REL
    block = build_block(read_text(AGENTS_SRC))

    if not target.exists():
        if dry_run:
            return "would-create"
        write_text(target, f"{block}\n")
        return "created"

    current = read_text(target)

    if BLOCK_BEGIN in current and BLOCK_END in current:
        # 已有受管区块 → 原位替换
        if block in current:
            return "unchanged"
        start = current.find(BLOCK_BEGIN)
        end = current.find(BLOCK_END, start) + len(BLOCK_END)
        new_content = current[:start] + block + current[end:]
        if dry_run:
            return "would-update"
        backup(target)
        write_text(target, new_content)
        return "updated"

    # 没有受管区块 → 注入
    if dry_run:
        return "would-inject"

    backup(target)
    if position == "bottom":
        new_content = current.rstrip() + "\n\n" + block + "\n"
    else:
        new_content = block + "\n\n" + current.lstrip("\n")
    write_text(target, new_content)
    return "injected"


def uninstall_skill(base: Path, dry_run: bool) -> str:
    target = base / SKILL_REL
    if not target.exists():
        return "absent"
    if dry_run:
        return "would-remove"
    target.unlink()
    # 清理空目录（仅限我们创建的 skill 目录）
    try:
        shutil.rmtree(target.parent)
    except OSError:
        pass
    return "removed"


def uninstall_agents(base: Path, dry_run: bool) -> str:
    target = base / AGENTS_REL
    if not target.exists():
        return "absent"
    current = read_text(target)
    if BLOCK_BEGIN not in current:
        return "not-managed"
    if dry_run:
        return "would-remove-block"
    backup(target)
    write_text(target, strip_block(current))
    return "block-removed"


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="安装 refuse-cracking 安全护栏 (SKILL.md + AGENTS.md)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--dry-run", action="store_true", help="只打印计划，不写入任何文件")
    p.add_argument(
        "--scope",
        choices=["both", "global", "project"],
        default="both",
        help="安装范围：global=~/.agents，project=当前目录（或 --project 指定），默认 both",
    )
    p.add_argument("--project", type=Path, default=Path.cwd(), help="项目级安装的目标目录，默认当前目录")
    p.add_argument(
        "--position",
        choices=["top", "bottom"],
        default="top",
        help="注入到已有 AGENTS.md 时，区块置顶(top，默认)或追加到底部(bottom)",
    )
    p.add_argument("--no-skill", action="store_true", help="不安装 SKILL.md")
    p.add_argument("--no-agents", action="store_true", help="不安装 AGENTS.md")
    p.add_argument("--uninstall", action="store_true", help="移除本工具安装的内容")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    global_base = Path.home() / ".agents"
    project_base = args.project.resolve()

    targets: list[tuple[str, Path]] = []
    if args.scope in ("both", "global"):
        targets.append(("global", global_base))
    if args.scope in ("both", "project"):
        targets.append(("project", project_base))

    if not targets:
        print("没有可用的安装目标。", file=sys.stderr)
        return 2

    print(f"模式: {'DRY-RUN（不写入）' if args.dry_run else '实际写入'}")
    print(f"源文件: {REPO_ROOT}")
    print("-" * 68)

    changed = False
    for label, base in targets:
        print(f"[{label}] {base}")
        if args.uninstall:
            if not args.no_skill:
                st = uninstall_skill(base, args.dry_run)
                print(f"    skill   -> {st}")
                changed = changed or st.startswith("would-") or st in ("removed",)
            if not args.no_agents:
                st = uninstall_agents(base, args.dry_run)
                print(f"    agents  -> {st}")
                changed = changed or st.startswith("would-") or st == "block-removed"
        else:
            if not args.no_skill:
                st = install_skill(base, args.dry_run)
                print(f"    skill   -> {st}")
                changed = changed or st in ("created", "updated")
            if not args.no_agents:
                st = install_agents(base, args.dry_run, args.position)
                print(f"    agents  -> {st}")
                changed = changed or st in ("created", "updated", "injected")
        print()

    print("-" * 68)
    if args.dry_run:
        print("DRY-RUN 结束：未写入任何文件。去掉 --dry-run 即可实际安装。")
    elif changed:
        print("安装完成。被修改的文件均已生成 .bak 备份。")
    else:
        print("无需变更（目标已是最新）。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
