# update-upstream.ps1
# Hermes-Agent-Portable 上游源码一键同步脚本
# 用法: .\update-upstream.ps1 [-AgentBranch main] [-WebUIBranch main] [-SkipTests]

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

# 检查 Git
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error @"
Git not found. Please install Git for Windows:
  https://git-scm.com/download/win

During install, choose:
  - 'Git from the command line and also from 3rd-party software'
  - 'Checkout as-is, commit as-is' (or 'Checkout Windows-style, commit Unix-style')
"@
    exit 1
}

# 如果根目录不是 git 仓库，给出提示
if (-not (Test-Path .git)) {
    Write-Warning @"
Root directory is NOT a Git repository yet.
Please run initialization first (see UPDATE_STRATEGY.md):
  1. git init
  2. Remove/Rename existing hermes-agent and hermes-webui folders
  3. git submodule add https://github.com/nousresearch/hermes-agent.git hermes-agent
  4. git submodule add https://github.com/nesquena/hermes-webui.git hermes-webui
  5. git commit -m "init submodules"
"@
    exit 1
}

$agentUpdated = $false
$webuiUpdated = $false

# --- 更新 hermes-agent ---
Write-Host "`n[1/5] Updating hermes-agent (branch: $AgentBranch) ..." -ForegroundColor Yellow
if (Test-Path hermes-agent\.git) {
    Push-Location hermes-agent
    try {
        git fetch origin $AgentBranch
        $before = git rev-parse HEAD
        git merge "origin/$AgentBranch" --no-edit 2>$null
        $after = git rev-parse HEAD
        if ($before -eq $after) {
            Write-Host "   hermes-agent: already up-to-date ($(git rev-parse --short HEAD))" -ForegroundColor Green
        } else {
            Write-Host "   hermes-agent: updated $(git rev-parse --short $before) -> $(git rev-parse --short $after)" -ForegroundColor Green
            $agentUpdated = $true
        }
    } catch {
        Write-Warning "   hermes-agent update failed: $_"
    } finally {
        Pop-Location
    }
} else {
    Write-Warning "   hermes-agent is not a git submodule. Skipped."
}

# --- 更新 hermes-webui ---
Write-Host "`n[2/5] Updating hermes-webui (branch: $WebUIBranch) ..." -ForegroundColor Yellow
if (Test-Path hermes-webui\.git) {
    Push-Location hermes-webui
    try {
        git fetch origin $WebUIBranch
        $before = git rev-parse HEAD
        git merge "origin/$WebUIBranch" --no-edit 2>$null
        $after = git rev-parse HEAD
        if ($before -eq $after) {
            Write-Host "   hermes-webui: already up-to-date ($(git rev-parse --short HEAD))" -ForegroundColor Green
        } else {
            Write-Host "   hermes-webui: updated $(git rev-parse --short $before) -> $(git rev-parse --short $after)" -ForegroundColor Green
            $webuiUpdated = $true
        }
    } catch {
        Write-Warning "   hermes-webui update failed: $_"
    } finally {
        Pop-Location
    }
} else {
    Write-Warning "   hermes-webui is not a git submodule. Skipped."
}

# --- 应用本地补丁 ---
Write-Host "`n[3/5] Applying local patches ..." -ForegroundColor Yellow
$patchesApplied = 0
$patchesFailed = 0
$patchesDir = Join-Path $root "patches"
if (Test-Path $patchesDir) {
    $patchFiles = Get-ChildItem -Path $patchesDir -Filter "*.patch" | Sort-Object Name
    foreach ($patch in $patchFiles) {
        $relPath = $patch.Name
        # 判断 patch 目标子模块（默认 hermes-agent）
        $targetSubdir = "hermes-agent"
        if ($relPath -match "^webui-" -or $relPath -match "-webui\.") {
            $targetSubdir = "hermes-webui"
        }
        $targetPath = Join-Path $root $targetSubdir
        if (-not (Test-Path $targetPath)) {
            Write-Warning "   $relPath -> target directory '$targetSubdir' not found, skip."
            $patchesFailed++
            continue
        }
        Push-Location $targetPath
        try {
            $result = git apply --check "../../patches/$relPath" 2>&1
            if ($LASTEXITCODE -eq 0) {
                git apply "../../patches/$relPath" 2>$null | Out-Null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "   $relPath -> $targetSubdir applied." -ForegroundColor Green
                    $patchesApplied++
                } else {
                    Write-Warning "   $relPath -> $targetSubdir apply failed (git apply returned error)."
                    $patchesFailed++
                }
            } else {
                Write-Host "   $relPath -> already applied or incompatible, skip." -ForegroundColor Gray
            }
        } finally {
            Pop-Location
        }
    }
    if ($patchesApplied -eq 0 -and $patchesFailed -eq 0) {
        Write-Host "   No patches to apply." -ForegroundColor Gray
    }
} else {
    Write-Host "   patches/ directory not found, skip." -ForegroundColor Gray
}

# --- 记录指针到主仓库 ---
if ($agentUpdated -or $webuiUpdated -or $patchesApplied -gt 0) {
    Write-Host "`n[4/5] Recording submodule pointers in root repo ..." -ForegroundColor Yellow
    if ($agentUpdated) { git add hermes-agent }
    if ($webuiUpdated) { git add hermes-webui }

    $msgLines = @("sync: bump upstream")
    if ($agentUpdated) { $msgLines += "- hermes-agent: $(git -C hermes-agent rev-parse --short HEAD)" }
    if ($webuiUpdated) { $msgLines += "- hermes-webui: $(git -C hermes-webui rev-parse --short HEAD)" }
    $msg = $msgLines -join "`n"

    git commit -m "$msg" | Out-Null
    Write-Host "   Committed submodule pointer update." -ForegroundColor Green
} else {
    Write-Host "`n[4/5] No upstream changes, skip commit." -ForegroundColor Gray
}

# --- 可选测试 ---
if (-not $SkipTests) {
    Write-Host "`n[5/5] Running quick tests ..." -ForegroundColor Yellow
    if (Test-Path test-hermes.bat) {
        & .\test-hermes.bat
    } else {
        Write-Host "   test-hermes.bat not found, skip." -ForegroundColor Gray
    }
} else {
    Write-Host "`n[5/5] Skipped tests (-SkipTests)." -ForegroundColor Gray
}

Write-Host "`n=== Sync Complete ===" -ForegroundColor Cyan
