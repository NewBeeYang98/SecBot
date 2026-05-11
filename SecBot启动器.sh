#!/bin/bash
# ═══════════════════════════════════════════════════════
#  SecBot 一键启动器 v1.0
#  零配置全自动：检测 → 安装依赖 → 启动 WebUI
# ═══════════════════════════════════════════════════════

set -e

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
RESET='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ═══════════════════════════════════════════════════════
#  Banner
# ═══════════════════════════════════════════════════════
banner() {
    echo -e "${CYAN}${BOLD}"
    echo "  ██████╗ ██████╗ ███████╗ █████╗  ██████╗██╗  ██╗"
    echo "  ██╔══██╗██╔══██╗██╔════╝██╔══██╗██╔════╝██║  ██║"
    echo "  ██████╔╝██████╔╝█████╗  ███████║██║     ███████║"
    echo "  ██╔══██╗██╔══██╗██╔══╝  ██╔══██║██║     ██╔══██║"
    echo "  ██████╔╝██║  ██║███████╗██║  ██║╚██████╗██║  ██║"
    echo "  ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝"
    echo -e "${RESET}${CYAN}  智能网络安全工具箱 · 零配置全自动 · 开箱即用${RESET}"
    echo ""
}

# ═══════════════════════════════════════════════════════
#  阶段1：检查Python
# ═══════════════════════════════════════════════════════
check_python() {
    echo -e "${CYAN}⚡ 检查Python...${RESET}"
    if command -v python3 &>/dev/null; then
        PYTHON="python3"
    elif command -v python &>/dev/null; then
        PYTHON="python"
    else
        echo -e "${RED}✗ 未找到 Python，请先安装 Python 3.8+${RESET}"
        echo "  下载: https://www.python.org/downloads/"
        exit 1
    fi
    PYVER=$($PYTHON --version 2>&1 | awk '{print $2}')
    PYMAJOR=$(echo $PYVER | cut -d. -f1)
    PYMINOR=$(echo $PYVER | cut -d. -f2)
    if [ "$PYMAJOR" -lt 3 ] || ([ "$PYMAJOR" -eq 3 ] && [ "$PYMINOR" -lt 8 ]); then
        echo -e "${RED}✗ Python版本过低: $PYVER，需要 3.8+${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✓ Python $PYVER${RESET}"
}

# ═══════════════════════════════════════════════════════
#  阶段2：自动安装依赖
# ═══════════════════════════════════════════════════════
install_deps() {
    echo ""
    echo -e "${CYAN}⚡ 检查并安装依赖...${RESET}"
    DEPS="streamlit requests beautifulsoup4 lxml colorama pycryptodome pygments"
    MISSING=""

    # 检查是否有离线包目录
    OFFLINE_DIR="$SCRIPT_DIR/offline/pip"
    HAS_OFFLINE=false
    if [ -d "$OFFLINE_DIR" ] && [ "$(ls -A "$OFFLINE_DIR" 2>/dev/null)" ]; then
        HAS_OFFLINE=true
        echo -e "  ${CYAN}发现离线包目录，优先使用离线安装${RESET}"
    fi

    for dep in $DEPS; do
        # 模块名到包名的映射
        case $dep in
            beautifulsoup4) PKG="beautifulsoup4"; MOD="bs4" ;;
            pycryptodome)  PKG="pycryptodome"; MOD="Crypto" ;;
            *)             PKG="$dep"; MOD="$dep" ;;
        esac

        if $PYTHON -c "import $MOD" 2>/dev/null; then
            echo -e "  ${GREEN}✓ $dep${RESET}"
        else
            INSTALLED=false
            # 先尝试离线包
            if [ "$HAS_OFFLINE" = true ]; then
                WHL=$(find "$OFFLINE_DIR" -name "${PKG}*.whl" -o -name "${PKG}*.tar.gz" 2>/dev/null | head -1)
                if [ -n "$WHL" ]; then
                    echo -e "  ${CYAN}↗ 离线安装 $dep...${RESET}"
                    $PYTHON -m pip install "$WHL" --no-deps -q 2>/dev/null && INSTALLED=true
                fi
            fi
            # 离线失败则在线安装
            if [ "$INSTALLED" = false ]; then
                echo -e "  ${YELLOW}↗ 在线安装 $dep...${RESET}"
                # 尝试普通安装，失败则尝试 --break-system-packages (Ubuntu 24.04)
                $PYTHON -m pip install $dep -q --user 2>/dev/null || \
                $PYTHON -m pip install $dep -q --break-system-packages 2>/dev/null || true
            fi
            # 验证安装
            if $PYTHON -c "import $MOD" 2>/dev/null; then
                echo -e "  ${GREEN}✓ $dep 安装成功${RESET}"
            else
                echo -e "  ${RED}✗ $dep 安装失败${RESET}"
                MISSING="$MISSING $dep"
            fi
        fi
    done
    echo ""
    if [ -n "$MISSING" ]; then
        echo -e "${YELLOW}⚠ 以下包安装失败: $MISSING${RESET}"
    else
        echo -e "${GREEN}✓ 依赖就绪${RESET}"
    fi
}

# ═══════════════════════════════════════════════════════
#  阶段3：网络检测
# ═══════════════════════════════════════════════════════
check_network() {
    echo ""
    echo -e "${CYAN}🌐 检测网络环境...${RESET}"
    if curl -s --max-time 3 https://www.baidu.com >/dev/null 2>&1; then
        echo -e "${GREEN}✓ 网络正常（互联网模式）${RESET}"
        NET_MODE="online"
    else
        echo -e "${YELLOW}⚠ 无法访问互联网（内网/隔离模式）${RESET}"
        NET_MODE="offline"
    fi
}

# ═══════════════════════════════════════════════════════
#  阶段4：检查web_app
# ═══════════════════════════════════════════════════════
check_webapp() {
    echo ""
    if [ ! -f "web_app.py" ]; then
        echo -e "${RED}✗ web_app.py 未找到${RESET}"
        exit 1
    fi
    echo -e "${GREEN}✓ Web UI 文件就绪${RESET}"
}

# ═══════════════════════════════════════════════════════
#  阶段5：启动
# ═══════════════════════════════════════════════════════
launch() {
    echo ""
    echo "═══════════════════════════════════════════════════════"
    echo -e "${GREEN}${BOLD}  ✅ 准备就绪，正在启动 SecBot Web UI...${RESET}"
    echo "═══════════════════════════════════════════════════════"
    echo ""
    echo -e "  浏览器打开: ${CYAN}http://localhost:8501${RESET}"
    echo -e "  按 ${YELLOW}Ctrl+C${RESET} 停止服务"
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${RESET}"
    echo ""

    # 自动打开浏览器 (macOS / Linux)
    if [[ "$OSTYPE" == "darwin"* ]]; then
        sleep 2 && open http://localhost:8501 &
    elif command -v xdg-open &>/dev/null; then
        sleep 2 && xdg-open http://localhost:8501 &
    fi

    $PYTHON -m streamlit run web_app.py \
        --server.port 8501 \
        --browser.gatherUsageStats false \
        --server.headless true \
        --server.address localhost
}

# ═══════════════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════════════
banner
check_python
install_deps
check_network
check_webapp
launch
