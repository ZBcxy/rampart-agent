#!/bin/bash
# =============================================================================
# BeiJiXing Agent - GitHub Deployment Script
# 
# 此脚本用于将本地项目部署到 GitHub 仓库
# 
# 使用方法：
#   bash deploy.sh
#
# 前提条件：
#   1. 已创建 GitHub 仓库 (https://github.com/954510662-bot/BeiJiXing-agent)
#   2. 具有访问该仓库的权限 (SSH 密钥或 Personal Access Token)
# =============================================================================

set -e

echo "=============================================="
echo "BeiJiXing Agent - GitHub Deployment"
echo "=============================================="
echo ""

# 检查是否在正确的目录
if [[ ! -d ".git" ]]; then
    echo "错误: 当前目录不是 Git 仓库"
    echo "请在项目根目录中运行此脚本"
    exit 1
fi

# 设置远程仓库 URL
REPO_URL="https://github.com/954510662-bot/BeiJiXing-agent.git"

echo "步骤 1: 配置远程仓库"
echo "--------------------"

# 检查远程仓库是否已配置
if git remote -v | grep -q "origin"; then
    echo "远程仓库 'origin' 已配置"
    echo "当前 URL:"
    git remote -v
    echo ""
else
    echo "添加远程仓库 'origin'..."
    git remote add origin "${REPO_URL}"
    echo "远程仓库已添加"
fi

echo ""
echo "步骤 2: 检查 Git 配置"
echo "--------------------"

# 配置用户信息（如果尚未配置）
if [[ -z "$(git config user.name)" ]]; then
    echo "请输入 Git 用户名:"
    read -r USER_NAME
    git config user.name "${USER_NAME}"
fi

if [[ -z "$(git config user.email)" ]]; then
    echo "请输入 Git 邮箱:"
    read -r USER_EMAIL
    git config user.email "${USER_EMAIL}"
fi

echo "Git 用户信息:"
echo "  用户名: $(git config user.name)"
echo "  邮箱: $(git config user.email)"
echo ""

echo "步骤 3: 检查待提交的更改"
echo "-----------------------"

# 检查是否有未提交的更改
if git status --porcelain | grep -q .; then
    echo "有待提交的更改:"
    git status --short
    echo ""
    echo "是否提交这些更改? (y/n)"
    read -r -n 1 REPLY
    echo ""
    
    if [[ "$REPLY" =~ ^[Yy]$ ]]; then
        echo "请输入提交信息:"
        read -r COMMIT_MSG
        
        if [[ -z "$COMMIT_MSG" ]]; then
            COMMIT_MSG="Update: $(date '+%Y-%m-%d %H:%M:%S')"
        fi
        
        git add .
        git commit -m "$COMMIT_MSG"
        echo "更改已提交"
    fi
else
    echo "没有待提交的更改"
fi

echo ""
echo "步骤 4: 推送到 GitHub"
echo "--------------------"

echo "准备推送到: ${REPO_URL}"
echo ""
echo "推送选项:"
echo "  1. HTTPS + Personal Access Token (推荐)"
echo "  2. SSH"
echo "  3. 取消"
echo ""
echo "请选择推送方式 (1/2/3):"
read -r -n 1 PUSH_METHOD
echo ""

case "$PUSH_METHOD" in
    1)
        echo "使用 HTTPS 方式推送..."
        echo ""
        echo "请输入 GitHub Personal Access Token:"
        echo "(可以在 GitHub Settings > Developer settings > Personal access tokens 创建)"
        read -r -s TOKEN
        echo ""
        
        # 设置使用 Token 的 URL
        git remote set-url origin "https://954510662-bot:${TOKEN}@github.com/954510662-bot/BeiJiXing-agent.git"
        
        echo "正在推送..."
        git push -u origin main
        ;;
    2)
        echo "使用 SSH 方式推送..."
        echo ""
        echo "请确保您已经:"
        echo "  1. 生成了 SSH 密钥 (ssh-keygen -t ed25519)"
        echo "  2. 将公钥添加到 GitHub 账户"
        echo ""
        echo "正在推送..."
        git remote set-url origin "git@github.com:954510662-bot/BeiJiXing-agent.git"
        git push -u origin main
        ;;
    3)
        echo "取消推送"
        exit 0
        ;;
    *)
        echo "无效的选择"
        exit 1
        ;;
esac

echo ""
echo "=============================================="
echo "部署完成!"
echo "=============================================="
echo ""
echo "您可以访问以下链接查看您的仓库:"
echo "  ${REPO_URL}"
echo ""
