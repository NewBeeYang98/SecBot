# SecBot

<div align="center">

**AI驱动的网络安全工具箱 — CTF解题 · 内网扫描 · 渗透测试 · 离线支持 · Web界面**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux%20%7C%20WSL-orange.svg)](README.md)
[![Web UI](https://img.shields.io/badge/Web%20UI-Streamlit-ff4b4b.svg)]()

*支持互联网/内网隔离/U盘模式 自动切换，开箱即用*

</div>

---

## 快速开始

### Linux / WSL / macOS

```bash
cd SecBot
bash SecBot启动器.sh
```

### Windows

```
双击运行 SecBot启动器.bat
```

启动器会自动检测 Python 版本、安装缺失依赖、探测网络环境，**无需手动配置**。

> 如果遇到 Ubuntu 24.04 "externally managed environment" 报错，启动器会自动处理，无需手动解决。

---

## 功能概览

### Web UI（推荐）

浏览器打开 **http://localhost:8501**，提供图形化操作界面：

| 模块 | 说明 |
|------|------|
| 🔍 端口扫描 | nmap / 纯socket两种模式，实时进度 |
| 📂 目录扫描 | 多线程目录爆破，实时进度条 |
| 📋 Swagger分析 | 自动探测API文档，标记未认证接口 |
| 🔑 弱口令爆破 | HTTP表单/Basic Auth，内置弱口令字典 |
| 🕷️ Web爬虫 | 递归爬取 + 敏感信息泄露检测 |
| 🤖 AI解题 | 对接本地Ollama/OpenAI/Claude |
| 🚀 综合扫描 | 一键端口→目录→Swagger→弱口令 |

### CLI 终端菜单

```bash
python main.py
```

```
╔══════════════════════════════════════════════════╗
║           SecBot - 智能网络安全工具箱             ║
║  网络: 🌐 互联网 | AI: OpenAI / Claude / Ollama ║
╚══════════════════════════════════════════════════╝

  [1] 内网扫描      — nmap 集成，AI 辅助分析
  [2] AI自动渗透    — 扫描→AI规划→执行→迭代
  [3] CTF解题       — Web/Reverse/Crypto/Pwn/Misc
  [4] 隐写分析      — 图片/文件/十六进制隐写检测
  [5] SQL注入       — 自动探测 + sqlmap 调用
  [6] 暴力破解      — HTTP登录/目录扫描
  [7] 报告生成      — Markdown格式报告

  [D] 环境检查      — 一键检测/修复缺失依赖
  [S] 切换模式      — Auto / SemiAuto / Manual / UDisk
  [P] 切换AI        — OpenAI / Claude / Ollama
```

---

## 网络环境与部署模式

SecBot 自动检测当前网络环境，切换到对应模式：

| 场景 | 说明 | 如何启用 |
|------|------|---------|
| 🌐 **互联网模式** | 在线安装依赖，AI 用云端模型 | 有网络时自动启用 |
| 🔒 **内网隔离模式** | 优先用离线包，AI 用本地 Ollama | 无网络时自动切换 |
| 💾 **U盘模式** | 内网扫描→导出JSON→拿到外网分析→带任务回来执行 | 内网隔离+需要AI分析时 |
| 🛠️ **纯手动模式** | 纯工具链，AI 不可用 | 完全隔离环境 |

### 内网/离线部署（无需互联网）

```bash
# 方式1：用启动器（推荐，自动处理一切）
bash SecBot启动器.sh

# 方式2：手动从离线包安装（需要 offline/pip/*.whl）
pip install offline/pip/*.whl --no-deps --break-system-packages

# 方式3：完整离线安装向导
python install.py
```

**如何获取离线包（3种方式）：**

1. **有网络时下载**（推荐）：
   ```bash
   # 在有网络的机器上运行
   python download_offline.py
   # 自动下载所有离线包到 offline/pip/
   ```

2. **U盘拷贝**：
   ```bash
   # 在有网络的机器下载后，拷贝整个 SecBot 文件夹到 U盘
   # 到内网机器后直接运行
   bash SecBot启动器.sh
   ```

3. **网内文件服务器**：
   ```bash
   # 将 offline/pip/ 放到内网文件服务器
   # 内网机器从服务器同步后运行
   rsync -avp user@内网服务器:/path/to/offline/pip/ ./offline/pip/
   ```

离线包包含：streamlit / requests / beautifulsoup4 / lxml / colorama / pycryptodome / pygments 等（约 310MB）。

---

## AI 配置

编辑 `config.py`，或运行 `install.py` 时自动引导配置：

```python
MODEL_PROVIDER = "openai"          # openai / anthropic / ollama

# OpenAI
OPENAI_API_KEY="sk-..."
OPENAI_MODEL = "gpt-4o"

# Anthropic Claude
ANTHROPIC_API_KEY="sk-ant-..."
ANTHROPIC_MODEL = "claude-sonnet-4-20250514"

# Ollama 本地模型（推荐内网使用）
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen2.5-coder:7b"
```

---

## 项目架构

```
SecBot/
├── main.py                     # CLI 入口菜单
├── web_app.py                  # Web UI 入口（Streamlit）
├── config.py                   # AI + 工具配置
│
├── core/                       # 核心引擎
│   ├── agent.py               # AI 大脑（规划→执行→迭代）
│   ├── task_queue.py          # 持久化任务队列
│   ├── executor.py            # 任务执行器
│   ├── network_detector.py    # 网络环境检测
│   └── check_dependencies.py  # 依赖检查器
│
├── modules/                    # 功能模块
│   ├── ollama_client.py      # 统一模型客户端
│   ├── ctf_solver.py         # CTF 解题框架
│   ├── scanner.py            # nmap 扫描集成
│   ├── stego.py              # 隐写分析
│   ├── sqli.py               # SQL 注入
│   ├── brute.py              # 暴力破解
│   └── report.py             # 报告生成
│
├── scanner_iso/               # 零依赖扫描器
│   └── isolated_scanner.py   # 纯Python标准库，无需nmap
│
├── offline/                    # 离线依赖包
│   ├── pip/                  # Python wheel 包
│   ├── tools/                # 安全工具（sqlmap等）
│   └── scripts/              # 离线安装脚本
│
├── SecBot启动器.sh             # Linux/WSL 一键启动
├── SecBot启动器.bat            # Windows 一键启动
├── install.py                 # 在线安装向导
└── README.md
```

---

## 适用场景

| 场景 | 推荐配置 | 说明 |
|------|----------|------|
| 互联网机器 CTF 解题 | OpenAI / Claude | 全程 AI 参与，效果最好 |
| 内网渗透测试 | Ollama 本地模型 | 不需要外网连接 |
| 内网隔离（无网络） | U盘模式 | 先扫描导出，拿到外网分析 |
| 完全隔离（无网无 Ollama）| Manual 模式 | 纯工具链，AI 不可用 |

---

## 支持的工具

### 系统工具
| 工具 | 用途 | 安装 |
|------|------|------|
| nmap | 端口扫描 | `apt install nmap` |
| sqlmap | SQL注入 | 已在 offline/tools/ |
| steghide | 隐写分析 | `apt install steghide` |
| binwalk | 固件分析 | `pip install binwalk` |

### Python 包（已在 offline/pip/）
| 包 | 用途 |
|---|---|
| streamlit | Web 界面 |
| requests | HTTP 请求 |
| beautifulsoup4 | HTML 解析 |
| lxml | XML/HTML 解析 |
| pycryptodome | 密码学（AES/RSA） |
| colorama | 终端着色 |
| pygments | 代码高亮 |

---

## 常见问题

**Q: 报 `externally managed environment`（Ubuntu 24.04）？**
```bash
# 启动器已自动处理，无需手动操作
bash SecBot启动器.sh
```

**Q: 报 `ModuleNotFoundError`？**
```bash
# 方式1：启动器自动处理
bash SecBot启动器.sh

# 方式2：手动从离线包安装
pip install offline/pip/*.whl --no-deps --break-system-packages
```

**Q: 内网隔离模式 AI 不可用？**
```bash
# 在有网的机器上准备 Ollama
ollama serve
ollama pull qwen2.5-coder:7b

# 修改 config.py
MODEL_PROVIDER = "ollama"
OLLAMA_BASE_URL = "http://你的Ollama地址:11434"
```

**Q: nmap 扫描权限不足？**
```bash
# Linux 需要 root 或 CAP_NET_RAW
sudo python main.py

# 或设置 nmap suid
sudo chmod +s /usr/bin/nmap
```

---

## 更新日志

See [CHANGELOG.md](CHANGELOG.md)

---

## 贡献指南

See [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 插件开发

See [PLUGINS.md](PLUGINS.md)

---

## 免责声明

SecBot 仅供学习与研究使用。请勿用于未经授权的渗透测试或攻击活动。使用者需自行承担所有责任，作者不承担任何直接或间接损失。