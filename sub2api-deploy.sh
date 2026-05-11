#!/bin/bash
# Sub2API 一键部署脚本
# 使用: ./deploy-sub2api.sh

set -e

echo "============================================"
echo "  Sub2API 一键部署脚本"
echo "============================================"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# 检查 root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}请用 root 用户运行: sudo ./deploy-sub2api.sh${NC}"
    exit 1
fi

# ===== 1. 安装 Docker =====
echo -e "${GREEN}[1/6] 检查 Docker...${NC}"
if ! command -v docker &> /dev/null; then
    echo "安装 Docker..."
    apt update
    apt install -y ca-certificates curl gnupg
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    apt update
    apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
fi
docker --version

# ===== 2. 创建目录 =====
echo -e "${GREEN}[2/6] 创建目录...${NC}"
mkdir -p ~/sub2api && cd ~/sub2api

# ===== 3. 下载部署文件 =====
echo -e "${GREEN}[3/6] 下载部署文件...${NC}"
if [ ! -f docker-compose.yml ]; then
    curl -L https://raw.githubusercontent.com/Wei-Shaw/sub2api/main/deploy/docker-compose.yml -o docker-compose.yml
    curl -L https://raw.githubusercontent.com/Wei-Shaw/sub2api/main/deploy/.env.example -o .env.example
    cp .env.example .env
fi

# ===== 4. 配置环境变量 =====
echo -e "${GREEN}[4/6] 配置环境变量 (请修改关键密码)...${NC}"
if [ -f .env ]; then
    echo ".env 已存在，如需重新配置请手动编辑 ~/sub2api/.env"
    read -p "是否编辑 .env? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        nano ~/sub2api/.env
    fi
fi

# ===== 5. 启动服务 =====
echo -e "${GREEN}[5/6] 启动服务...${NC}"
docker-compose up -d

# ===== 6. 检查状态 =====
echo -e "${GREEN}[6/6] 检查状态...${NC}"
sleep 5
docker-compose ps
docker-compose logs --tail=20

echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}部署完成!${NC}"
echo -e "访问地址: http://你的服务器IP:8080"
echo "日志: docker-compose logs -f"
echo "停止: docker-compose down"
echo "============================================${NC}"