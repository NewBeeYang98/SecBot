#!/usr/bin/env python3
"""下载 SecBot Windows 离线 wheel 包（PyPI JSON API）"""
import os, sys, json, urllib.request, urllib.error, time

PYTHON_VER = "cp38"   # cp38=3.8 起，兼容大多数 Windows Python
PLATFORM   = "win_amd64"
OFFLINE    = os.path.join(os.path.dirname(__file__), "offline", "pip")
os.makedirs(OFFLINE, exist_ok=True)

PACKAGES = [
    # Web UI 核心
    "streamlit",
    # 数据分析 / 绘图
    "numpy", "pandas", "matplotlib", "pandas",
    # 可视化
    "plotly",
    # HTML 解析
    "beautifulsoup4", "lxml",
    # protobuf / jsonschema（streamlit 依赖）
    "protobuf", "jsonschema", "fastjsonschema",
    # 其他 streamlit 依赖
    "altair", "vega-datasets", "frozendict", "validators",
    "pytz", "python-dateutil", "tzdata",
    "packaging", "typing-extensions",
    # Web
    "requests", "urllib3", "certifi", "charset-normalizer", "idna",
    # Jinja2 / MarkupSafe
    "jinja2", "markupsafe",
    # Markdown
    "markdown", "markdown-it-py", "mdit-py-plugins",
    # TOML
    "tomlkit",
    # Pillow
    "pillow",
    # GitPython
    "gitpython", "gitdb", "smmap",
    # PyYAML
    "pyyaml",
    # cryptography（paramiko 依赖）
    "cryptography",
    # paramiko（ssh 爆破）
    "paramiko",
    # pycryptodome
    "pycryptodome",
    # pyarrow（pandas 依赖）
    "pyarrow",
    # puremagic（文件类型识别）
    "puremagic",
    # websocket
    "websocket-client",
    # blinker（streamlit 依赖）
    "blinker",
    # cachetools
    "cachetools",
    # click
    "click",
    # sympy
    "sympy",
    # toolz
    "toolz",
    # pygments
    "pygments",
    # base58
    "base58",
    # pymdown-extensions
    "pymdown-extensions",
    # pip / setuptools / wheel
    "pip", "setuptools", "wheel",
    # type stubs
    "types-python-dateutil",
]

def get_wheels(package):
    """从 PyPI JSON API 获取 Windows wheel 下载链接"""
    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(url, timeout=15) as r:
            data = json.loads(r.read())
    except Exception as e:
        print(f"  [失败] {package}: {e}")
        return []

    version = data["info"]["version"]
    files = data["releases"][version]

    wheels = []
    for f in files:
        fname = f["filename"]
        if not fname.endswith(".whl"):
            continue
        # 优先 win_amd64 + python version
        if PLATFORM in fname and PYTHON_VER in fname:
            wheels.append((fname, f["url"], f["digests"]["sha256"]))
        # 退而求次：py3-none-any（跨平台纯 Python）
        elif "py3-none-any" in fname and fname.count("-none-any") == 1:
            wheels.append((fname, f["url"], f["digests"]["sha256"]))
        # 再退：abi3（Python 版本无关 ABI）
        elif "abi3" in fname and PLATFORM.split("_")[0] in fname:
            wheels.append((fname, f["url"], f["digests"]["sha256"]))

    # 去重（同包多版本保留最新版）
    seen, result = set(), []
    for fname, url, sha in wheels:
        key = fname.split("-")[0]
        if key not in seen:
            seen.add(key)
            result.append((fname, url, sha))
    return result

def download_wheel(package, fname, url, sha256):
    """下载单个 wheel 并校验 SHA256"""
    dest = os.path.join(OFFLINE, fname)
    if os.path.exists(dest):
        print(f"  [已有] {fname}")
        return True
    print(f"  [下载] {fname}", flush=True)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            content = r.read()
        import hashlib
        if hashlib.sha256(content).hexdigest() != sha256:
            print(f"  [错误] SHA256 不匹配: {fname}")
            return False
        with open(dest, "wb") as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"  [失败] {fname}: {e}")
        return False

def main():
    print(f"目标平台: {PLATFORM}  Python: {PYTHON_VER}")
    print(f"离线目录: {OFFLINE}\n")

    success, failed = 0, []
    seen_pkgs = set()

    for pkg in PACKAGES:
        if pkg in seen_pkgs:
            continue
        seen_pkgs.add(pkg)
        print(f"查询 {pkg} ...", end=" ", flush=True)
        wheels = get_wheels(pkg)
        if not wheels:
            print("无匹配 wheel，跳过")
            failed.append(pkg)
            continue
        for fname, url, sha in wheels:
            ok = download_wheel(pkg, fname, url, sha)
            if ok:
                success += 1
        time.sleep(0.3)

    print(f"\n完成: {success} 个 wheel，失败: {len(failed)}")
    if failed:
        print("失败包:", failed)

    # 统计
    whls = [f for f in os.listdir(OFFLINE) if f.endswith(".whl")]
    total_mb = sum(os.path.getsize(os.path.join(OFFLINE, f)) for f in whls) / 1024 / 1024
    print(f"离线包: {len(whls)} 个 wheel，{total_mb:.1f} MB")

if __name__ == "__main__":
    main()
