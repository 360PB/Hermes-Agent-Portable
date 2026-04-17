# Hermes-Agent-Portable

> **Windows 便携整合包** —— 解压即用，无需安装 Python / uv / 任何系统级依赖。
>
> 内置 [Hermes Agent](https://github.com/nousresearch/hermes-agent) CLI + [Hermes WebUI](https://github.com/nesquena/hermes-webui)，支持一键同步上游最新源码。
>
> ##### 整合包下载
>
> 链接：https://pan.quark.cn/s/34d70bcb9b01

---

## ✨ 特性

- **零依赖运行** — 自带 Python 3.11 运行时 + 完整依赖环境
- **源码优先加载** — 直接运行最新源码，而非 venv 中固化的旧包
- **一键同步上游** — `update-hermes.bat` 自动 `git pull` 两个上游仓库
- **版本可追溯** — 使用 Git 子模块精确锁定源码版本，随时回滚
- **U 盘可移植** — 相对路径设计，复制到任意位置双击即用

---

## 📦 包含内容

| 目录 | 说明 |
|------|------|
| `hermes-agent/` | Hermes Agent 源码（Git 子模块 → `nousresearch/hermes-agent`） |
| `hermes-webui/` | Hermes WebUI 源码（Git 子模块 → `nesquena/hermes-webui`） |
| `python_runtime/` | 独立 Python 3.11 解释器（Windows x64） |
| `venv/` | 完整的第三方依赖包（`site-packages`） |
| `tools/` | uv 包管理器等工具 |

---

## 🚀 快速开始

### 1. 解压到任意目录

建议路径不含中文或空格：
```
D:\Hermes\Hermes-Agent-Portable\
```

### 2. 配置 API Key

在 `%USERPROFILE%\.hermes\.env` 中写入：
```env
KIMI_API_KEY=your-api-key-here
# 或其他你使用的提供商 key
```

### 3. 启动

| 功能 | 操作 |
|------|------|
| 启动 CLI 聊天 | 双击 `start-hermes.bat` |
| 启动 Web UI | 双击 `start-webui.bat`（自动打开浏览器） |
| 快速测试 | 双击 `test-hermes.bat` |
| 打开仪表盘 | 双击 `hermes ui.bat` |

WebUI 默认地址：`http://127.0.0.1:8787`

---

## 🔄 同步上游更新

### 自动更新（推荐）

双击 `update-hermes.bat`，脚本会自动：
1. `git pull` `hermes-agent` 源码（`nousresearch/hermes-agent`）
2. `git pull` `hermes-webui` 源码（`nesquena/hermes-webui`）
3. 记录新的子模块指针到主仓库
4. 可选运行测试验证

### 手动更新单个子模块

```powershell
# 只更新 Agent
cd hermes-agent
git pull origin main

# 只更新 WebUI
cd hermes-webui
git pull origin main

# 回到根目录记录指针
cd ..
git add hermes-agent hermes-webui
git commit -m "sync: bump upstream"
```

### 锁定到稳定版本

如果不想跟进最新 commit，可锁定到 Release Tag：

```powershell
cd hermes-agent
git checkout v0.10.0        # 示例 tag

cd ../hermes-webui
git checkout v0.50.75       # 示例 tag

cd ..
git add hermes-agent hermes-webui
git commit -m "pin: lock to stable versions"
```

---

## ⚙️ 启动原理

### 为什么不需要 `venv\Scripts\activate`？

uv 在 Windows 上生成的 `venv\Scripts\*.exe` 是 **trampoline 二进制文件**，内部硬编码了原电脑 Python 解释器的绝对路径。直接复制到新电脑后会崩溃。

**解决方案**：
- 自带 `python_runtime\python.exe` 作为真实解释器
- `PYTHONPATH` 同时指向源码目录 + venv 依赖目录：
  ```batch
  set PYTHONPATH=%CD%\hermes-agent;%CD%\venv\Lib\site-packages
  ```
- **源码优先** — 确保运行的是最新拉取的上游代码，而非 venv 中固化的旧版本

---

## 🛠️ 开发维护

### 目录结构

```
Hermes-Agent-Portable/
├── hermes-agent/            ← Git Submodule (上游源码)
├── hermes-webui/            ← Git Submodule (上游源码)
├── python_runtime/          ← 便携 Python 运行时
├── venv/                    ← 第三方依赖
├── tools/                   ← 工具
├── start-hermes.bat         ← 启动 CLI
├── start-webui.bat          ← 启动 WebUI
├── update-hermes.bat        ← 同步上游入口
├── update-upstream.ps1      ← 同步脚本 (PowerShell)
├── test-hermes.bat          ← 快速测试
├── hermes ui.bat            ← 仪表盘
├── .gitignore
├── .gitmodules
└── README.md
```

### 首次 clone 后初始化子模块

```bash
git clone https://github.com/360PB/Hermes-Agent-Portable.git
cd Hermes-Agent-Portable
git submodule update --init --recursive
```

### 新增/更新依赖

如果上游源码引入了新的 Python 依赖：

```powershell
.\python_runtime\python.exe -m pip install -r hermes-agent\requirements.txt
```

---

## ❓ 常见问题

### Q1: 新电脑上启动报错，提示找不到模块？

**排查清单**：
1. 确认解压路径**不含中文或空格**
2. 确认 `%USERPROFILE%\.hermes\.env` 已存在且包含有效 API Key
3. 若提示缺少 `VCRUNTIME140.dll`，安装 [VC++ Redistributable x64](https://aka.ms/vs/17/release/vc_redist.x64.exe)

### Q2: 运行的是旧版本？

确认 `PYTHONPATH` 中 `hermes-agent` 在 venv 之前。如果手动改过启动脚本，确保：
```batch
set PYTHONPATH=%CD%\hermes-agent;%CD%\venv\Lib\site-packages
```

### Q3: 子模块更新失败 / 冲突？

如果你修改了子模块内的文件，`git pull` 会阻止覆盖。建议：
```bash
cd hermes-agent
git stash        # 暂存本地修改
git pull origin main
git stash pop    # 恢复（可能有冲突需手动解决）
```

### Q4: 整合包能放到 U 盘吗？

**可以**。只要保持所有目录的相对位置不变，启动脚本使用 `%~dp0` 自动定位，无需修改。

---

## 📋 版本信息

| 组件 | 当前版本 | 上游仓库 |
|------|----------|----------|
| Hermes Agent | `v2026.4.16-92` | [nousresearch/hermes-agent](https://github.com/nousresearch/hermes-agent) |
| Hermes WebUI | `v0.50.75` | [nesquena/hermes-webui](https://github.com/nesquena/hermes-webui) |

> 查看具体 commit：`git submodule status`

---

## 📜 协议

- `hermes-agent/` 遵循其上游 [LICENSE](https://github.com/nousresearch/hermes-agent/blob/main/LICENSE)
- `hermes-webui/` 遵循其上游 [LICENSE](https://github.com/nesquena/hermes-webui/blob/main/LICENSE)
- 整合包脚本与配置属于公共维护，欢迎 Fork 和改进

---

> **维护提示**：整合包使用 Git 子模块跟踪上游。每次 `update-hermes.bat` 成功执行后，建议 `git push` 将新的子模块指针推送到远程，方便多设备同步。
