# Hermes-Agent-Portable 同步更新方案

> 目标：建立可复现、自动化的上游源码同步机制，同时保护整合包的自定义文件不被覆盖。

---

## 一、现状分析

| 问题 | 影响 |
|------|------|
| `hermes-agent/` 和 `hermes-webui/` 不是 Git 仓库 | 无法直接 `git pull` 同步上游更新 |
| 上游仓库提交频繁（几乎每日更新） | 手动下载覆盖效率低、易出错 |
| 整合包根目录有自定义文件（`.bat`、README、python_runtime、venv 等） | 直接覆盖会丢失自定义配置 |
| Windows 便携包定位 | 需要尽量降低对外部工具的依赖 |

---

## 二、推荐方案：Git 子模块 + 自定义层隔离

采用 **Git Submodule** 跟踪上游仓库，整合包自定义内容放在仓库根目录，与上游源码物理隔离。

```
Hermes-Agent-Portable/          ← Git 主仓库（你维护）
├── .git/                       ← 主仓库 Git
├── .gitmodules                 ← 子模块声明
├── hermes-agent/               ← Git Submodule → nousresearch/hermes-agent
├── hermes-webui/               ← Git Submodule → nesquena/hermes-webui
├── python_runtime/             ← 整合包自定义（不受子模块影响）
├── venv/                       ← 整合包自定义
├── tools/                      ← 整合包自定义
├── start-hermes.bat            ← 整合包自定义
├── start-webui.bat             ← 整合包自定义
├── update-hermes.bat           ← 整合包自定义（更新脚本入口）
├── test-hermes.bat             ← 整合包自定义
├── README.md                   ← 整合包自定义
└── UPDATE_STRATEGY.md          ← 本文档
```

### 方案优势

| 优势 | 说明 |
|------|------|
| **物理隔离** | 上游代码在子目录，自定义文件在根目录，互不干扰 |
| **版本可控** | 可精确锁定子模块到特定 commit，也可随时升级 |
| **可追溯** | 每次更新都有 Git 记录，出问题时可回滚 |
| **自动化** | 一条命令即可完成两个子仓库的 `git pull` + 冲突检查 |
| **保留便携性** | Windows 下只需安装 Git for Windows 即可操作 |

---

## 三、实施步骤

### 步骤 1：初始化主仓库（在整合包根目录执行）

```powershell
# 进入整合包根目录
cd Hermes-Agent-Portable

# 初始化主仓库（根目录变成 Git 仓库）
git init

# 添加 .gitignore，排除不需要跟踪的大文件/环境目录
git add .gitignore
git commit -m "init: portable bundle root repo"
```

### 步骤 2：将现有源码目录转为子模块

> ⚠️ **重要**：操作前务必备份当前目录，以防数据丢失。

```powershell
# 1. 删除现有的非 Git 源码目录（或重命名备份）
Move-Item hermes-agent hermes-agent.backup
Move-Item hermes-webui hermes-webui.backup

# 2. 添加 hermes-agent 子模块
git submodule add https://github.com/nousresearch/hermes-agent.git hermes-agent

# 3. 添加 hermes-webui 子模块
git submodule add https://github.com/nesquena/hermes-webui.git hermes-webui

# 4. 提交子模块配置
git add .gitmodules
git commit -m "feat: add upstream submodules for hermes-agent and hermes-webui"
```

### 步骤 3：验证子模块状态

```powershell
git submodule status
# 应输出类似：
#  fc04f830622dab7feff5b17bb3e36cf0cc7fb76e hermes-agent (latest)
#  f3f23abd4e4bb886fbf4bc941e76f8adc9845dee hermes-webui (v0.50.75)
```

### 步骤 4：恢复/整合自定义文件

将备份目录中的**自定义文件**（如你对源码做的本地化修改）合并到新拉取的子模块中。如果此前未修改过源码，则跳过此步。

```powershell
# 如果之前备份了，确认无误后可删除备份
Remove-Item -Recurse -Force hermes-agent.backup
Remove-Item -Recurse -Force hermes-webui.backup
```

---

## 四、日常使用：同步更新脚本

### 4.1 一键更新脚本 `update-upstream.ps1`

在整合包根目录创建以下 PowerShell 脚本：

```powershell
# update-upstream.ps1
# 用法: .\update-upstream.ps1 [-Branch main] [-SkipTests]
param(
    [string]$AgentBranch = "main",
    [string]$WebUIBranch = "main",
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $root

Write-Host "=== Hermes-Agent-Portable Upstream Sync ===" -ForegroundColor Cyan
Write-Host "Root: $root" -ForegroundColor Gray

# 检查 Git 是否安装
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "Git not found. Please install Git for Windows: https://git-scm.com/download/win"
    exit 1
}

# 更新 hermes-agent
Write-Host "`n[1/4] Updating hermes-agent (branch: $AgentBranch) ..." -ForegroundColor Yellow
Push-Location hermes-agent
try {
    git fetch origin
    $before = git rev-parse HEAD
    git pull origin $AgentBranch
    $after = git rev-parse HEAD
    if ($before -eq $after) {
        Write-Host "   hermes-agent: already up-to-date ($before)" -ForegroundColor Green
    } else {
        Write-Host "   hermes-agent: updated $before -> $after" -ForegroundColor Green
        $agentUpdated = $true
    }
} finally {
    Pop-Location
}

# 更新 hermes-webui
Write-Host "`n[2/4] Updating hermes-webui (branch: $WebUIBranch) ..." -ForegroundColor Yellow
Push-Location hermes-webui
try {
    git fetch origin
    $before = git rev-parse HEAD
    git pull origin $WebUIBranch
    $after = git rev-parse HEAD
    if ($before -eq $after) {
        Write-Host "   hermes-webui: already up-to-date ($before)" -ForegroundColor Green
    } else {
        Write-Host "   hermes-webui: updated $before -> $after" -ForegroundColor Green
        $webuiUpdated = $true
    }
} finally {
    Pop-Location
}

# 如果源码有更新，记录到主仓库
if ($agentUpdated -or $webuiUpdated) {
    Write-Host "`n[3/4] Recording submodule pointers in root repo ..." -ForegroundColor Yellow
    git add hermes-agent hermes-webui
    $msg = "sync: bump upstream"
    if ($agentUpdated) { $msg += "`n- hermes-agent: $(git -C hermes-agent rev-parse --short HEAD)" }
    if ($webuiUpdated) { $msg += "`n- hermes-webui: $(git -C hermes-webui rev-parse --short HEAD)" }
    git commit -m $msg
    Write-Host "   Committed submodule pointer update." -ForegroundColor Green
} else {
    Write-Host "`n[3/4] No upstream changes, skip commit." -ForegroundColor Gray
}

# 可选：运行测试
if (-not $SkipTests) {
    Write-Host "`n[4/4] Running quick tests ..." -ForegroundColor Yellow
    if (Test-Path test-hermes.bat) {
        & .\test-hermes.bat
    } else {
        Write-Host "   test-hermes.bat not found, skip." -ForegroundColor Gray
    }
} else {
    Write-Host "`n[4/4] Skipped tests (-SkipTests)." -ForegroundColor Gray
}

Write-Host "`n=== Sync Complete ===" -ForegroundColor Cyan
```

### 4.2 对应 `.bat` 入口（双击即用）

将现有的 `update-hermes.bat` 替换为：

```batch
@echo off
chcp 65001 >nul
echo ==========================================
echo   Hermes Agent Portable - Update Upstream
echo ==========================================
powershell -ExecutionPolicy Bypass -File "%~dp0update-upstream.ps1" %*
echo.
pause
```

### 4.3 `.gitignore` 建议

```gitignore
# 环境/大目录（不应进入 Git）
venv/
python_runtime/
tools/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/

# 用户本地配置
.env
*.local

# 备份目录（更新过程中生成）
*.backup/
```

---

## 五、高级用法

### 5.1 锁定到特定版本（稳定发布）

如果不想每天跟进最新 commit，可锁定到上游的 Release Tag：

```powershell
# hermes-agent 锁定到某个 commit
cd hermes-agent
git checkout fc04f830622dab7feff5b17bb3e36cf0cc7fb76e

# hermes-webui 锁定到某个 tag
cd ../hermes-webui
git checkout v0.50.75

# 然后回到根目录记录指针
cd ..
git add hermes-agent hermes-webui
git commit -m "pin: lock upstream to stable versions"
```

### 5.2 使用国内镜像加速（可选）

如果 GitHub 访问慢，可在添加子模块时使用镜像地址：

```powershell
# 使用 ghproxy 等镜像（示例）
git submodule add https://ghproxy.com/https://github.com/nousresearch/hermes-agent.git hermes-agent
git submodule add https://ghproxy.com/https://github.com/nesquena/hermes-webui.git hermes-webui
```

### 5.3 仅更新单个子模块

```powershell
# 只更新 agent
git submodule update --remote hermes-agent

# 只更新 webui
git submodule update --remote hermes-webui
```

---

## 六、常见问题

### Q1: 子模块目录为空？

首次 clone 带有子模块的仓库时，需要初始化子模块：

```powershell
git submodule update --init --recursive
```

### Q2: 上游有破坏性变更，更新后整合包启动失败？

由于主仓库记录了子模块的精确 commit，可随时回滚：

```powershell
git log --oneline          # 找到更新前的 commit
git revert <update-commit> # 回滚子模块指针
git submodule update       # 将子模块代码恢复到指针位置
```

### Q3: 我对源码做了本地修改（如汉化、配置调整），更新会被覆盖吗？

如果你有未提交的本地修改，`git pull` 会报错阻止覆盖。建议：

1. **优先方式**：将修改提取为 Patch 文件，放在整合包根目录的 `patches/` 中，更新后自动应用：

```powershell
# update-upstream.ps1 中，在 pull 之后添加：
Get-ChildItem patches/*.patch | ForEach-Object {
    git -C hermes-agent apply --reject ../$_
}
```

2. **备用方式**：在子模块内用 `git stash` 暂存 -> `git pull` -> `git stash pop` 恢复（可能有冲突）。

---

## 七、检查清单（首次迁移）

- [ ] 备份整个 `Hermes-Agent-Portable/` 目录
- [ ] 在根目录执行 `git init`
- [ ] 重命名/删除旧的 `hermes-agent` 和 `hermes-webui`
- [ ] 执行 `git submodule add` 添加两个子模块
- [ ] 创建/更新 `.gitignore`
- [ ] 创建 `update-upstream.ps1` 和 `update-hermes.bat`
- [ ] 提交主仓库初始配置
- [ ] 测试运行 `start-hermes.bat` 和 `start-webui.bat`
- [ ] 测试运行 `update-hermes.bat` 进行一次同步验证

---

## 八、方案对比

| 方案 | 复杂度 | 上游同步 | 自定义保护 | 版本追溯 | 推荐度 |
|------|--------|----------|------------|----------|--------|
| **A. Git 子模块**（本文推荐） | 中 | 一条命令 | 物理隔离 | 完整 | ⭐⭐⭐ |
| B. 手动下载 ZIP 覆盖 | 低 | 繁琐易错 | 需手动备份 | 无 | ⭐ |
| C. 直接在上游目录 `git init` | 低 | 可 `git pull` | 无隔离，易被覆盖 | 仅上游 | ⭐⭐ |
| D. Fork 后合并上游 | 高 | 需处理合并冲突 | 完整 | 完整 | ⭐⭐（适合重度定制） |

---

> 维护者备注：迁移完成后，定期运行 `update-hermes.bat` 即可保持与上游同步。
