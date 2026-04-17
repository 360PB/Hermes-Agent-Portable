# Hermes Agent v0.10.0 (v2026.4.16)

**Release Date:** 2026-04-17

---

## 📦 整合包更新

首次采用 **Git 子模块** 架构跟踪上游源码，实现一键同步更新。

| 组件 | 版本 | Commit |
|------|------|--------|
| Hermes Agent | v0.10.0 (v2026.4.16-103) | `6ea7386a` |
| Hermes WebUI | v0.50.75 | `f3f23abd` |

---

## ✨ 主要变更

### 架构改进
- **Git 子模块化** — `hermes-agent/` 和 `hermes-webui/` 改为 Git Submodule，分别跟踪上游仓库
- **一键同步脚本** — 新增 `update-hermes.bat` / `update-upstream.ps1`，双击即可 `git pull` 两个上游仓库
- **源码优先加载** — `PYTHONPATH` 调整为源码目录优先于 venv，始终运行最新代码

### 清理优化
- 删除旧源码备份目录（~42 MB）
- 清理 `__pycache__` / `.pyc` 缓存文件（~27 MB）
- 清理构建产物 `build/` / `*.egg-info`
- **释放空间：~103 MB**

---

## 🚀 快速开始

```bash
git clone --recursive https://github.com/360PB/Hermes-Agent-Portable.git
# 或
git clone https://github.com/360PB/Hermes-Agent-Portable.git
cd Hermes-Agent-Portable
git submodule update --init --recursive
```

然后双击 `start-hermes.bat` 或 `start-webui.bat` 即可启动。

---

## 🔄 同步上游

双击 `update-hermes.bat` 自动拉取最新源码：
- `nousresearch/hermes-agent`
- `nesquena/hermes-webui`

---

## 📁 仓库结构

```
Hermes-Agent-Portable/
├── hermes-agent/       ← submodule (nousresearch/hermes-agent)
├── hermes-webui/       ← submodule (nesquena/hermes-webui)
├── python_runtime/     ← 便携 Python 3.11
├── venv/               ← 依赖包
├── start-hermes.bat
├── start-webui.bat
├── update-hermes.bat   ← 同步入口
└── README.md
```

---

## 🔗 上游仓库

- Hermes Agent: https://github.com/nousresearch/hermes-agent
- Hermes WebUI: https://github.com/nesquena/hermes-webui
