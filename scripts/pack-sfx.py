#!/usr/bin/env python3
"""
Hermes-Agent-Portable 自解压 EXE 打包脚本

用法:
    python scripts/pack-sfx.py                    # 从现有 7z 生成 SFX
    python scripts/pack-sfx.py --version 0.12     # 指定版本
    python scripts/pack-sfx.py --from-scratch     # 重新压缩并生成 SFX

原理:
    copy /b 7z.sfx + config.txt + archive.7z output.exe
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

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


def find_7z_sfx() -> Path | None:
    """查找 7z SFX 模块。"""
    candidates = [
        Path(r"C:\Program Files\7-Zip\7z.sfx"),
        Path(r"C:\Program Files (x86)\7-Zip\7z.sfx"),
        Path(r"C:\Tools\7-Zip\7z.sfx"),
    ]
    for p in candidates:
        if p.exists():
            return p
    # 尝试从 PATH 推断
    seven_zip = shutil.which("7z")
    if seven_zip:
        sfx = Path(seven_zip).parent / "7z.sfx"
        if sfx.exists():
            return sfx
    return None


def get_version() -> str:
    """从子模块提取版本号。"""
    root = _root()
    try:
        result = subprocess.run(
            ["git", "-C", str(root / "hermes-agent"), "describe", "--tags", "--always"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            tag = result.stdout.strip()
            if tag.startswith("v"):
                parts = tag.lstrip("v").split("-")
                if len(parts) >= 2:
                    return parts[0]
            return tag
    except Exception:
        pass
    return "unknown"


def create_sfx_config(version: str, output_path: Path) -> Path:
    """创建 SFX 配置文件。"""
    config = f""";!@Install@!UTF-8!
Title="Hermes Agent Portable v{version}"
BeginPrompt="即将解压 Hermes Agent Portable v{version}。\\n\\n建议解压到一个独立文件夹（如 D:\\Hermes-Agent-Portable）。"
ExtractPathText="目标文件夹："
ExtractDialogWidth=480
GUIMode="1"
InstallPath="%USERPROFILE%\\Hermes-Agent-Portable"
OverwriteMode="2"
RunProgram="explorer.exe \"%T\""
;!@InstallEnd@!
"""
    config_path = output_path.parent / "_sfx_config.txt"
    config_path.write_text(config, encoding="utf-8")
    return config_path


def create_sfx_from_7z(archive_7z: Path, version: str, output_exe: Path) -> bool:
    """从现有 7z 创建自解压 exe。"""
    sfx_module = find_7z_sfx()
    if not sfx_module:
        print(f"{RED}错误: 找不到 7z.sfx 模块。请安装 7-Zip。{RESET}")
        return False

    print(f"{CYAN}SFX 模块: {sfx_module}{RESET}")

    config_path = create_sfx_config(version, output_exe)
    print(f"{CYAN}SFX 配置: {config_path}{RESET}")

    # 使用 copy /b 合并: sfx + config + archive
    cmd = [
        "cmd", "/c", "copy", "/b",
        f'"{sfx_module}"', "+",
        f'"{config_path}"', "+",
        f'"{archive_7z}"',
        f'"{output_exe}"',
    ]

    print(f"{CYAN}=== 生成自解压 EXE ==={RESET}")
    result = subprocess.run(" ".join(cmd), shell=True)

    config_path.unlink(missing_ok=True)

    if result.returncode != 0:
        print(f"{RED}生成失败{RESET}")
        return False

    return True


def create_7z_then_sfx(version: str, output_exe: Path) -> bool:
    """重新压缩并创建自解压 exe。"""
    root = _root()
    parent = root.parent
    temp_7z = parent / f"_Hermes-Agent-Portable-v{version}.7z"

    print(f"{CYAN}=== 先创建 7z 压缩包 ==={RESET}")
    cmd = [
        "7z", "a",
        "-t7z",
        "-m0=lzma2", "-mx=9", "-mfb=64", "-md=32m", "-ms=on",
        "-xr!.git",
        "-xr!skills",
        "-xr!scripts",
        str(temp_7z),
        f"{root.name}\\",
    ]
    result = subprocess.run(cmd, cwd=parent)
    if result.returncode != 0:
        print(f"{RED}7z 压缩失败{RESET}")
        return False

    success = create_sfx_from_7z(temp_7z, version, output_exe)
    temp_7z.unlink(missing_ok=True)
    return success


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
        description="Hermes-Agent-Portable 自解压 EXE 打包",
        epilog="""
示例:
  python scripts/pack-sfx.py                  # 从现有 7z 生成 SFX
  python scripts/pack-sfx.py --version 0.12   # 指定版本
  python scripts/pack-sfx.py --from-scratch   # 重新压缩并生成
""",
    )
    parser.add_argument("-v", "--version", default="", help="版本号（默认自动检测）")
    parser.add_argument("--from-scratch", action="store_true", help="重新压缩并生成（而非使用现有 7z）")
    parser.add_argument("--skip-p0", action="store_true", help="跳过 P0 冒烟测试")
    parser.add_argument("-o", "--output", default="", help="输出路径（默认整合包同级目录）")
    args = parser.parse_args()

    root = _root()

    print(f"{BOLD}{CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     Hermes-Agent-Portable 自解压 EXE 打包                    ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")

    # 确定版本号
    version = args.version
    if not version:
        version = get_version()
        print(f"{CYAN}自动检测到版本号: {version}{RESET}")
    else:
        print(f"指定版本号: {version}")

    if not version or version == "unknown":
        print(f"{RED}错误: 无法确定版本号{RESET}")
        return 1

    # 确定输出路径
    output_dir = Path(args.output) if args.output else root.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    output_exe = output_dir / f"Hermes-Agent-Portable-v{version}.exe"

    if args.from_scratch:
        success = create_7z_then_sfx(version, output_exe)
    else:
        # 尝试找到现有 7z
        archive_7z = root.parent / f"Hermes-Agent-Portable-v{version}.7z"
        if not archive_7z.exists():
            # 尝试找任意版本 7z
            candidates = list(root.parent.glob("Hermes-Agent-Portable-v*.7z"))
            if candidates:
                archive_7z = candidates[0]
                print(f"{YELLOW}使用现有压缩包: {archive_7z.name}{RESET}")
            else:
                print(f"{YELLOW}未找到现有 7z，将重新压缩...{RESET}")
                success = create_7z_then_sfx(version, output_exe)
                if not success:
                    return 1
                # 继续到输出统计
                archive_7z = None
        if archive_7z:
            success = create_sfx_from_7z(archive_7z, version, output_exe)

    if not success or not output_exe.exists():
        print(f"\n{RED}{BOLD}[FAIL] 自解压 EXE 生成失败{RESET}")
        return 1

    size = output_exe.stat().st_size
    print(f"\n{GREEN}{BOLD}[OK] 自解压 EXE 生成完成！{RESET}")
    print(f"  文件: {output_exe}")
    print(f"  大小: {format_size(size)}")
    print(f"  说明: 双击即可运行，选择解压路径后自动解压")
    return 0


if __name__ == "__main__":
    sys.exit(main())
