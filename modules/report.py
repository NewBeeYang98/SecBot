"""
报告生成模块
生成Markdown格式的安全扫描/CTF解题报告
"""

import os
import datetime
from config import REPORT_DIR


class ReportGenerator:
    """报告生成器"""

    def __init__(self):
        self.report_dir = REPORT_DIR

    def generate(self, title, content):
        """生成Markdown报告"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_title = "".join(c if c.isalnum() else "_" for c in title)[:30]
        filename = f"{safe_title}_{timestamp}.md"
        filepath = os.path.join(self.report_dir, filename)

        report = f"""# {title}

**生成时间**: {datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 内容

{content}

---

*本报告由 SecBot 自动生成*
"""

        os.makedirs(self.report_dir, exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(report)

        return f"报告已保存: {filepath}"

    def generate_scan_report(self, target, scan_result, ai_analysis=None):
        """生成扫描报告"""
        title = f"安全扫描报告_{target}"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ai_section = f"\n## AI分析\n\n{ai_analysis}\n" if ai_analysis else ""
        content = f"""
## 目标信息

- **目标**: {target}
- **扫描时间**: {now}

## 扫描结果

{scan_result}
{ai_section}
## 结论与建议

1. [待补充]
2. [待补充]
"""
        return self.generate(title, content)

    def generate_ctf_report(self, challenge_name, solution, flag):
        """生成CTF解题报告"""
        title = f"CTF解题报告_{challenge_name}"
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        content = f"""
## 题目信息

- **题目名称**: {challenge_name}
- **解题时间**: {now}

## 解题过程

{solution}

## 最终Flag

```
{flag}
```
"""
        return self.generate(title, content)
