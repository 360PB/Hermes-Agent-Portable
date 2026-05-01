#!/usr/bin/env python3
"""
Hermes-Agent-Portable 一键打包脚本

用法:
    python scripts/pack.py                    # 自动检测版本号打包
    python scripts/pack.py --version 0.11.0   # 指定版本号
    python scripts/pack.py --format zip       # 使用 zip 格式（默认 7z）
    python scripts/pack.py --check-only       # 只运行检查，不打包

排除项:
    - .git/           # Git 历史，体积大且用户不需要
    - skills/         # AI skill 文档，维护者专用
    - scripts/        # 打包/检查脚本，用户不需要
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# 修复 Windows GBK 编码问题
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


def _root() -> Path:
    return Path(__file__).resolve().parent.parent


def run_pre_check() -> bool:
    """运行打包前检查，返回是否通过。"""
    check_script = _root() / "scripts" / "pre-pack-check.py"
    if not check_script.exists():
        print(f"{YELLOW}[WARN]{RESET} pre-pack-check.py 不存在，跳过检查")
        return True

    print(f"{CYAN}=== 运行打包前检查 ==={RESET}\n")
    result = subprocess.run(
        [sys.executable, str(check_script)],
        cwd=_root(),
        timeout=300,
    )
    print()
    return result.returncode == 0


def run_p0_test() -> bool:
    """运行 P0 冒烟测试，返回是否通过。"""
    p0_script = _root() / "scripts" / "p0-test.py"
    if not p0_script.exists():
        print(f"{YELLOW}[WARN]{RESET} p0-test.py 不存在，跳过 P0 测试")
        return True

    print(f"{CYAN}=== 运行 P0 冒烟测试 ==={RESET}\n")
    result = subprocess.run(
        [sys.executable, str(p0_script)],
        cwd=_root(),
        timeout=120,
    )
    print()
    return result.returncode == 0


def get_version_from_submodules() -> str:
    """从子模块提取版本号。"""
    root = _root()
    try:
        # 尝试获取 hermes-agent 的 tag
        result = subprocess.run(
            ["git", "-C", str(root / "hermes-agent"), "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            # 如果 tag 是 v2026.4.16-103-gxxxx 格式，取第一部分
            if tag.startswith("v"):
                parts = tag.lstrip("v").split("-")
                if len(parts) >= 2:
                    # 取 v2026.4.16 这种日期版本
                    return parts[0]
            return tag
    except Exception:
        pass
    return "unknown"


def pack_7z(version: str, output_dir: Path) -> Path:
    """使用 7z 打包。"""
    root = _root()
    parent = root.parent
    output_file = output_dir / f"Hermes-Agent-Portable-v{version}.7z"

    cmd = [
        "7z", "a",
        "-t7z",
        "-m0=lzma2", "-mx=9", "-mfb=64", "-md=32m", "-ms=on",
        "-xr!.git",
        "-xr!skills",
        "-xr!scripts",
        str(output_file),
        f"{root.name}\\",
    ]

    print(f"{CYAN}=== 打包命令 ==={RESET}")
    print(f"  {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=parent)
    if result.returncode != 0:
        raise RuntimeError("7z 打包失败")

    return output_file


def pack_zip(version: str, output_dir: Path) -> Path:
    """使用 7z 的 zip 模式打包。"""
    root = _root()
    parent = root.parent
    output_file = output_dir / f"Hermes-Agent-Portable-v{version}.zip"

    cmd = [
        "7z", "a",
        "-tzip",
        "-mx=9",
        "-xr!.git",
        "-xr!skills",
        "-xr!scripts",
        str(output_file),
        f"{root.name}\\",
    ]

    print(f"{CYAN}=== 打包命令 ==={RESET}")
    print(f"  {' '.join(cmd)}\n")

    result = subprocess.run(cmd, cwd=parent)
    if result.returncode != 0:
        raise RuntimeError("7z zip 打包失败")

    return output_file


def pack_ps_zip(version: str, output_dir: Path) -> Path:
    """使用 PowerShell Compress-Archive 打包（无 7z 时的备用）。"""
    root = _root()
    parent = root.parent
    output_file = output_dir / f"Hermes-Agent-Portable-v{version}.zip"

    # Compress-Archive 不支持排除目录，需要先复制到临时目录
    import tempfile
    import shutil

    temp_dir = Path(tempfile.mkdtemp(prefix="hermes-pack-"))
    temp_pack = temp_dir / root.name

    print(f"{CYAN}=== 复制到临时目录（排除 skills/ scripts/ .git/）==={RESET}")
    shutil.copytree(root, temp_pack, ignore=shutil.ignore_patterns(
        ".git", "skills", "scripts"
    ))

    print(f"{CYAN}=== PowerShell Compress-Archive ==={RESET}")
    ps_cmd = [
        "powershell",
        "-Command",
        f"Compress-Archive -Path '{temp_pack}\*' -DestinationPath '{output_file}' -Force",
    ]
    result = subprocess.run(ps_cmd)

    # 清理临时目录
    shutil.rmtree(temp_dir, ignore_errors=True)

    if result.returncode != 0:
        raise RuntimeError("Compress-Archive 打包失败")

    return output_file


def detect_7z() -> bool:
    """检查系统是否有 7z。"""
    try:
        result = subprocess.run(
            ["7z"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0 or result.returncode == 7  # 7z 无参数时返回 7
    except FileNotFoundError:
        return False


def format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024 * 1024:
        return f"{size_bytes / (1024*1024*1024):.2f} GB"
    elif size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024*1024):.2f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.2f} KB"
    return f"{size_bytes} B"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes-Agent-Portable 一键打包",
        epilog="""
示例:
  python scripts/pack.py                  # 自动检测版本，7z 格式
  python scripts/pack.py -v 0.11.0        # 指定版本
  python scripts/pack.py -f zip           # zip 格式
  python scripts/pack.py --check-only     # 仅检查，不打包
  python scripts/pack.py --yes            # 自动确认版本号，无交互
  python scripts/pack.py --skip-p0        # 跳过 P0 测试（不推荐）
""",
    )
    parser.add_argument("-v", "--version", default="", help="版本号（默认从子模块自动检测）")
    parser.add_argument("-f", "--format", default="7z", choices=["7z", "zip"], help="压缩格式（默认 7z）")
    parser.add_argument("-o", "--output", default="", help="输出目录（默认整合包同级目录）")
    parser.add_argument("--check-only", action="store_true", help="只运行检查，不打包")
    parser.add_argument("--skip-check", action="store_true", help="跳过打包前检查")
    parser.add_argument("--skip-p0", action="store_true", help="跳过 P0 冒烟测试")
    parser.add_argument("-y", "--yes", action="store_true", help="自动确认版本号，跳过交互提示")
    args = parser.parse_args()

    root = _root()

    print(f"{BOLD}{CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     Hermes-Agent-Portable 一键打包                           ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    print(f"整合包根目录: {root}")
    print(f"压缩格式: {args.format}")
    print(f"排除项: .git/, skills/, scripts/")
    print()

    # Step 1: 打包前检查
    if not args.skip_check:
        if not run_pre_check():
            print(f"{RED}{BOLD}[FAIL] 打包前检查未通过，请修复问题后再试。{RESET}")
            print(f"{YELLOW}  或使用 --skip-check 强制跳过（不推荐）{RESET}")
            return 1
        if args.check_only:
            print(f"{GREEN}{BOLD}[OK] 检查完成，--check-only 模式，不打包。{RESET}")
            return 0
    else:
        print(f"{YELLOW}[WARN] 已跳过打包前检查{RESET}\n")

    # Step 2: P0 冒烟测试
    if not args.skip_p0:
        if not run_p0_test():
            print(f"{RED}{BOLD}[FAIL] P0 冒烟测试未通过，不能打包！{RESET}")
            print(f"{YELLOW}  或使用 --skip-p0 强制跳过（不推荐）{RESET}")
            return 1
    else:
        print(f"{YELLOW}[WARN] 已跳过 P0 冒烟测试{RESET}\n")

    # Step 3: 确定版本号
    version = args.version
    if not version:
        version = get_version_from_submodules()
        print(f"{CYAN}自动检测到版本号: {version}{RESET}")
        if args.yes:
            print(f"{GREEN}自动确认（--yes）{RESET}")
        else:
            confirm = input(f"确认使用该版本号打包? [Y/n] ")
            if confirm.lower() == "n":
                version = input("请输入版本号: ").strip()
    else:
        print(f"指定版本号: {version}")

    if not version or version == "unknown":
        print(f"{RED}错误: 无法确定版本号，请使用 -v 指定。{RESET}")
        return 1

    # Step 3: 确定输出目录
    output_dir = Path(args.output) if args.output else root.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Step 4: 打包
    print(f"{CYAN}=== 开始打包 ==={RESET}\n")

    has_7z = detect_7z()
    if not has_7z and args.format == "7z":
        print(f"{YELLOW}7z 未安装，自动降级为 zip 格式{RESET}")
        args.format = "zip"

    try:
        if args.format == "7z":
            output_file = pack_7z(version, output_dir)
        else:
            if has_7z:
                output_file = pack_zip(version, output_dir)
            else:
                print(f"{YELLOW}使用 PowerShell Compress-Archive 打包（较慢）{RESET}")
                output_file = pack_ps_zip(version, output_dir)

        size = output_file.stat().st_size
        print(f"\n{GREEN}{BOLD}[OK] 打包完成！{RESET}")
        print(f"  文件: {output_file}")
        print(f"  大小: {format_size(size)}")
        print(f"  格式: {args.format}")
        print(f"  排除: .git/, skills/, scripts/")
        return 0

    except Exception as e:
        print(f"\n{RED}{BOLD}[FAIL] 打包失败: {e}{RESET}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
