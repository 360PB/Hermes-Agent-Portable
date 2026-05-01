#!/usr/bin/env python3
"""
Hermes-Agent-Portable P0 冒烟测试

在打包前运行，确保核心模块可导入、关键依赖就位、
Windows 兼容性补丁生效。

用法:
    python scripts/p0-test.py        # 运行全部测试
    python scripts/p0-test.py -v     # 详细模式
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

# 自动设置 PYTHONPATH（确保在子进程或被直接调用时都能正确导入）
_our_dir = Path(__file__).resolve().parent.parent
_agent = str(_our_dir / "hermes-agent")
_venv = str(_our_dir / "venv" / "Lib" / "site-packages")
_webui = str(_our_dir / "hermes-webui")
_current = os.environ.get("PYTHONPATH", "")
_parts = [p for p in [_agent, _venv, _webui, _current] if p]
if _parts:
    os.environ["PYTHONPATH"] = ";".join(_parts)
    # 将路径插入 sys.path 前端，避免已有缓存导致不生效
    for p in (_webui, _venv, _agent):
        if p not in sys.path:
            sys.path.insert(0, p)

RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
RESET = "\033[0m"
BOLD = "\033[1m"


class P0TestRunner:
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors: list[tuple[str, Exception]] = []

    def _ok(self, name: str) -> None:
        self.passed += 1
        print(f"  {GREEN}[OK]{RESET} {name}")

    def _fail(self, name: str, exc: Exception) -> None:
        self.failed += 1
        self.errors.append((name, exc))
        print(f"  {RED}[FAIL]{RESET} {name}: {exc}")

    def _warn(self, name: str, msg: str) -> None:
        self.warnings += 1
        print(f"  {YELLOW}[WARN]{RESET} {name}: {msg}")

    def check_import(self, name: str, module_path: str | None = None) -> bool:
        """测试模块可导入。"""
        try:
            mod = importlib.import_module(name)
            if self.verbose and mod.__file__:
                self._ok(f"{name}  ({mod.__file__})")
            else:
                self._ok(name)
            return True
        except Exception as exc:
            self._fail(name, exc)
            return False

    def check_version(self, name: str, attr: str = "__version__") -> bool:
        """测试模块有版本号属性。"""
        try:
            mod = importlib.import_module(name)
            ver = getattr(mod, attr, "unknown")
            self._ok(f"{name}  ({ver})")
            return True
        except Exception as exc:
            self._fail(name, exc)
            return False

    def section(self, title: str) -> None:
        print(f"\n{BOLD}{CYAN}=== {title} ==={RESET}")

    def run(self) -> int:
        root = Path(__file__).resolve().parent.parent
        webui_path = root / "hermes-webui"

        # -- 核心导入 --------------------------------------------------
        self.section("P0: Core Imports")
        self.check_import("hermes_cli")
        self.check_import("hermes_cli.main")
        self.check_import("hermes_cli.web_server")
        self.check_import("hermes_cli.pty_bridge")
        self.check_import("agent")
        self.check_import("gateway.run")
        self.check_import("tools")
        self.check_import("cron.scheduler")

        # -- 新依赖 ----------------------------------------------------
        self.section("P0: New Dependencies")
        self.check_version("croniter")

        # -- WebUI -----------------------------------------------------
        self.section("P0: WebUI")
        if webui_path.exists():
            sys.path.insert(0, str(webui_path))
            self.check_import("server")
            sys.path.pop(0)
        else:
            self._fail("webui server", FileNotFoundError("hermes-webui/ not found"))

        # -- 关键第三方依赖 --------------------------------------------
        self.section("P0: Key Dependencies")
        self.check_version("fastapi")
        self.check_version("pydantic")
        self.check_version("httpx")
        self.check_version("rich")
        self.check_version("yaml", "__version__")
        self.check_version("starlette")
        self.check_version("prompt_toolkit")

        # -- Windows 兼容性 --------------------------------------------
        self.section("P0: Windows Compatibility")
        try:
            # pty_bridge 曾经因直接 import fcntl 在 Windows 上崩溃
            import hermes_cli.pty_bridge as pb

            if pb.fcntl is None and pb.termios is None:
                self._ok("pty_bridge fcntl/termios fallback")
            else:
                self._warn(
                    "pty_bridge",
                    "fcntl/termios available (running on POSIX?)",
                )
        except Exception as exc:
            self._fail("pty_bridge fallback", exc)

        # -- 汇总 ------------------------------------------------------
        total = self.passed + self.failed + self.warnings
        print(f"\n{BOLD}{CYAN}=== P0 测试汇总 ==={RESET}")
        print(f"  {GREEN}通过: {self.passed}{RESET}")
        print(f"  {RED}失败: {self.failed}{RESET}")
        print(f"  {YELLOW}警告: {self.warnings}{RESET}")
        print(f"  总计: {total}")

        if self.failed:
            print(f"\n{RED}{BOLD}✗ P0 测试未通过，不能打包！{RESET}")
            print(f"{YELLOW}  请修复上述错误后再运行打包。{RESET}")
            return 1

        print(f"\n{GREEN}{BOLD}✓ P0 测试通过，可以安全打包。{RESET}")
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Hermes-Agent-Portable P0 冒烟测试")
    parser.add_argument("-v", "--verbose", action="store_true", help="详细模式")
    args = parser.parse_args()

    print(f"{BOLD}{CYAN}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║     Hermes-Agent-Portable P0 冒烟测试                        ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{RESET}")
    print(f"Python: {sys.version.split()[0]}")
    print(f"平台:   {sys.platform}")

    runner = P0TestRunner(verbose=args.verbose)
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())
