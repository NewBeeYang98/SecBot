# 贡献指南

感谢你关注 SecBot 的开发！欢迎提交 Issue 和 Pull Request。

---

## 如何参与开发

### 1. Fork & Clone

```bash
# Fork 后在本地克隆（将 YOUR_USERNAME 替换为你的 GitHub 用户名）
git clone https://github.com/YOUR_USERNAME/secbot.git
cd secbot

# 添加上游仓库（将 original 替换为实际仓库地址）
git remote add upstream https://github.com/original/secbot.git
```

### 2. 创建功能分支

```bash
git checkout -b feature/your-feature-name
# 或修复类
git checkout -b fix/issue-description
```

### 3. 开发规范

**代码风格**
- Python 3.8+，使用 type hint
- 缩进：4 空格（不用 Tab）
- 行长度：≤ 120 字符
- 模块顶部注明功能说明

```python
"""
模块名称
功能描述
"""

import os
from typing import Optional

def function_name(param: str) -> Optional[str]:
    """函数文档字符串"""
    pass
```

**文件命名**
- 模块：`snake_case.py`
- 测试：`test_module_name.py`
- 配置：`config.py`

**提交规范**

```
<type>: <简短描述>

<详细说明（可选）>

<关闭的Issue（可选）>
Fixes #123
```

Type 类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `refactor`: 重构
- `test`: 测试
- `chore`: 杂项（依赖更新等）

### 4. 测试

```bash
# 语法检查
python -m py_compile your_file.py

# 依赖检查
python core/check_dependencies.py
```

### 5. 提交 & Push

```bash
git add .
git commit -m "feat: 添加新的CTF题型支持"
git push origin feature/your-feature-name
```

然后在 GitHub 上创建 Pull Request。

---

## 提 Issue

提交 Bug 或功能请求时，请包含：

- Python 版本、系统环境
- 复现步骤
- 期望行为 vs 实际行为
- 错误日志/截图

---

## 开发方向建议

如果你想贡献但不知道从哪里入手，以下方向欢迎参与：

- [ ] **模块扩展**：添加更多 CTF 题型的解题支持（如 MISC 流量分析逆向）
- [ ] **Agent 增强**：完善 AI 自动渗透流程的任务规划逻辑
- [ ] **Web 界面**：开发可选的 Web 管理后台
- [ ] **插件系统**：设计可插拔的模块加载机制
- [ ] **测试覆盖**：为各模块添加单元测试
- [ ] **文档完善**：补充各平台安装细节、常见问题

---

## 项目结构说明

```
core/        # 核心引擎，不涉及具体安全工具
modules/     # 功能模块，调用具体安全工具
scanner_iso/ # 零依赖扫描器，纯Python标准库
offline/     # 预下载的离线资源
```

- `core/` 的代码应保持通用，不依赖特定外部工具
- `modules/` 可以调用 nmap / sqlmap 等具体工具
- 新增工具支持优先考虑加入 `modules/`
