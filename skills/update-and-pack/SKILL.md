# Hermes-Agent-Portable 更新与打包 Skill

> 自动化整合包的版本更新、源码同步和打包发布流程。

---

## 适用场景

- 用户说："更新整合包"
- 用户说："同步上游最新代码"
- 用户说："重新打包"
- 用户说："发布新版本"
- 用户说："打包成 zip"

---

## 项目结构

```
Hermes-Agent-Portable/
├── hermes-agent/           ← Git Submodule (nousresearch/hermes-agent)
├── hermes-webui/           ← Git Submodule (nesquena/hermes-webui)
├── python_runtime/         ← 便携 Python 3.11
├── venv/                   ← 依赖包
├── tools/                  ← uv 等工具
├── scripts/
│   └── pre-pack-check.py   ← 打包前检查脚本
├── start-hermes.bat
├── start-webui.bat
├── update-hermes.bat       ← 一键同步入口
├── update-upstream.ps1     ← PowerShell 同步脚本
└── .gitmodules             ← 子模块声明
```

---

## 核心原则

1. **先检查，后打包** — 始终运行 `pre-pack-check.py`
2. **源码优先** — PYTHONPATH 中 `hermes-agent` 必须在 venv 之前
3. **web_dist 预构建** — Dashboard 前端必须预构建，不能依赖新电脑有 npm
4. **Git 子模块** — 精确记录上游版本，一键同步

---

## 完整更新流程

### 步骤 1：同步上游子模块

```powershell
cd Hermes-Agent-Portable

# 方式 A: 使用一键脚本
cd ..
.\Hermes-Agent-Portable\update-hermes.bat

# 方式 B: 手动同步
# hermes-agent
cd hermes-agent
git fetch origin
git pull origin main

# hermes-webui
cd ../hermes-webui
git fetch origin
git pull origin main

# 记录指针到主仓库
cd ..
git add hermes-agent hermes-webui
git commit -m "sync: bump upstream`n`n- hermes-agent: $(git -C hermes-agent rev-parse --short HEAD)`n- hermes-webui: $(git -C hermes-webui rev-parse --short HEAD)"
```

### 步骤 2：运行打包前检查

```powershell
cd Hermes-Agent-Portable
python_runtime\python.exe scripts\pre-pack-check.py
```

### 步骤 3：P0 冒烟测试（打包前必做）

确保核心模块能正常导入、Windows 兼容性补丁生效、关键依赖就位。

```powershell
cd Hermes-Agent-Portable
python_runtime\python.exe scripts\p0-test.py
```

**P0 测试覆盖**：

| 类别 | 检查项 |
|------|--------|
| Core Imports | hermes_cli, main, web_server, pty_bridge, agent, gateway, tools, cron |
| New Dependencies | croniter 等上游新增依赖 |
| WebUI | server.py 可导入 |
| Key Deps | fastapi, pydantic, httpx, rich, yaml, starlette, prompt_toolkit |
| Windows 兼容 | pty_bridge fcntl/termios fallback 生效 |

**关键检查项**：

| # | 检查项 | 失败后果 | 自动修复 |
|---|--------|----------|----------|
| 1 | 目录结构 | 包不完整 | 否 |
| 2 | 启动脚本 PYTHONPATH | 运行旧版本 | 否 |
| 3 | Python 运行时 | 完全无法启动 | 否 |
| 4 | venv 依赖 | 模块缺失 | 否 |
| 5 | hermes_cli 从源码加载 | 运行旧版本 | 否 |
| 6 | `web_dist/index.html` | Dashboard 报错 | 是（需 npm） |
| 7 | Dashboard 源码修复 | `npm not available` | 否 |
| 8 | Git 子模块状态 | 版本不可追溯 | 否 |
| 9 | 残留备份/缓存 | 体积过大 | 是 |
| 10 | P0 冒烟测试 | 打包后软件无法启动 | 否 |

如果检查失败，先修复问题，再重新运行检查。

### 步骤 4：构建 Dashboard 前端（如需）

如果检查项 6 失败，需要构建 web_dist：

```powershell
cd Hermes-Agent-Portable\hermes-agent\web
npm install
npm run build
# 产物自动输出到 ../hermes_cli/web_dist/
```

构建完成后重新运行检查。

### 步骤 5：确认 Dashboard 源码修复

如果检查项 7 失败，说明上游代码覆盖了 `cmd_dashboard` 的修复，需要重新添加：

在 `hermes-agent/hermes_cli/main.py` 的 `cmd_dashboard` 函数中：

```python
def cmd_dashboard(args):
    """Start the web UI server."""
    try:
        import fastapi  # noqa: F401
        import uvicorn  # noqa: F401
    except ImportError:
        print("Web UI dependencies not installed.")
        print("Install them with:  pip install hermes-agent[web]")
        sys.exit(1)

    # Skip build if web_dist already exists (pre-built portable bundle)
    web_dist = PROJECT_ROOT / "hermes_cli" / "web_dist"
    if not (web_dist.exists() and (web_dist / "index.html").exists()):
        if not _build_web_ui(PROJECT_ROOT / "web", fatal=True):
            sys.exit(1)

    from hermes_cli.web_server import start_server
    start_server(
        host=args.host,
        port=args.port,
        open_browser=not args.no_open,
        allow_public=getattr(args, "insecure", False),
    )
```

### 步骤 6：清理缓存

```powershell
cd Hermes-Agent-Portable

# 删除所有 __pycache__
Get-ChildItem -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Recurse -Force $_.FullName
}

# 删除 .pyc/.pyo
Get-ChildItem -Recurse -File -Include "*.pyc","*.pyo" -ErrorAction SilentlyContinue | ForEach-Object {
    Remove-Item -Force $_.FullName
}

# 删除备份目录
Remove-Item -Recurse -Force *.backup* -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force *.bak* -ErrorAction SilentlyContinue
```

### 步骤 7：打包

**一键打包（推荐）**：

```powershell
cd Hermes-Agent-Portable

# 自动检测版本，7z 格式，排除 .git/ skills/ scripts/
python_runtime\python.exe scripts\pack.py

# 指定版本号
python_runtime\python.exe scripts\pack.py --version 0.11.0

# zip 格式
python_runtime\python.exe scripts\pack.py --format zip

# 仅检查，不打包
python_runtime\python.exe scripts\pack.py --check-only

# 自动确认版本号，无交互（CI/自动化场景）
python_runtime\python.exe scripts\pack.py --yes
```

**手动打包**：

```powershell
cd ..  # 到整合包父目录

# 7z 压缩（推荐，体积更小）
# 排除: .git/ (Git 历史) skills/ (AI skill 文档) scripts/ (打包/检查脚本)
7z a -t7z -m0=lzma2 -mx=9 -mfb=64 -md=32m -ms=on "-xr!.git" "-xr!skills" "-xr!scripts" "Hermes-Agent-Portable-vX.Y.Z.7z" "Hermes-Agent-Portable\"

# zip 压缩（兼容性更好）
7z a -tzip "-xr!.git" "-xr!skills" "-xr!scripts" "Hermes-Agent-Portable-vX.Y.Z.zip" "Hermes-Agent-Portable\"
```

**自解压 EXE 打包（Windows 用户友好）**：

```powershell
cd Hermes-Agent-Portable

# 从现有 7z 直接生成自解压 exe（最快）
python_runtime\python.exe scripts\pack-sfx.py --version 0.12

# 重新压缩并生成自解压 exe
python_runtime\python.exe scripts\pack-sfx.py --from-scratch

# 指定输出目录
python_runtime\python.exe scripts\pack-sfx.py -o D:\Release
```

生成的 `.exe` 双击即可运行，弹出 GUI 向导让用户选择解压路径，默认解压到 `%USERPROFILE%\Hermes-Agent-Portable`。解压完成后**自动打开目标文件夹**（通过 `explorer.exe`），方便用户直接找到启动脚本。

**注意**：`skills/` 和 `scripts/` 是给维护者/AI 使用的，用户不需要。打包时务必排除，可减小约 10 KB 体积并避免用户困惑。

**PowerShell 原生压缩（无 7z 时备用）**：

```powershell
# Compress-Archive 不支持排除目录，会包含 skills/ 和 scripts/
# 如需排除，先复制到临时目录再压缩
$temp = New-TemporaryFile; $tempDir = "$temp-dir"
robocopy "Hermes-Agent-Portable" "$tempDir\Hermes-Agent-Portable" /E /XD ".git" "skills" "scripts"
Compress-Archive -Path "$tempDir\Hermes-Agent-Portable\*" -DestinationPath "Hermes-Agent-Portable-vX.Y.Z.zip" -Force
Remove-Item -Recurse -Force $tempDir
```

**建议**：优先使用 `scripts/pack.py` 一键脚本，自动处理所有细节。

### 步骤 8：版本管理

```powershell
cd Hermes-Agent-Portable

# 查看子模块当前版本
$agentVer = git -C hermes-agent describe --tags --always 2>$null
$webuiVer = git -C hermes-webui describe --tags --always 2>$null
Write-Host "hermes-agent: $agentVer"
Write-Host "hermes-webui: $webuiVer"

# 创建 tag（发布用）
git tag -a "v0.10.0" -m "Hermes Agent v0.10.0`n`n- hermes-agent: $agentVer`n- hermes-webui: $webuiVer"
git push origin v0.10.0
```

---

## 常见上游更新后的问题

### 问题 1：PYTHONPATH 被覆盖

**现象**：`start-hermes.bat` 运行的是 venv 里的旧版本。

**原因**：上游代码更新了启动脚本，覆盖了 `PYTHONPATH` 修改。

**修复**：确保 `.bat` 文件中：
```batch
set PYTHONPATH=%CD%\hermes-agent;%CD%\venv\Lib\site-packages
```

### 问题 2：`hermes ui.bat` 报 `npm not available`

**现象**：新电脑运行 `hermes ui.bat` 报错：
```
Web UI frontend not built and npm is not available.
```

**原因**：上游 `cmd_dashboard` 函数没有检查 `web_dist` 是否已预构建。

**修复**：在 `cmd_dashboard` 开头添加 web_dist 存在性检查（见步骤 4）。

### 问题 3：缺少新依赖

**现象**：启动时报 `ModuleNotFoundError`。

**原因**：上游源码引入了新的 Python 包，但 venv 中没有。

**修复**：
```powershell
# 方法 1: 使用 uv 安装到 venv（推荐，此便携包使用 uv 管理 Python）
.\tools\uv.exe pip install --python .\python_runtime\python.exe --target .\venv\Lib\site-packages <package>

# 方法 2: 如果有 requirements.txt
.\python_runtime\python.exe -m pip install -r hermes-agent\requirements.txt
```

### 问题 4：上游代码破坏 Windows 兼容性

**现象**：启动时报 `ModuleNotFoundError: No module named 'fcntl'` 或类似 Unix-only 模块错误。

**原因**：上游新增代码直接导入了 Unix 特有模块（如 `fcntl`、`termios`、`resource`），没有 Windows 回退保护。

**修复**：

1. **定位问题文件**：
   ```powershell
   cd hermes-agent
   grep -r "import fcntl" --include="*.py" .
   ```

2. **添加 try/except 保护**（遵循项目已有惯例）：
   ```python
   try:
       import fcntl
   except ImportError:
       fcntl = None  # type: ignore
   ```

3. **保存为 patch**，放入 `patches/` 目录：
   ```powershell
   cd hermes-agent
   git diff > ../patches/001-some-fix.patch
   ```

4. **更新脚本会自动应用 patches** —— `update-upstream.ps1` 在 `git pull` 后会自动执行 `git apply` 所有 `patches/*.patch`。

### 问题 5：子模块指针未记录

**现象**：更新后 `git status` 显示 `hermes-agent` 和 `hermes-webui` 有修改。

**原因**：子模块 `git pull` 后，主仓库的指针没有更新。

**修复**：
```powershell
git add hermes-agent hermes-webui
git commit -m "sync: bump upstream"
```

---

## 一键脚本模板

如果需要写一个完整的更新+打包脚本：

```powershell
# update-and-pack.ps1
param(
    [string]$Version = "",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$root = "D:\Hermes\Hermes-Agent-Portable"
Set-Location $root

Write-Host "=== Step 1: Sync upstream ===" -ForegroundColor Cyan
cd hermes-agent; git pull origin main; cd ..
cd hermes-webui; git pull origin main; cd ..

Write-Host "`n=== Step 2: Apply local patches ===" -ForegroundColor Cyan
Get-ChildItem -Path "patches" -Filter "*.patch" -ErrorAction SilentlyContinue | Sort-Object Name | ForEach-Object {
    $patchName = $_.Name
    Push-Location hermes-agent
    try {
        git apply --check "../patches/$patchName" 2>$null
        if ($LASTEXITCODE -eq 0) {
            git apply "../patches/$patchName"
            Write-Host "  Applied: $patchName" -ForegroundColor Green
        } else {
            Write-Host "  Already applied or skipped: $patchName" -ForegroundColor Gray
        }
    } finally {
        Pop-Location
    }
}

git add hermes-agent hermes-webui
git commit -m "sync: bump upstream before release"

Write-Host "`n=== Step 3: P0 smoke test ===" -ForegroundColor Cyan
$env:PYTHONPATH = "$PWD\hermes-agent;$PWD\venv\Lib\site-packages"
$env:PYTHONIOENCODING = "utf-8"
$result = python_runtime\python.exe scripts\p0-test.py
if ($LASTEXITCODE -eq 1) {
    Write-Error "P0 test failed, abort."
    exit 1
}

Write-Host "`n=== Step 4: Pre-pack check ===" -ForegroundColor Cyan
$check = python_runtime\python.exe scripts\pre-pack-check.py
if ($LASTEXITCODE -eq 1) {
    Write-Error "Check failed, abort."
    exit 1
}

Write-Host "`n=== Step 5: Build web_dist if needed ===" -ForegroundColor Cyan
if (-not (Test-Path hermes-agent\hermes_cli\web_dist\index.html)) {
    cd hermes-agent\web
    npm install
    npm run build
    cd ..\..
}

Write-Host "`n=== Step 6: Clean cache ===" -ForegroundColor Cyan
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force

Write-Host "`n=== Step 7: Pack ===" -ForegroundColor Cyan
if (-not $Version) {
    $Version = Read-Host "Enter version (e.g., 0.10.0)"
}
cd ..
# 排除 .git/ skills/ scripts/ —— 用户不需要这些维护者文件
7z a -t7z -mx=9 "-xr!.git" "-xr!skills" "-xr!scripts" "Hermes-Agent-Portable-v$Version.7z" "Hermes-Agent-Portable\"

Write-Host "`n=== Done ===" -ForegroundColor Green
```

---

## 质量检查清单

发布前必须确认：

- [ ] `pre-pack-check.py` 全部通过（0 失败）
- [ ] `p0-test.py` 全部通过（0 失败）
- [ ] `hermes ui.bat` 在新电脑能正常启动 Dashboard
- [ ] `start-hermes.bat` 运行的是最新源码版本
- [ ] `update-hermes.bat` 能正常同步上游并自动应用 patches
- [ ] 包体积合理（排除 .git 后 < 200 MB）
- [ ] Git tag 已创建并推送
- [ ] Release 说明已写（包含版本号和子模块 commit）

---

## 参考文件

| 文件/目录 | 作用 |
|-----------|------|
| `scripts/pre-pack-check.py` | 打包前自动化检查 |
| `scripts/pack.py` | 一键打包（7z/zip） |
| `scripts/pack-sfx.py` | 自解压 EXE 打包 |
| `update-upstream.ps1` | 同步上游子模块 + 自动应用 patches |
| `update-hermes.bat` | `update-upstream.ps1` 的 Windows 入口 |
| `patches/` | 本地补丁目录（`*.patch` 更新后自动应用） |
| `hermes-agent/hermes_cli/main.py` | Dashboard 启动逻辑 |
| `hermes-agent/web/package.json` | 前端依赖 |
| `.gitmodules` | 子模块声明 |
