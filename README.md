# Hermes-Agent-Portable

> **目标读者**：后续需要维护、迁移或排查该整合包的 AI Agent / 开发者。  
> **适用场景**：Windows 11/10 x64，目标是在**不安装 uv / Python / 任何系统级依赖**的新电脑上直接运行 Hermes Agent + WebUI。

---

## 1. 这是什么

这是一个 **Windows 便携整合包**，将以下内容打包在一起：

- `hermes-agent` 源码
- `hermes-webui` 源码
- 独立的 Python 3.11 运行时 (`python_runtime/`)
- 完整依赖环境 (`venv/`)
- uv 包管理器 (`tools/uv.exe`)

通过特定的启动方式（`PYTHONPATH` + 自带 Python 解释器），绕过了 uv 虚拟环境 trampoline 的绝对路径限制，实现**解压即用**。

---

## 2. 物理结构

```
Hermes-Agent-Portable/
├── hermes-agent/            # Hermes Agent 纯源码
├── hermes-webui/            # Hermes WebUI 源码（保留独立 .git）
├── python_runtime/          # 独立 Python 3.11 解释器
│   ├── python.exe
│   ├── python311.dll
│   └── Lib/
├── venv/
│   └── Lib/site-packages/   # 完整的 hermes-agent + webui 依赖（普通安装，非 editable）
├── tools/
│   └── uv.exe               # uv 包管理器
├── start-hermes.bat         # 启动 Hermes CLI Chat
├── start-webui.bat          # 启动 Web UI（自动打开浏览器）
├── test-hermes.bat          # 快速测试：hermes chat -q "hello"
├── update-hermes.bat        # 更新入口
└── README.md
```

### 2.1 为什么没有 `venv\Scripts\activate`？

uv 在 Windows 上生成的 `venv\Scripts\*.exe` 是 **trampoline 二进制文件**，内部硬编码了原电脑 Python 解释器的绝对路径。直接复制到新电脑后会崩溃。

**解决方案**：
- 自带 `python_runtime\python.exe` 作为真实解释器。
- 启动脚本通过 `PYTHONPATH=%CD%\venv\Lib\site-packages` 加载所有依赖。
- `hermes-agent` 和 `hermes-webui` 作为平等的源码目录，通过环境变量被指向。

---

## 3. 启动脚本的核心逻辑

### `start-hermes.bat`
```bat
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0
set PYTHONPATH=%CD%\venv\Lib\site-packages
"%CD%\python_runtime\python.exe" -m hermes_cli.main chat
```

### `start-webui.bat`
```bat
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0

set PYTHONPATH=%CD%\venv\Lib\site-packages
set HERMES_WEBUI_AGENT_DIR=%CD%\hermes-agent
set HERMES_WEBUI_PYTHON=%CD%\python_runtime\python.exe

echo Starting Hermes WebUI...
start "Hermes WebUI" "%CD%\python_runtime\python.exe" "%CD%\hermes-webui\server.py"

echo Waiting for server...
ping 127.0.0.1 -n 4 >nul

echo Opening browser...
start http://127.0.0.1:8787
```

### `test-hermes.bat`
```bat
@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
cd /d %~dp0
set PYTHONPATH=%CD%\venv\Lib\site-packages
"%CD%\python_runtime\python.exe" -m hermes_cli.main chat -q "hello"
pause
```

### 关键环境变量
| 变量 | 作用 |
|:---|:---|
| `PYTHONIOENCODING=utf-8` | 避免 Windows 默认 GBK 编码导致日志输出崩溃。 |
| `PYTHONPATH=%CD%\venv\Lib\site-packages` | 让内置 python.exe 能导入所有第三方依赖。 |
| `HERMES_WEBUI_AGENT_DIR=%CD%\hermes-agent` | 让 WebUI 自动发现 agent 目录。 |
| `HERMES_WEBUI_PYTHON` | 指定 WebUI 使用哪个 Python 解释器。 |
| `cd /d %~dp0` | 确保无论从哪里双击启动，工作目录都切换到脚本所在目录。 |

---

## 4. 更新脚本的核心逻辑

### `update-hermes.bat`

执行以下步骤：

1. **更新 hermes-agent 源码与依赖**：进入 `hermes-agent/` 执行 `hermes update`（内部执行 `git pull` + `uv pip install`）
2. **消除 editable 绝对路径依赖**：`tools\uv.exe pip install . --force-reinstall --no-deps`
3. **清理 `__pycache__`**：防止跨目录移动后缓存失效
4. **同步更新 hermes-webui**：进入 `hermes-webui/` 执行 `git pull`

> **注意**：`hermes update` 默认使用 editable 安装，会生成硬编码绝对路径的 `.pth` 文件。第 2 步将其转为普通安装，恢复整合包的便携性。

---

## 5. 给 AI 的操作手册

### 场景 A：用户说"整合包在新电脑上打不开"

**排查清单**：
1. **路径检查**：确认解压路径不含中文或空格（某些 C 扩展 DLL 对中文路径敏感）。
2. **`.env` 检查**：确认 `%USERPROFILE%\.hermes\.env` 已存在且包含有效 `KIMI_API_KEY`。
3. **运行库检查**：若提示缺少 `VCRUNTIME140.dll`，需安装 [VC++ Redistributable x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)。
4. **不要运行 `venv\Scripts\activate`**：跨机器复制后 trampoline 已失效，这是已知陷阱。

### 场景 B：用户要求"重新打包/更新整合包"

**用户端最简方案**：直接双击 `update-hermes.bat`。

**母环境重新打包流程**（若需要从零重建）：
1. 确保有正常 uv 环境，执行 `uv pip install -e ".[all,dev]"`
2. `uv pip install . --force-reinstall --no-deps`（消除 editable）
3. 复制 Python 运行时到 `python_runtime/`
4. 复制 uv 到 `tools/uv.exe`
5. 将 hermes-agent 源码放入 `hermes-agent/`，webui 源码放入 `hermes-webui/`
6. 重新生成 4 个启动脚本（内容参考第 3 节）
7. 清理 `__pycache__`、`.git`、`build`、`*.egg-info`

### 场景 C：用户想把整合包放到 U 盘 / 移动硬盘

**可直接复制**。只要保持 `hermes-agent/`、`hermes-webui/`、`python_runtime/`、`venv/`、`tools/` 的相对路径不变（即一起移动），启动脚本使用 `%~dp0`，无需修改。

---

## 6. 已知问题与边界

| 限制 | 说明 |
|:---|:---|
| **操作系统锁定** | 仅 Windows 11/10 x64。`python_runtime` 和大量 `.pyd`/`.dll` 是 Windows 原生二进制。 |
| **GitHub 大文件警告** | `tools/uv.exe`（约 65 MB）超过 GitHub 推荐的 50 MB 软限制。当前未使用 Git LFS，但仍在 100 MB 硬限制之内，可正常推送/拉取。如需优化，建议将 `tools/uv.exe` 和 `python_runtime/DLLs/*.dll` 迁移到 Git LFS。 |
| **不可跨用户名** | 已尽量消除绝对路径，但某些编译扩展（如 `pywin32`）的注册表操作仍可能与原系统有关。 |
| **体积** | 约 450 MB（删除 `.git` 后）。其中 `venv/` 约占 447 MB，`python_runtime/` 约 60 MB。 |
| **WebUI 的 `fcntl` 问题** | 已修复。原始 `hermes-agent/tools/memory_tool.py` 直接 `import fcntl`，Windows 上不存在该 Unix-only 模块，启动时会打印警告。当前整合包已将其包裹在 `try/except` 中，Windows 下静默跳过文件锁逻辑，不影响核心功能。 |

---

## 7. 快速验证命令

在新电脑上解压后，打开 CMD 执行：

```cmd
cd /d D:\Hermes\Hermes-Agent-Portable
set PYTHONPATH=%CD%\venv\Lib\site-packages
"%CD%\python_runtime\python.exe" -m hermes_cli.main --version
```

预期应输出版本信息且不报错。

验证 WebUI：
```cmd
cd /d D:\Hermes\Hermes-Agent-Portable
start-webui.bat
```

然后浏览器访问 `http://127.0.0.1:8787/health`，应返回 JSON `{"status": "ok"}`。

---

## 8. 总结

- **核心机制**：自带 Python + 自带 uv + `PYTHONPATH` 加载依赖 + 绕过 uv trampoline。
- **唯一正确入口**：`start-hermes.bat` 启动 CLI，`start-webui.bat` 启动 WebUI。
- **唯一正确更新入口**：`update-hermes.bat`，它会自动修复 `hermes update` 产生的 editable 绝对路径副作用。
- **不要建议用户运行 `venv\Scripts\activate`**。
