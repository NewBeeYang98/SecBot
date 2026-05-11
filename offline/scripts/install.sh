#!/bin/bash
echo ""
echo "╔════════════════════════════════════════════╗"
echo "║       SecBot 离线安装程序               ║"
echo "╚════════════════════════════════════════════╝"
echo ""

cd "$(dirname "$0")/.."

# 检查Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到Python3: sudo apt install python3 python3-pip"
    exit 1
fi
echo "[OK] $(python3 --version)"

# 安装Python包
echo ""
echo "[1/2] 安装Python依赖包..."
if [ -d "offline/pip" ]; then
    for whl in offline/pip/*.whl; do
        [ -f "$whl" ] || continue
        echo "  安装 $(basename $whl)..."
        sudo pip3 install "$whl" --no-deps -q 2>/dev/null
    done
    sudo pip3 install requests colorama -q 2>/dev/null
    echo "[完成] Python包"
else
    echo "[跳过] 未找到offline/pip目录"
fi

# 检查AI配置
echo ""
echo "[2/2] 检查AI配置..."
if grep -q 'YOUR_API_KEY' config.py 2>/dev/null; then
    echo "[警告] API Key未配置，请编辑config.py"
else
    echo "[OK] AI配置就绪"
fi

# 验证
echo ""
python3 -c "import requests, colorama; print('[OK] Python包正常')" 2>/dev/null

echo ""
echo "════════════════════════════════════════════"
echo " 安装完成! 运行: python3 main.py"
echo "════════════════════════════════════════════"
echo ""
echo " 推荐安装系统工具: sudo apt install nmap sqlmap steghide binwalk"
echo ""
