#!/usr/bin/env python3
"""
Hermes-Agent-Portable 打包前检查脚本

用法:
    python scripts/pre-pack-check.py
    python scripts/pre-pack-check.py --fix

--fix 模式下会尝试自动修复部分问题（如构建 web_dist）
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 修复 Windows GBK 编码问题
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 颜色码
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"

CHECKS_PASSED = 0
CHECKS_FAILED = 0
CHECKS_WARN = 0


def ok(msg: str) -> None:
    global CHECKS_PASSED
    CHECKS_PASSED += 1
    print(f"  {GREEN}[OK]{RESET} {msg}")


def fail(msg: str) -> None:
    global CHECKS_FAILED
    CHECKS_FAILED += 1
    print(f"  {RED}[FAIL]{RESET} {msg}")


def warn(msg: str) -> None:
    global CHECKS_WARN
    CHECKS_WARN += 1
    print(f"  {YELLOW}[WARN]{RESET} {msg}")


def info(msg: str) -> None:
    print(f"  {CYAN}[INFO]{RESET} {msg}")


def section(title: str) -> None:
    print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")


def _root() -> Path:
    """返回整合包根目录。"""
    return Path(__file__).resolve().parent.parent


def check_directory_structure() -> None:
    """1. 目录结构完整性检查"""
    section("1. 目录结构完整性")
    root = _root()

    required_dirs = [
        ("hermes-agent", "Hermes Agent 源码"),
        ("hermes-webui", "Hermes WebUI 源码"),
        ("python_runtime", "Python 运行时"),
        ("venv", "虚拟环境依赖"),
        ("tools", "工具目录"),
    ]

    for dirname, desc in required_dirs:
        path = root / dirname
        if path.exists() and path.is_dir():
            count = len(list(path.iterdir()))
            if count > 0:
                ok(f"{desc}: `{dirname}/` 存在且非空 ({count} 项)")
            else:
                fail(f"{desc}: `{dirname}/` 为空目录")
        else:
            fail(f"{desc}: `{dirname}/` 不存在")


def check_bat_files() -> None:
    """2. 启动脚本存在性 + 内容正确性检查"""
    section("2. 启动脚本检查")
    root = _root()

    required_bats = {
        "start-hermes.bat": ["hermes-agent", "hermes_cli.main chat"],
        "start-webui.bat": ["hermes-webui", "server.py"],
        "test-hermes.bat": ["hermes-agent", "hermes_cli.main chat -q"],
        "update-hermes.bat": ["update-upstream.ps1"],
        "hermes ui.bat": ["hermes-agent", "hermes_cli.main dashboard"],
    }

    for filename, expected_snippets in required_bats.items():
        path = root / filename
        if not path.exists():
            fail(f"启动脚本缺失: `{filename}`")
            continue

        content = path.read_text(encoding="utf-8")
        missing = [s for s in expected_snippets if s not in content]

        if missing:
            fail(f"`{filename}` 内容异常，缺少: {missing}")
        else:
            ok(f"`{filename}` 存在且内容正确")

        # 关键: PYTHONPATH 必须包含 hermes-agent 源码目录
        if filename in ("start-hermes.bat", "test-hermes.bat", "hermes ui.bat"):
            if r"%CD%\hermes-agent" in content:
                ok(f"`{filename}` PYTHONPATH 源码优先 ✓")
            else:
                fail(f"`{filename}` PYTHONPATH 未包含 `hermes-agent` 源码目录！运行会加载旧版本！")


def check_python_runtime() -> None:
    """3. Python 运行时可用性检查"""
    section("3. Python 运行时检查")
    root = _root()
    py_exe = root / "python_runtime" / "python.exe"

    if not py_exe.exists():
        fail(f"Python 解释器不存在: {py_exe}")
        return

    try:
        result = subprocess.run(
            [str(py_exe), "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            ok(f"Python 可用: {result.stdout.strip()}")
        else:
            fail(f"Python 启动失败: {result.stderr}")
    except Exception as e:
        fail(f"Python 测试异常: {e}")


def check_venv_dependencies() -> None:
    """4. venv 依赖可用性检查"""
    section("4. venv 依赖检查")
    root = _root()
    py_exe = root / "python_runtime" / "python.exe"
    venv_site = root / "venv" / "Lib" / "site-packages"

    if not py_exe.exists():
        warn("Python 不可用，跳过依赖检查")
        return

    critical_packages = [
        "fastapi",
        "httpx",
        "prompt_toolkit",
        "pydantic",
        "rich",
        "starlette",
        "yaml",
    ]

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{root / 'hermes-agent'};{venv_site}"
    env["PYTHONIOENCODING"] = "utf-8"

    for pkg in critical_packages:
        try:
            result = subprocess.run(
                [str(py_exe), "-c", f"import {pkg}; print({pkg}.__file__)"],
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            if result.returncode == 0:
                ok(f"`{pkg}` 可导入")
            else:
                fail(f"`{pkg}` 导入失败: {result.stderr.strip()}")
        except Exception as e:
            fail(f"`{pkg}` 检查异常: {e}")


def check_hermes_cli_import() -> None:
    """5. hermes_cli 可导入性检查（源码优先模式）"""
    section("5. hermes_cli 源码导入检查")
    root = _root()
    py_exe = root / "python_runtime" / "python.exe"
    venv_site = root / "venv" / "Lib" / "site-packages"

    if not py_exe.exists():
        warn("Python 不可用，跳过")
        return

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{root / 'hermes-agent'};{venv_site}"
    env["PYTHONIOENCODING"] = "utf-8"

    script = "import hermes_cli; print(hermes_cli.__file__)"
    try:
        result = subprocess.run(
            [str(py_exe), "-c", script],
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        if result.returncode == 0:
            path = result.stdout.strip()
            if "hermes-agent" in path.replace("\\", "/"):
                ok(f"hermes_cli 从源码加载: {path}")
            else:
                fail(f"hermes_cli 未从源码加载！当前路径: {path}")
                info("请检查 .bat 脚本的 PYTHONPATH 是否包含 hermes-agent 目录")
        else:
            fail(f"hermes_cli 导入失败: {result.stderr.strip()}")
    except Exception as e:
        fail(f"hermes_cli 检查异常: {e}")


def check_dashboard_web_dist(fix: bool = False) -> None:
    """6. Dashboard 前端产物检查（打包前关键！）"""
    section("6. Dashboard 前端产物检查")
    root = _root()
    web_dist = root / "hermes-agent" / "hermes_cli" / "web_dist"
    web_src = root / "hermes-agent" / "web"

    critical_items = [
        (web_dist / "index.html", "index.html"),
        (web_dist / "assets", "assets/ 目录"),
    ]

    all_exist = True
    for item, name in critical_items:
        if item.exists():
            ok(f"`web_dist/{name}` 存在")
        else:
            fail(f"`web_dist/{name}` 不存在")
            all_exist = False

    if not all_exist:
        if fix and web_src.exists():
            npm = shutil.which("npm")
            if npm:
                info("尝试自动构建 web_dist...")
                try:
                    r1 = subprocess.run(
                        [npm, "install", "--silent"],
                        cwd=web_src,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if r1.returncode != 0:
                        fail(f"npm install 失败: {r1.stderr}")
                        return

                    r2 = subprocess.run(
                        [npm, "run", "build"],
                        cwd=web_src,
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if r2.returncode == 0:
                        ok("web_dist 自动构建成功")
                        for item, name in critical_items:
                            if item.exists():
                                ok(f"`web_dist/{name}` 构建后已存在")
                            else:
                                fail(f"`web_dist/{name}` 构建后仍不存在")
                    else:
                        fail(f"npm run build 失败: {r2.stderr}")
                except Exception as e:
                    fail(f"自动构建异常: {e}")
            else:
                fail("npm 未安装，无法自动修复。请安装 Node.js 后重试。")
        else:
            warn("缺少 web_dist 会导致 `hermes ui.bat` 在新电脑报错:")
            warn('  "Web UI frontend not built and npm is not available."')
            if not fix:
                info("提示: 运行 `python scripts/pre-pack-check.py --fix` 尝试自动构建")


def check_git_submodules() -> None:
    """7. Git 子模块状态检查"""
    section("7. Git 子模块状态")
    root = _root()

    if not (root / ".git").exists():
        warn("根目录不是 Git 仓库，跳过子模块检查")
        return

    if (root / ".gitmodules").exists():
        ok("`.gitmodules` 存在")
    else:
        fail("`.gitmodules` 不存在")

    for subdir in ["hermes-agent", "hermes-webui"]:
        git_file = root / subdir / ".git"
        if git_file.exists():
            ok(f"`{subdir}/` 子模块已初始化")
        else:
            fail(f"`{subdir}/` 子模块未初始化！运行: git submodule update --init")

    try:
        result = subprocess.run(
            ["git", "submodule", "status"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.startswith("+"):
                    warn(f"子模块有新提交未记录: {line[:70]}")
                    info("  建议: cd <subdir> && git log --oneline -3 查看差异")
                elif line.startswith("-"):
                    fail(f"子模块未检出: {line[:70]}")
                elif line.startswith("U"):
                    fail(f"子模块有合并冲突: {line[:70]}")
                else:
                    ok(f"子模块状态正常: {line[:70]}")
    except Exception as e:
        warn(f"子模块状态检查异常: {e}")


def check_dashboard_source_fix() -> None:
    """8. Dashboard 源码修复检查"""
    section("8. Dashboard 源码修复检查")
    root = _root()
    main_py = root / "hermes-agent" / "hermes_cli" / "main.py"

    if not main_py.exists():
        warn("`main.py` 不存在，跳过源码检查")
        return

    content = main_py.read_text(encoding="utf-8")

    # 检查 cmd_dashboard 中是否包含 web_dist 跳过逻辑
    has_web_dist_check = "web_dist" in content and "web_dist.exists()" in content
    has_skip_comment = "Skip build if web_dist" in content

    if has_web_dist_check and has_skip_comment:
        ok("`cmd_dashboard` 已包含 web_dist 存在性检查，新电脑无需 npm")
    else:
        fail("`cmd_dashboard` 缺少 web_dist 存在性检查！")
        info("  这会导致新电脑运行 `hermes ui.bat` 时报错:")
        info('    "Web UI frontend not built and npm is not available."')
        info("  修复方法: 在 `cmd_dashboard` 中添加:")
        info("    web_dist = PROJECT_ROOT / 'hermes_cli' / 'web_dist'")
        info("    if not (web_dist.exists() and (web_dist / 'index.html').exists()):")
        info("        if not _build_web_ui(PROJECT_ROOT / 'web', fatal=True):")
        info("            sys.exit(1)")


def check_no_backup_dirs() -> None:
    """9. 清理残留备份目录"""
    section("9. 残留文件检查")
    root = _root()

    suspicious = list(root.glob("*.backup*")) + list(root.glob("*.bak*"))
    if suspicious:
        for p in suspicious:
            warn(f"发现残留备份: `{p.name}`")
        info("建议: 删除这些目录以减小包体积")
    else:
        ok("无残留备份目录")

    # 只检查源码目录中的 __pycache__（venv 和 python_runtime 中的会在运行时重新生成）
    pycaches = [
        p for p in root.rglob("__pycache__")
        if "hermes-agent" in str(p) or "hermes-webui" in str(p)
    ]
    if pycaches:
        warn(f"发现 {len(pycaches)} 个源码中的 `__pycache__` 目录")
        info("建议: 打包前清理以减小体积")
    else:
        ok("无源码 `__pycache__` 缓存")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hermes-Agent-Portable 打包前检查",
        epilog="""
示例:
  python scripts/pre-pack-check.py        # 仅检查
  python scripts/pre-pack-check.py --fix  # 检查并尝试自动修复
""",
    )
    parser.add_argument("--fix", action="store_true", help="尝试自动修复检测到的问题")
    args = parser.parse_args()

    print(f"{BOLD}{CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     Hermes-Agent-Portable 打包前完整性检查                   ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    print(f"根目录: {_root()}")
    print(f"模式: {'自动修复' if args.fix else '仅检查'}")

    check_directory_structure()
    check_bat_files()
    check_python_runtime()
    check_venv_dependencies()
    check_hermes_cli_import()
    check_dashboard_web_dist(fix=args.fix)
    check_git_submodules()
    check_dashboard_source_fix()
    check_no_backup_dirs()

    total = CHECKS_PASSED + CHECKS_FAILED + CHECKS_WARN
    print(f"\n{BOLD}{CYAN}=== 检查汇总 ==={RESET}")
    print(f"  {GREEN}通过: {CHECKS_PASSED}{RESET}")
    print(f"  {RED}失败: {CHECKS_FAILED}{RESET}")
    print(f"  {YELLOW}警告: {CHECKS_WARN}{RESET}")
    print(f"  总计: {total}")

    if CHECKS_FAILED > 0:
        print(f"\n{RED}{BOLD}✗ 打包检查未通过，请修复上述问题后再打包！{RESET}")
        return 1

    # 检查通过，输出打包建议
    print(f"\n{GREEN}{BOLD}✓ 检查通过！{RESET}")
    if CHECKS_WARN > 0:
        print(f"{YELLOW}{BOLD}⚠ 有 {CHECKS_WARN} 个警告项，建议确认后再打包。{RESET}")

    print(f"\n{BOLD}{CYAN}=== 打包命令 ==={RESET}")
    print(f"  一键打包:")
    print(f"    python_runtime\\python.exe scripts\\pack.py")
    print(f"")
    print(f"  手动打包（排除 .git/ skills/ scripts/）:")
    print(f"    7z a -t7z -mx=9 -xr!.git -xr!skills -xr!scripts Hermes-Agent-Portable-vX.Y.Z.7z Hermes-Agent-Portable\\")
    print(f"")
    print(f"  PowerShell 打包（无 7z 时，较慢）:")
    print(f"    Compress-Archive -Path 'Hermes-Agent-Portable\\*' -DestinationPath 'Hermes-Agent-Portable-vX.Y.Z.zip' -Force")
    print(f"    {YELLOW}注意: Compress-Archive 无法排除目录，会包含 skills/ 和 scripts/{RESET}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
