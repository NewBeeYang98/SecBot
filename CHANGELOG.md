# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [1.2.0] - 2025-05-11

### Added
- **Swagger分析**: 支持直接上传本地 JSON/YAML 文件进行解析
- **UI美化**: 全新深色主题，渐变按钮、发光Tab、输入框聚焦效果、侧边栏模块列表

### Fixed
- **web_app.py**: 修复 `tab_port_scan` 和 `tab_comprehensive` 中 `env` 变量未定义的bug
- **web_app.py**: 修复 Streamlit 新版重复元素 ID 报错（button/text_input 加唯一 key）
- **启动器脚本**: 修复 Ubuntu 24.04 externally-managed-environment 报错
- **install.py**: 修复离线包安装失败问题
- **依赖安装逻辑**: 优先使用离线包，离线包不存在时自动在线安装
- **模块名映射**: beautifulsoup4→bs4, pycryptodome→Crypto

### Changed
- **启动器**: 优先检测 offline/pip/ 目录，有离线包时优先离线安装
- **pip 安装**: 自动尝试 `--break-system-packages` fallback（Ubuntu 24.04）
- **UI主题**: 全套 GitHub Dark 风格配色，渐变按钮，动画效果

---

## [1.1.0] - 2025-05-11

### Fixed
- **web_app.py**: 修复 Streamlit 新版重复元素 ID 报错（button/text_input 加唯一 key）
- **启动器脚本**: 修复 Ubuntu 24.04 externally-managed-environment 报错
- **install.py**: 修复离线包安装失败问题
- **依赖安装逻辑**: 优先使用离线包，离线包不存在时自动在线安装

### Changed
- **启动器**: 优先检测 offline/pip/ 目录，有离线包时优先离线安装
- **pip 安装**: 自动尝试 `--break-system-packages` fallback（Ubuntu 24.04）
- **模块名映射**: beautifulsoup4→bs4, pycryptodome→Crypto

### Added
- **离线包**: 预置 streamlit/requests/beautifulsoup4/lxml/colorama/pycryptodome/pygments

---

## [1.0.0] - 2025-05-09

### Added
- **main.py** — 交互式菜单，支持 7 大功能模块
- **core/agent.py** — AI 大脑，自动规划 → 执行 → 迭代
- **core/task_queue.py** — 持久化任务队列（JSON）
- **core/executor.py** — 任务执行器
- **core/network_detector.py** — 网络环境检测（互联网/内网隔离/完全隔离）
- **core/check_dependencies.py** — 依赖检查与修复，支持从本地离线包安装
- **modules/ollama_client.py** — 统一模型客户端（OpenAI / Claude / Ollama）
- **modules/ctf_solver.py** — CTF 解题框架，支持 Web/Reverse/Crypto/Pwn/Misc/Forensics
- **modules/scanner.py** — nmap 集成扫描
- **modules/stego.py** — 隐写分析（图片/文件/Hex）
- **modules/sqli.py** — SQL 注入探测与利用
- **modules/brute.py** — HTTP 暴力破解 / 目录扫描
- **modules/report.py** — Markdown 报告生成
- **scanner_iso/isolated_scanner.py** — 零依赖内网扫描器（纯 Python 标准库）
- **install.py** — 在线安装向导（引导配置 AI + 安装依赖 + 创建快捷方式）
- **download_offline.py** — 离线包下载工具（PyPI 真实链接 API 获取）
- **offline/** — 预下载的离线依赖包（sqlmap / Python wheel）
- **prompts/** — CTF/隐写专用提示词模板
- **dicts/** — SQL 注入 payload 字典
- **web_app.py** — Web UI 界面（Streamlit）

### Features
- 4 种运行模式：AutoRun / SemiAuto / Manual / UDiskMode
- 3 种网络环境自动适配：互联网 / 内网隔离 / 完全隔离
- 3 种 AI 提供商：OpenAI (GPT-4o) / Anthropic (Claude) / Ollama (本地)
- 启动时自动检测缺失依赖，按 D 进入交互修复
- U 盘模式：内网扫描 → 导出 JSON → 拿到外网 AI 分析 → 带任务回来执行
- 桌面快捷方式自动创建（Windows .bat / Linux .desktop）
- 图形化 Web UI（Streamlit + 多 Tab 页面）

### Security
- 任务队列数据持久化在本地 JSON
- API Key 配置写入本地 config.py
- 所有网络请求使用自定义 User-Agent
- 命令执行包含安全检查（防止误操作危险命令）