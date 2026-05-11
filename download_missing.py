#!/usr/bin/env python3
"""下载 SecBot Windows 离线 wheel（支持多 Python 版本）"""
import os, sys, json, urllib.request, time, hashlib

OFFLINE = os.path.join(os.path.dirname(__file__), "offline", "pip")
os.makedirs(OFFLINE, exist_ok=True)

PYTHONS = ["cp39", "cp310", "cp311", "cp312"]   # cp38 无 matplotlib，退而用 cp39+
FALLBACK_PYTHONS = ["cp38", "cp39", "cp310", "cp311", "cp312"]

# {包名: {cp版本: (版本, 文件名, url, sha256)}}
NEEDED = {
    # 关键缺包：matplotlib, pyarrow, markupsafe
    "matplotlib": {
        "cp39": ("3.9.4", "matplotlib-3.9.4-cp39-cp39-win_amd64.whl"),
        "cp310": ("3.9.4", "matplotlib-3.9.4-cp310-cp310-win_amd64.whl"),
        "cp311": ("3.9.4", "matplotlib-3.9.4-cp311-cp311-win_amd64.whl"),
        "cp312": ("3.9.4", "matplotlib-3.9.4-cp312-cp312-win_amd64.whl"),
    },
    "pyarrow": {
        "cp38": ("9.0.0", "pyarrow-9.0.0-cp38-cp38-win_amd64.whl"),
        "cp39": ("9.0.0", "pyarrow-9.0.0-cp39-cp39-win_amd64.whl"),
        "cp310": ("9.0.0", "pyarrow-9.0.0-cp310-cp310-win_amd64.whl"),
    },
    "MarkupSafe": {
        "cp38": ("2.1.5", "MarkupSafe-2.1.5-cp38-cp38-win_amd64.whl"),
        "cp39": ("2.1.5", "MarkupSafe-2.1.5-cp39-cp39-win_amd64.whl"),
        "cp310": ("2.1.5", "MarkupSafe-2.1.5-cp310-cp310-win_amd64.whl"),
        "cp311": ("2.1.5", "MarkupSafe-2.1.5-cp311-cp311-win_amd64.whl"),
        "cp312": ("2.1.5", "MarkupSafe-2.1.5-cp312-cp312-win_amd64.whl"),
    },
    "pillow": {
        "cp38": ("10.4.0", "Pillow-10.4.0-cp38-cp38-win_amd64.whl"),
        "cp39": ("11.3.0", "Pillow-11.3.0-cp39-cp39-win_amd64.whl"),
        "cp310": ("12.2.0", "Pillow-12.2.0-cp310-cp310-win_amd64.whl"),
        "cp311": ("12.2.0", "Pillow-12.2.0-cp311-cp311-win_amd64.whl"),
        "cp312": ("12.2.0", "Pillow-12.2.0-cp312-cp312-win_amd64.whl"),
    },
    "numpy": {
        "cp38": ("1.24.4", "numpy-1.24.4-cp38-cp38-win_amd64.whl"),
        "cp39": ("2.0.2", "numpy-2.0.2-cp39-cp39-win_amd64.whl"),
        "cp310": ("2.2.6", "numpy-2.2.6-cp310-cp310-win_amd64.whl"),
        "cp311": ("2.4.4", "numpy-2.4.4-cp311-cp311-win_amd64.whl"),
        "cp312": ("2.4.4", "numpy-2.4.4-cp312-cp312-win_amd64.whl"),
    },
    "pandas": {
        "cp38": ("2.0.3", "pandas-2.0.3-cp38-cp38-win_amd64.whl"),
        "cp39": ("2.3.3", "pandas-2.3.3-cp39-cp39-win_amd64.whl"),
        "cp310": ("2.3.3", "pandas-2.3.3-cp310-cp310-win_amd64.whl"),
        "cp311": ("3.0.2", "pandas-3.0.2-cp311-cp311-win_amd64.whl"),
        "cp312": ("3.0.2", "pandas-3.0.2-cp312-cp312-win_amd64.whl"),
    },
}

def get_url_sha(pkg, version, filename):
    url = f"https://pypi.org/pypi/{pkg}/{version}/{filename}"
    try:
        with urllib.request.urlopen(f"https://pypi.org/pypi/{pkg}/{version}/json", timeout=15) as r:
            data = json.loads(r.read())
        for f in data["releases"][version]:
            if f["filename"] == filename:
                return f["url"], f["digests"]["sha256"]
    except:
        pass
    # fallback: 构造 PyPI direct URL
    safe = filename.replace("_", "_")
    return (f"https://files.pythonhosted.org/packages/"
            f"{filename[:2]}/{filename[2:4]}/{filename[4:]}//{filename}"), None

def download(pkg, version, filename):
    dest = os.path.join(OFFLINE, filename)
    if os.path.exists(dest):
        print(f"  [已有] {filename}")
        return True
    print(f"  [下载] {filename}", flush=True)
    url, sha = get_url_sha(pkg, version, filename)
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            content = r.read()
        if sha and hashlib.sha256(content).hexdigest() != sha:
            print(f"  [错误] SHA256 不匹配: {filename}")
            return False
        with open(dest, "wb") as f:
            f.write(content)
        sz = len(content) / 1024 / 1024
        print(f"  [成功] {filename} ({sz:.1f} MB)")
        return True
    except Exception as e:
        print(f"  [失败] {filename}: {e}")
        return False

def main():
    total = 0
    for pkg, versions in NEEDED.items():
        for py_ver, (version, filename) in versions.items():
            if download(pkg, version, filename):
                total += 1
            time.sleep(0.2)

    print(f"\n新增 {total} 个 wheel")
    whls = [f for f in os.listdir(OFFLINE) if f.endswith(".whl")]
    mb = sum(os.path.getsize(os.path.join(OFFLINE, f)) for f in whls) / 1024 / 1024
    print(f"离线包合计: {len(whls)} 个 wheel，{mb:.1f} MB")

if __name__ == "__main__":
    main()
