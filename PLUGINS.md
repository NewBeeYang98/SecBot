# SecBot 插件开发指南

> 文档编写中 — 为后续插件系统预留

---

## 概述

SecBot 支持通过插件扩展功能。插件是一个独立的 Python 模块，放置在 `modules/plugins/` 目录下即可被自动加载。

## 已有插件

| 插件 | 类型 | 说明 |
|------|------|------|
| `ctf_solver` | 解题 | Web/Reverse/Crypto/Pwn/Misc/Forensics |
| `stego` | 分析 | 图片隐写/文件附加数据/Hex字符串 |
| `sqli` | 渗透 | SQL注入点探测与利用 |
| `brute` | 渗透 | HTTP登录爆破/目录扫描 |
| `scanner` | 扫描 | nmap集成端口扫描 |

## 计划中的插件

- [ ] `pwn_solver` — 专用PWN题解题插件（结合pwntools）
- [ ] `reverse_helper` — 逆向分析辅助插件
- [ ] `crypto_attack` — 密码学攻击插件（AES/RSA常见攻击）
- [ ] `web_fuzz` — Web目录/参数模糊测试
- [ ] `vuln_scanner` — 已知漏洞POC扫描

## 开发状态

插件系统正在规划中，欢迎贡献！

如果你想添加新功能，最快的方式是在 `modules/` 目录下新建模块文件，然后在 `main.py` 的菜单中添加入口。
