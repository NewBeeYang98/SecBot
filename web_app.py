#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SecBot Web UI - Streamlit界面
一键启动，零配置，自动检测网络和工具环境
"""

import streamlit as st
import subprocess
import sys
import os
import socket
import re
import json
import time
from pathlib import Path

# ── 页面配置 ──────────────────────────────────────────
st.set_page_config(
    page_title="SecBot 安全工具箱",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── 主题样式 ──────────────────────────────────────────
st.markdown("""
<style>
    /* 全局 */
    .stApp { background: #0d1117; }
    h1, h2, h3, h4 { color: #e6edf3 !important; font-family: 'Segoe UI', sans-serif !important; }
    p, span, div { font-family: 'Segoe UI', sans-serif !important; }

    /* 侧边栏 */
    section[data-testid="stSidebar"] { background: #161b22; border-right: 1px solid #30363d; }
    section[data-testid="stSidebar"] .stMarkdown { color: #c9d1d9; }

    /* 指标卡片 */
    .element-container { margin: 0 !important; }

    /* Tab 样式 */
    .stTabs button { background: #161b22 !important; color: #8b949e !important; border-radius: 8px 8px 0 0 !important; font-weight: 500 !important; transition: all 0.2s; }
    .stTabs button:hover { background: #21262d !important; color: #c9d1d9 !important; }
    .stTabs button[data-testid="stTab-active"] { background: #1f6feb !important; color: white !important; box-shadow: 0 -2px 8px rgba(31,111,235,0.4); }

    /* 按钮 */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #238636 0%, #2ea043 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-size: 15px;
        font-weight: 600;
        transition: all 0.2s;
        box-shadow: 0 2px 6px rgba(35,134,54,0.3);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #2ea043 0%, #3fb950 100%);
        box-shadow: 0 4px 12px rgba(35,134,54,0.4);
        transform: translateY(-1px);
    }
    .stButton>button:active { transform: translateY(0); }

    /* 输入框 */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>div>textarea {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        color: #e6edf3 !important;
        border-radius: 8px !important;
        font-size: 14px;
    }
    .stTextInput>div>div>input:focus,
    .stNumberInput>div>div>input:focus,
    .stTextArea>div>div>textarea:focus {
        border-color: #1f6feb !important;
        box-shadow: 0 0 0 3px rgba(31,111,235,0.2) !important;
    }

    /* 选择框 */
    .stSelectbox>div>div {
        background: #161b22 !important;
        border: 1px solid #30363d !important;
        border-radius: 8px !important;
    }
    .stSelectbox [data-baseweb="select"] { background: #161b22 !important; }
    .stSelectbox [data-baseweb="popover"] { background: #161b22 !important; border: 1px solid #30363d; }
    .stSelectbox [role="option"] { background: #161b22 !important; color: #e6edf3 !important; }
    .stSelectbox [role="option"]:hover { background: #30363d !important; }

    /* 进度条 */
    .stProgress > div > div {
        background: linear-gradient(90deg, #238636, #3fb950);
        border-radius: 4px;
        height: 6px;
    }

    /* 多选框/复选框 */
    .stCheckbox label, .stMultiSelect label { color: #c9d1d9 !important; font-size: 14px; }
    .stCheckbox [data-testid="stCheckbox"] > label > div:first-child { border-radius: 4px; }

    /* spinner */
    .stSpinner { color: #3fb950 !important; }

    /* 工具栏 */
    div[data-testid="stToolbar"] { display: none; }

    /* 信息框 */
    .info-box { background: #161b22; border-left: 3px solid #3fb950; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0; }
    .warning-box { background: #161b22; border-left: 3px solid #d29922; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0; }
    .error-box { background: #161b22; border-left: 3px solid #f85149; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0; }
    .success-box { background: #161b22; border-left: 3px solid #238636; padding: 12px 16px; border-radius: 0 8px 8px 0; margin: 8px 0; }

    /* 标签徽章 */
    .tag-badge {
        display: inline-block;
        background: #1f6feb;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        margin: 2px;
        font-weight: 500;
    }
    .tag-green { background: #238636; }
    .tag-red { background: #f85149; }
    .tag-yellow { background: #d29922; color: #0d1117; }
    .tag-purple { background: #8957e5; }

    /* 滚动条 */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #161b22; }
    ::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #484f58; }

    /* divider */
    hr { border-color: #30363d !important; margin: 16px 0; }

    /* 下载按钮 */
    .stDownloadButton>button {
        background: linear-gradient(135deg, #1f6feb, #388bfd) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }

    /* 折叠面板 */
    .streamlit-expanderHeader { background: #161b22; border-radius: 8px; color: #c9d1d9; }
    .streamlit-expanderContent { background: #0d1117; border-radius: 0 0 8px 8px; }

    /* 代码块 */
    .stCodeBlock code { background: #161b22 !important; border-radius: 8px; }

    /* 空元素占位 */
    .stEmpty { background: transparent !important; }

    /* metric数字 */
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; font-weight: 700 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; color: #8b949e !important; }

    /* 滑块 */
    .stSlider [data-baseweb="slider"] { background: #30363d; }
    .stSlider [role="slider"] { background: #1f6feb; }

    /* 上传组件 */
    [data-testid="stFileUploader"] { background: #161b22; border-radius: 8px; border: 1px dashed #30363d; }
</style>
""", unsafe_allow_html=True)

# ── 工具函数 ──────────────────────────────────────────
def check_tool(name, check_cmd):
    """检测工具是否可用"""
    try:
        result = subprocess.run(
            check_cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stdout.strip()[:100]
    except Exception:
        return False, "未找到"


def find_nmap_path():
    """检测 nmap 安装路径（支持 Windows）"""
    import os
    # Windows 常见路径
    if os.name == "nt":
        for base in [os.environ.get("ProgramFiles", "C:\\Program Files"),
                     os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"),
                     "C:\\"]:
            nmap_bin = os.path.join(base, "nmap", "nmap.exe")
            if os.path.exists(nmap_bin):
                return nmap_bin
        # PATH 中查找
        for p in os.environ.get("PATH", "").split(os.pathsep):
            nmap_bin = os.path.join(p, "nmap.exe")
            if os.path.exists(nmap_bin):
                return nmap_bin
    return None

def check_port_open(host, port, timeout=2):
    """检测端口是否开放"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception:
        return False

def get_local_ip():
    """获取本机IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def run_tool(cmd, timeout=60, capture=True):
    """执行系统命令"""
    try:
        if capture:
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            return result.returncode, result.stdout, result.stderr
        else:
            subprocess.Popen(cmd, shell=True)
            return 0, "", ""
    except subprocess.TimeoutExpired:
        return -1, "", "执行超时"
    except Exception as e:
        return 1, "", str(e)

# ── 环境检测 ──────────────────────────────────────────
@st.cache_data(ttl=30)
def detect_env():
    env = {}
    # nmap 检测（兼容 Windows 路径）
    nmap_path = find_nmap_path()
    if nmap_path:
        try:
            result = subprocess.run([nmap_path, "--version"], capture_output=True, text=True, timeout=10)
            env["has_nmap"] = result.returncode == 0
            env["nmap_ver"] = result.stdout.strip().split("\n")[0][:100] if result.stdout else "可用"
        except Exception:
            env["has_nmap"] = False
            env["nmap_ver"] = "未找到"
    else:
        env["has_nmap"], env["nmap_ver"] = check_tool("nmap", "nmap --version 2>&1 | head -1")
    env["has_sqlmap"], env["sqlmap_ver"] = check_tool("sqlmap", "sqlmap --version 2>&1 | head -1")
    env["has_python"], env["python_ver"] = check_tool("python3", "python3 --version 2>&1")
    env["local_ip"] = get_local_ip()
    try:
        import urllib.request
        urllib.request.urlopen("https://www.baidu.com", timeout=3)
        env["network"] = "online"
    except Exception:
        env["network"] = "offline"
    return env

def render_env_bar():
    env = detect_env()
    col1, col2, col3, col4 = st.columns(4)
    net_color = "🟢" if env["network"] == "online" else "🟡"
    nmap_color = "🟢" if env["has_nmap"] else "🔴"
    sql_color = "🟢" if env["has_sqlmap"] else "🔴"
    py_color = "🟢" if env["has_python"] else "🔴"
    with col1:
        st.metric("🌐 网络", env["network"].upper(), f"本机IP: {env['local_ip']}")
    with col2:
        st.metric(f"{nmap_color} Nmap", "可用" if env["has_nmap"] else "未安装")
    with col3:
        st.metric(f"{sql_color} SQLMap", "可用" if env["has_sqlmap"] else "未安装")
    with col4:
        st.metric(f"{py_color} Python", "OK" if env["has_python"] else "异常")

# ── 侧边栏 ────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 16px 0; border-bottom: 1px solid #30363d; margin-bottom: 12px;">
        <h2 style="margin:0; color:#58a6ff;">🛡️ SecBot</h2>
        <p style="margin:4px 0 0 0; color:#8b949e; font-size:13px;">智能网络安全工具箱</p>
    </div>
    """, unsafe_allow_html=True)

    env = detect_env()
    # 网络状态
    net_icon = "🟢" if env["network"] == "online" else "🔴"
    net_label = "已连接" if env["network"] == "online" else "内网隔离"
    nmap_icon = "🟢" if env["has_nmap"] else "🔴"
    sql_icon = "🟢" if env["has_sqlmap"] else "🔴"

    st.markdown(f"""
    <div style="background:#161b22; border-radius:10px; padding:14px; margin-bottom:12px; border:1px solid #30363d;">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="color:#c9d1d9;">🌐 网络</span>
            <span style="background:{'#238636' if env['network']=='online' else '#d29922'}; color:{'white' if env['network']=='online' else '#0d1117'}; padding:2px 10px; border-radius:10px; font-size:12px; font-weight:600;">{net_icon} {net_label}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="color:#c9d1d9;">🔍 Nmap</span>
            <span style="background:{'#238636' if env['has_nmap'] else '#6e7681'}; color:white; padding:2px 10px; border-radius:10px; font-size:12px;">{nmap_icon} {'可用' if env['has_nmap'] else '未安装'}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="color:#c9d1d9;">💉 SQLMap</span>
            <span style="background:{'#238636' if env['has_sqlmap'] else '#6e7681'}; color:white; padding:2px 10px; border-radius:10px; font-size:12px;">{sql_icon} {'可用' if env['has_sqlmap'] else '未安装'}</span>
        </div>
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="color:#c9d1d9;">💻 本机IP</span>
            <code style="background:#0d1117; color:#79c0ff; padding:2px 8px; border-radius:4px; font-size:12px;">{env['local_ip']}</code>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("**📋 功能模块**")
    modules = [
        ("🔍", "端口扫描", "nmap / 纯Socket"),
        ("📂", "目录扫描", "多线程爆破"),
        ("📋", "Swagger分析", "API文档解析"),
        ("🔑", "弱口令爆破", "HTTP表单/Base Auth"),
        ("🕷️", "Web爬虫", "递归+敏感检测"),
        ("🤖", "AI解题", "CTF题目分析"),
        ("🔧", "综合扫描", "一键自动化"),
    ]
    for ico, name, desc in modules:
        st.markdown(f"""
        <div style="display:flex; align-items:center; padding:6px 0; border-bottom:1px solid #21262d;">
            <span style="font-size:16px; margin-right:8px;">{ico}</span>
            <div>
                <div style="color:#c9d1d9; font-size:13px; font-weight:500;">{name}</div>
                <div style="color:#6e7681; font-size:11px;">{desc}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ── 主界面 ────────────────────────────────────────────
st.markdown("""
<div style="text-align:center; margin-bottom: 20px; padding: 20px; background: linear-gradient(135deg, #161b22 0%, #0d1117 100%); border-radius: 12px; border: 1px solid #30363d;">
    <h1 style="margin:0; font-size: 2rem;">🛡️ <span style="color:#58a6ff;">SecBot</span> 安全工具箱</h1>
    <p style="color:#8b949e; font-size:14px; margin:8px 0 0 0;">零配置全自动 · 开箱即用 · 支持内网隔离模式</p>
</div>
""", unsafe_allow_html=True)

render_env_bar()
st.divider()

# ═══ Tab 1: 端口扫描 ════════════════════════════════
def tab_port_scan():
    env = detect_env()  # 修复：添加环境检测
    col1, col2 = st.columns([3, 1])
    with col1:
        target = st.text_input("🎯 目标", value="", placeholder="例: 192.168.1.1 或 scanme.nmap.org",
                                 help="支持IP、域名、网段(例:192.168.1.1/24)")
    with col2:
        mode = st.selectbox("模式", ["快速扫描(常用100端口)", "全端口扫描", "自定义端口"])
    custom_ports = ""
    if mode == "自定义端口":
        custom_ports = st.text_input("端口范围", value="1-1000", placeholder="如: 22,80,443,1000-2000", key="ti_port_custom")
    if mode == "快速扫描(常用100端口)":
        ports = "22,80,443,445,3306,3389,5432,6379,8080,8443,27017"
    elif mode == "全端口扫描":
        ports = "1-65535"
    else:
        ports = custom_ports if custom_ports else "1-1000"
    if st.button("🚀 开始扫描", type="primary", use_container_width=True, key="btn_port_scan"):
        if not target:
            st.warning("请输入目标地址")
            return
        with st.spinner(f"正在扫描 {target} ..."):
            if env["has_nmap"]:
                cmd = f"nmap -sV -sC -Pn {'-p ' + ports if ports != '1-65535' else '-p-'} -oN /tmp/nmap_result.txt {target}"
                code, stdout, stderr = run_tool(cmd, timeout=300)
                # 读取结果
                try:
                    with open("/tmp/nmap_result.txt", "r", encoding="utf-8", errors="ignore") as f:
                        result = f.read()
                except Exception:
                    result = stdout if stdout else stderr
            else:
                # 纯Python扫描
                result = f"[纯Socket扫描] {target}\n端口检测:\n"
                port_list = [21,22,23,80,443,445,3306,3389,5432,6379,8080,8443]
                open_ports = []
                for p in port_list:
                    if check_port_open(target.strip(), p):
                        open_ports.append(str(p))
                result += ", ".join(open_ports) if open_ports else "未发现开放端口"
        st.success("✅ 扫描完成")
        st.text_area("📋 扫描结果", value=result, height=400)
        # 解析开放端口
        if env["has_nmap"]:
            import re
            open_ports = re.findall(r'^(\d+)/', result, re.MULTILINE)
            if open_ports:
                st.markdown("**🔓 检测到的开放端口:**")
                cols = st.columns(min(len(open_ports), 6))
                for i, p in enumerate(set(open_ports)):
                    service = ""
                    for line in result.split("\n"):
                        if line.startswith(p + "/"):
                            service = line.split()[2] if len(line.split()) > 2 else ""
                            break
                    with cols[i % 6]:
                        st.code(f"{p} {service}", language="")

# ── Tab 2: 目录扫描 ───────────────────────────────────
def tab_dir_scan():
    env = detect_env()
    col1, col2 = st.columns([3, 1])
    with col1:
        target = st.text_input("🎯 目标URL", value="", placeholder="http://example.com 或 http://192.168.1.1", key="ti_dir_target")
    with col2:
        threads = st.number_input("线程数", min_value=1, max_value=50, value=20)
    wordlist_options = {
        "常用目录": ["admin", "login", "backup", "api", "phpmyadmin", "robots.txt", "config", "dashboard", "upload", "images", "css", "js", ".git", ".env", "debug", "console", "swagger", "api-docs", "v2/api", "graphiql"],
        "后台路径": ["admin", "admin/login", "administrator", "manage", "backend", "cpanel", "webmail", "webadmin"],
        "API端点": ["api", "api/v1", "api/v2", "swagger", "api-docs", "/graphql", "graphiql", "api/health", "api/status"],
        "敏感文件": [".env", ".git/config", ".htaccess", "config.php", "wp-login", "administrator", "database.yml", "secrets.yml"],
    }
    selected = st.multiselect("📚 字典选择", list(wordlist_options.keys()), default=["常用目录"])
    if st.button("🚀 开始扫描", type="primary", use_container_width=True, key="btn_dir_scan"):
        if not target:
            st.warning("请输入目标URL")
            return
        target = target.rstrip("/")
        words = []
        for s in selected:
            words.extend(wordlist_options[s])
        words = list(set(words))
        progress = st.progress(0)
        status = st.empty()
        found = []
        total = len(words)
        for i, w in enumerate(words):
            status.text(f"扫描: {w} ({i+1}/{total})")
            code, stdout, _ = run_tool(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 3 {target}/{w}", timeout=10)
            try:
                status_code = int(stdout)
                if status_code < 400:
                    found.append((w, status_code))
            except Exception:
                pass
            progress.progress((i+1)/total)
        if found:
            st.success(f"✅ 发现 {len(found)} 个有效路径")
            for path, code in found:
                color = "🟢" if code == 200 else "🟡"
                st.markdown(f"{color} `[{code}]` {target}/{path}")
        else:
            st.info("未发现可访问路径")

# ── Tab 3: Swagger分析 ────────────────────────────────
SWAGGER_PATHS = [
    "/swagger-ui/index.html", "/swagger-ui.html", "/swagger-ui/",
    "/api-docs", "/api-docs/", "/v1/api-docs",
    "/swagger.json", "/v1/swagger.json", "/swagger/v1/swagger.json",
    "/openapi.json", "/v1/openapi.json",
    "/api/swagger.json", "/doc", "/documentation",
    "/swagger", "/api.html", "/api/index.html",
]

def _parse_swagger_file(content: str) -> dict:
    """解析 Swagger/OpenAPI JSON/YAML 内容"""
    try:
        data = json.loads(content)
        return data, "json"
    except Exception:
        pass
    # 尝试 YAML（容错：没有 pyyaml 也正常工作）
    try:
        import yaml  # pylint: disable=import-error
        data = yaml.safe_load(content)
        if data:
            return data, "yaml"
    except Exception:
        pass
    return None, None


def _render_api_paths(data: dict):
    """渲染 API 路径列表"""
    paths = data.get("paths", {})
    if not paths:
        st.info("未找到 paths 字段")
        return
    st.markdown(f"\n**📋 解析到 {len(paths)} 个API路径:**\n")
    for path, methods in sorted(paths.items()):
        for method, details in methods.items():
            if method.upper() in ("GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"):
                summary = details.get("summary", details.get("description", ""))
                auth = details.get("security", [])
                auth_badge = "🔓" if not auth else "🔒"
                st.markdown(f"  `{auth_badge} {method.upper()}` {path}")
                if summary:
                    st.caption(f"    └─ {summary}")


def tab_swagger():
    col1, col2 = st.columns([2, 1])
    with col1:
        target = st.text_input("🎯 目标URL", value="", placeholder="http://192.168.1.1:8080", key="ti_swagger_target")
    with col2:
        st.markdown("&nbsp;", unsafe_allow_html=True)  # 占位对齐
        uploaded = st.file_uploader("📄 或上传本地文件", type=["json", "yaml", "yml"], key="fu_swagger")

    # 文件分析模式
    if uploaded:
        st.markdown("---")
        st.markdown(f"**📄 已加载: `{uploaded.name}`**")
        content = uploaded.getvalue()
        try:
            text = content.decode("utf-8")
        except Exception:
            text = content.decode("gbk", errors="replace")
        data, fmt = _parse_swagger_file(text)
        if data:
            st.success(f"✅ 解析成功（{fmt.upper()}），开始渲染...")
            _render_api_paths(data)
            # 额外信息
            info = data.get("info", {})
            if info:
                st.markdown(f"**📌 标题:** {info.get('title', 'N/A')}  **版本:** {info.get('version', 'N/A')}")
            desc = info.get("description", "")
            if desc:
                with st.expander("📝 描述"):
                    st.markdown(desc)
            servers = data.get("servers", [])
            if servers:
                st.markdown(f"**🌐 服务器:** `{servers[0].get('url', 'N/A')}`")
        else:
            st.error("无法解析文件，请确认是有效的 Swagger/OpenAPI JSON 或 YAML 文件")
        st.markdown("---")

    auto_detect = st.button("🔍 自动探测", type="primary", use_container_width=True, key="btn_swagger_detect")
    if auto_detect and target:
        target = target.rstrip("/")
        found = []
        no_auth = []
        progress = st.progress(0)
        status = st.empty()
        for i, path in enumerate(SWAGGER_PATHS):
            status.text(f"探测: {path}")
            code, stdout, _ = run_tool(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 5 {target}{path}", timeout=10)
            try:
                status_code = int(stdout)
                if status_code == 200:
                    found.append(path)
                    # 检测是否需要认证
                    curl_out, _, _ = run_tool(f"curl -s --max-time 5 {target}{path}", timeout=10)
                    if "security" not in curl_out.lower() and "authoriz" not in curl_out.lower():
                        no_auth.append(path)
            except Exception:
                pass
            progress.progress((i+1)/len(SWAGGER_PATHS))
        if found:
            st.success(f"✅ 发现 {len(found)} 个API文档端点，其中 {len(no_auth)} 个可能无需认证")
            for p in found:
                badge = "🔓 无认证" if p in no_auth else "🔒 需要认证"
                st.markdown(f"{badge} `{p}`")
            # 尝试解析swagger JSON
            for p in found:
                if p.endswith(".json"):
                    code, stdout, _ = run_tool(f"curl -s --max-time 5 {target}{p}", timeout=10)
                    try:
                        data = json.loads(stdout)
                        paths = data.get("paths", {})
                        if paths:
                            st.markdown(f"\n**📋 解析到 {len(paths)} 个API路径:**")
                            for path, methods in paths.items():
                                for method, details in methods.items():
                                    st.markdown(f"  `{method.upper()}` {path} — {details.get('summary','')}")
                    except Exception:
                        pass
        else:
            st.warning("未发现Swagger/OpenAPI文档")

# ── Tab 4: 弱口令爆破 ─────────────────────────────────
COMMON_CREDS = [
    ("admin", "admin"), ("admin", "123456"), ("admin", "password"), ("admin", "12345678"),
    ("admin", "1234"), ("root", "root"), ("root", "toor"),
    ("root", "123456"), ("root", "password"), ("administrator", "administrator"),
    ("administrator", "123456"), ("administrator", "password"),
    ("user", "user"), ("test", "test"), ("guest", "guest"),
    ("tomcat", "tomcat"), ("tomcat", "admin"), ("manager", "manager"),
    ("postgres", "postgres"), ("mysql", "mysql"), ("admin", "Admin@123"),
]

def tab_brute():
    col1, col2 = st.columns(2)
    with col1:
        target = st.text_input("🎯 目标", value="", placeholder="http://192.168.1.1/login")
    with col2:
        mode = st.selectbox("类型", ["HTTP表单", "HTTP Basic认证", "自定义"])
    username_f = st.text_input("👤 用户名", value="admin")
    progress = st.progress(0)
    status = st.empty()
    if st.button("🚀 开始爆破", type="primary", use_container_width=True, key="btn_brute"):
        if not target:
            st.warning("请输入目标URL")
            return
        if mode == "HTTP表单":
            found = []
            for user, pwd in COMMON_CREDS:
                status.text(f"尝试: {user}/{pwd}")
                code, stdout, _ = run_tool(
                    f"curl -s -o /dev/null -w '%{{http_code}}' -d 'username={user}&password={pwd}' {target}",
                    timeout=10
                )
                try:
                    if int(stdout) in [200, 302]:
                        found.append((user, pwd))
                        st.success(f"🎉 撞开: {user} / {pwd}")
                except Exception:
                    pass
                progress.progress(len(found) / len(COMMON_CREDS))
            if not found:
                st.info("未爆破成功（可尝试社工字典）")
        elif mode == "HTTP Basic认证":
            found = []
            for user, pwd in COMMON_CREDS:
                status.text(f"尝试: {user}/{pwd}")
                code, stdout, _ = run_tool(
                    f"curl -s -o /dev/null -w '%{{http_code}}' -u {user}:{pwd} {target}",
                    timeout=10
                )
                try:
                    if int(stdout) == 200:
                        found.append((user, pwd))
                        st.success(f"🎉 撞开: {user} / {pwd}")
                except Exception:
                    pass
                progress.progress(len(found) / len(COMMON_CREDS))
            if not found:
                st.info("未爆破成功")
        else:
            st.info("自定义模式: 请在终端中手动执行")

# ── Tab 5: Web爬虫 ────────────────────────────────────
def tab_crawler():
    target = st.text_input("🎯 目标URL", value="", placeholder="http://192.168.1.1", key="ti_crawler_target")
    depth = st.slider("爬取深度", 1, 5, 2)
    if st.button("🕷️ 开始爬取", type="primary", use_container_width=True, key="btn_crawler"):
        if not target:
            st.warning("请输入目标URL")
            return
        target = target.rstrip("/")
        status_text = st.empty()
        status_text.text("正在递归爬取 ...")
        # 简单爬虫：逐层爬取
        visited = set()
        to_visit = [target]
        sensitive = []
        api_endpoints = []
        for _ in range(depth):
            if not to_visit:
                break
            next_layer = []
            for url in to_visit:
                if url in visited:
                    continue
                visited.add(url)
                code, stdout, _ = run_tool(f"curl -s --max-time 5 {url}", timeout=10)
                if code == 0 and stdout:
                    # 检测敏感信息
                    for pattern in ["api_key", "apiKey", "token", "password", "secret", "Authorization"]:
                        if pattern.lower() in stdout.lower():
                            sensitive.append(url)
                    # 提取链接
                    links = re.findall(r'href=["\'](.*?)["\']', stdout)
                    for link in links:
                        if link.startswith("/"):
                            full = target + link
                            if full not in visited:
                                next_layer.append(full)
                        elif link.startswith(target):
                            if link not in visited:
                                next_layer.append(link)
                        elif link.startswith("http"):
                            if target in link and link not in visited:
                                next_layer.append(link)
                status_text.text(f"已爬: {len(visited)} 页，待爬: {len(next_layer)}")
            to_visit = list(set(next_layer))[:50]  # 限制每层数量
        st.success(f"✅ 完成: 共爬取 {len(visited)} 个页面")
        if sensitive:
            st.markdown(f"⚠️ **发现 {len(sensitive)} 处可能包含敏感信息:**")
            for s in sensitive[:10]:
                st.markdown(f"  🚨 `{s}`")
        st.markdown(f"\n**📋 发现的页面 ({min(len(visited), 20)} 个示例):**")
        for v in list(visited)[:20]:
            st.markdown(f"  - `{v}`")

# ── Tab 6: AI解题 ─────────────────────────────────────
def tab_ai():
    st.markdown("""
    <div class="info-box">
    <strong>🤖 AI 解题助手</strong><br>
    支持 CTF 题目分析与解答思路推荐<br>
    请在 <code>config.py</code> 中配置 API Key 或本地 Ollama
    </div>
    """, unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        provider = st.selectbox("模型提供商", ["ollama-local", "openai", "anthropic", "vllm"])
    with c2:
        model = st.text_input("模型名称", value="qwen2.5-coder:7b" if provider == "ollama-local" else "gpt-4o")
    task_type = st.selectbox("题目类型", ["Web", "Reverse", "Crypto", "Pwn", "Misc", "Forensics", "Cloud"])
    task_desc = st.text_area("题目描述 / 描述", value="", placeholder="粘贴题目描述、源码、链接...", height=200)
    extra = ""
    if "file" in task_type.lower() or "reverse" in task_type.lower():
        extra = st.text_area("附加信息", value="", placeholder="附件路径、IDA截图描述...", height=100)
    if st.button("🧠 开始分析", type="primary", use_container_width=True, key="btn_ai_analyze"):
        if not task_desc:
            st.warning("请输入题目描述")
            return
        with st.spinner("🤖 AI 正在分析 ..."):
            prompt = f"""你是CTF解题专家。用户遇到了一道{task_type}题目。

题目描述：
{task_desc}
{f'附加信息: {extra}' if extra else ''}

请给出：
1. 解题思路（按步骤）
2. 可能用到的工具
3. 关键flag位置或解题突破口
"""
            # 使用 UnifiedClient 统一调用
            try:
                from modules.ollama_client import UnifiedClient
                client = UnifiedClient(provider_name=provider)
                answer = client.generate(prompt, model_override=model if model else None)
            except Exception as e:
                answer = f"❌ 调用失败: {str(e)}"
        st.markdown("### 💡 AI 分析结果")
        st.markdown(answer)

# ═══ Tab 7: 综合扫描 ══════════════════════════════════
def tab_comprehensive():
    env = detect_env()  # 修复：添加环境检测
    target = st.text_input("🎯 目标URL", value="", placeholder="http://192.168.1.1", key="ti_comp_target")
    st.markdown("""
    <div class="warning-box">
    <strong>⚠️ 综合扫描</strong> 将依次执行：端口扫描 → 目录扫描 → Swagger探测 → 弱口令探测<br>
    可能触发安全设备告警，请在获得授权的测试环境中使用
    </div>
    """, unsafe_allow_html=True)
    agree = st.checkbox("我确认已获得合法授权")
    if st.button("🚀 启动综合扫描", type="primary", use_container_width=True, disabled=not agree, key="btn_comprehensive_scan"):
        if not target:
            st.warning("请输入目标URL")
            return
        progress_bar = st.progress(0)
        logs = st.empty()
        results = {}

        # ── 1. 端口扫描 ──
        logs.markdown("🔍 **[1/4] 端口扫描** - 正在探测开放端口 ...")
        progress_bar.progress(0.05)
        host = target.split("//")[1].split("/")[0] if "//" in target else target
        results["ports"] = []
        if env["has_nmap"]:
            # Windows nmap 路径支持
            nmap_cmd = "nmap"
            np = find_nmap_path()
            if np:
                nmap_cmd = np
            code, stdout, _ = run_tool(f'"{nmap_cmd}" -Pn -F -oN /tmp/comp_nmap.txt {host}', timeout=120)
            try:
                with open("/tmp/comp_nmap.txt", "r") as f:
                    results["nmap_raw"] = f.read()
            except Exception:
                results["nmap_raw"] = stdout
            import re
            results["ports"] = re.findall(r'^(\d+)/', results.get("nmap_raw",""), re.MULTILINE)
        else:
            # 无nmap时用Socket扫描常用端口
            common = [21,22,23,80,443,445,3306,3389,5432,6379,8080,8443,27017]
            open_p = []
            for p in common:
                if check_port_open(host, p):
                    open_p.append(str(p))
            results["ports"] = open_p
            results["nmap_raw"] = f"[Socket扫描] 发现端口: {','.join(open_p) if open_p else '无'}"
        logs.markdown("✅ **[1/4] 端口扫描完成**")
        progress_bar.progress(0.25)
        # ── 2. 目录扫描 ──
        logs.markdown("📂 **[2/4] 目录扫描** - 探测常见路径 ...")
        target_http = target if target.startswith("http") else f"http://{target}"
        found_dirs = []
        dir_words = ["admin","api","login","backup","swagger","phpmyadmin",".git","robots.txt"]
        for w in dir_words:
            code, out, _ = run_tool(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 3 {target_http}/{w}", timeout=10)
            try:
                if int(out) < 400:
                    found_dirs.append(w)
            except Exception:
                pass
        results["dirs"] = found_dirs
        logs.markdown("✅ **[2/4] 目录扫描完成**")
        progress_bar.progress(0.5)
        # ── 3. Swagger探测 ──
        logs.markdown("📋 **[3/4] Swagger探测** - 搜索API文档 ...")
        found_swagger = []
        for p in SWAGGER_PATHS[:8]:
            code, out, _ = run_tool(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 3 {target_http}{p}", timeout=10)
            try:
                if int(out) == 200:
                    found_swagger.append(p)
            except Exception:
                pass
        results["swagger"] = found_swagger
        logs.markdown("✅ **[3/4] Swagger探测完成**")
        progress_bar.progress(0.75)
        # ── 4. 生成报告 ──
        logs.markdown("📝 **[4/4] 生成报告** ...")
        report = f"""# 🔍 SecBot 综合扫描报告

**目标**: {target}
**时间**: {time.strftime('%Y-%m-%d %H:%M:%S')}
**网络**: {env['network']}

---

## 📌 开放端口 ({len(results['ports'])}个)
"""
        if results["ports"]:
            for p in set(results["ports"]):
                report += f"- 端口 `{p}`\n"
        else:
            report += "_未发现开放端口_\n"
        report += f"""
---

## 📂 发现目录 ({len(results['dirs'])}个)
"""
        if results["dirs"]:
            for d in results["dirs"]:
                report += f"- `{d}`\n"
        else:
            report += "_未发现可访问目录_\n"
        report += f"""
---

## 📋 Swagger/API文档 ({len(results['swagger'])}个)
"""
        if results["swagger"]:
            for s in results["swagger"]:
                report += f"- `{s}`\n"
        else:
            report += "_未发现Swagger文档_\n"
        progress_bar.progress(1.0)
        logs.markdown("✅ **扫描完成！**")
        st.text_area("📋 综合报告", value=report, height=400)
        st.download_button("💾 下载报告", report.encode(), file_name="secbot_report.md", mime="text/markdown")

# ── 运行所有Tab ───────────────────────────────────────
tabs = st.tabs([
    "🔍 端口扫描",
    "📂 目录扫描",
    "📋 Swagger分析",
    "🔑 弱口令爆破",
    "🕷️ Web爬虫",
    "🤖 AI解题",
    "🔧 综合扫描",
])
with tabs[0]: tab_port_scan()
with tabs[1]: tab_dir_scan()
with tabs[2]: tab_swagger()
with tabs[3]: tab_brute()
with tabs[4]: tab_crawler()
with tabs[5]: tab_ai()
with tabs[6]: tab_comprehensive()
