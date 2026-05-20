#!/bin/bash
# =============================================================================
# BeiJiXing Agent - Version Upgrade Script
# 
# 功能：
#   1. 版本检查 - 检查当前版本和最新版本
#   2. 一键升级 - 自动下载并安装最新版本
#   3. 回滚功能 - 支持版本回滚
#   4. 更新日志 - 显示版本更新内容
#
# 使用方法：
#   beijixing upgrade              - 检查更新
#   beijixing upgrade --check      - 仅检查版本
#   beijixing upgrade --latest     - 升级到最新版本
#   beijixing upgrade --rollback   - 回滚到上一个版本
#   beijixing upgrade --changelog - 显示更新日志
#
# =============================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

# 配置变量
CURRENT_VERSION="1.0.0"
REPO_URL="https://github.com/954510662-bot/beijixing-Agent.git"
INSTALL_DIR="${HOME}/.beijixing"
BACKUP_DIR="${INSTALL_DIR}/backups"
GITHUB_API_URL="https://api.github.com/repos/954510662-bot/beijixing-Agent/releases/latest"

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助
show_help() {
    echo -e "${BOLD}BeiJiXing Agent Upgrade${NC}"
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo -e "  beijixing upgrade [options]"
    echo ""
    echo -e "${CYAN}Options:${NC}"
    echo -e "  ${GREEN}--check${NC}       Check for updates (default)"
    echo -e "  ${GREEN}--latest${NC}     Upgrade to the latest version"
    echo -e "  ${GREEN}--rollback${NC}    Rollback to the previous version"
    echo -e "  ${GREEN}--changelog${NC}   Show changelog"
    echo -e "  ${GREEN}--version${NC}     Show current version"
    echo -e "  ${GREEN}--help${NC}        Show this help message"
    echo ""
}

# 显示当前版本
show_version() {
    echo -e "${BOLD}BeiJiXing Agent${NC}"
    echo -e "${CYAN}Current Version: ${GREEN}${CURRENT_VERSION}${NC}"
    echo ""
}

# 检查最新版本
check_latest_version() {
    log_info "Checking for updates..."
    echo ""
    
    # 显示当前版本
    echo -e "${CYAN}Current Version:${NC} ${YELLOW}${CURRENT_VERSION}${NC}"
    
    # 检查最新版本（这里模拟，实际应该从 GitHub API 获取）
    LATEST_VERSION="${CURRENT_VERSION}"
    UPDATE_AVAILABLE=false
    
    # 模拟版本检查（实际应该调用 GitHub API）
    if command -v curl &> /dev/null; then
        # 尝试从 GitHub 获取最新版本
        REMOTE_VERSION=$(curl -s "${GITHUB_API_URL}" 2>/dev/null | grep '"tag_name"' | sed 's/.*"v\?\([^"]*\)".*/\1/') || true
        
        if [[ -n "$REMOTE_VERSION" ]]; then
            LATEST_VERSION="$REMOTE_VERSION"
            
            # 比较版本
            if [[ "$REMOTE_VERSION" != "$CURRENT_VERSION" ]]; then
                UPDATE_AVAILABLE=true
            fi
        fi
    fi
    
    echo -e "${CYAN}Latest Version:${NC}  ${GREEN}${LATEST_VERSION}${NC}"
    echo ""
    
    if $UPDATE_AVAILABLE; then
        echo -e "${YELLOW}Update available!${NC}"
        echo ""
        echo -e "To upgrade, run:"
        echo -e "  ${BOLD}beijixing upgrade --latest${NC}"
        echo ""
    else
        echo -e "${GREEN}You're using the latest version!${NC}"
        echo ""
    fi
}

# 升级到最新版本
upgrade_to_latest() {
    log_info "Upgrading BeiJiXing Agent..."
    echo ""
    
    # 创建备份
    create_backup
    
    # 停止服务（如果有）
    log_info "Stopping BeiJiXing Agent..."
    pkill -f "beijixing" 2>/dev/null || true
    
    # 更新代码
    log_info "Updating code..."
    cd "${INSTALL_DIR}"
    
    if [[ -d ".git" ]]; then
        git fetch origin
        git pull origin main
    else
        log_warning "Not a git repository. Re-cloning..."
        rm -rf "${INSTALL_DIR}"
        git clone "${REPO_URL}" "${INSTALL_DIR}"
    fi
    
    # 重新安装依赖
    log_info "Reinstalling dependencies..."
    cd "${INSTALL_DIR}"
    
    if [[ -d "venv" ]]; then
        source venv/bin/activate
        pip install --upgrade pip
        pip install -e .
    else
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        pip install -e .
    fi
    
    log_success "Upgrade completed successfully!"
    echo ""
    echo -e "${CYAN}Version: ${CURRENT_VERSION}${NC}"
    echo ""
}

# 创建备份
create_backup() {
    log_info "Creating backup..."
    
    mkdir -p "${BACKUP_DIR}"
    
    BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
    BACKUP_PATH="${BACKUP_DIR}/${BACKUP_NAME}"
    
    cp -r "${INSTALL_DIR}" "${BACKUP_PATH}"
    
    log_success "Backup created: ${BACKUP_PATH}"
}

# 回滚到上一个版本
rollback_version() {
    log_info "Rolling back BeiJiXing Agent..."
    echo ""
    
    # 查找最新备份
    if [[ ! -d "${BACKUP_DIR}" ]]; then
        log_error "No backup found"
        return 1
    fi
    
    LATEST_BACKUP=$(ls -t "${BACKUP_DIR}" | head -n 1)
    
    if [[ -z "$LATEST_BACKUP" ]]; then
        log_error "No backup found"
        return 1
    fi
    
    log_warning "This will restore from backup: ${LATEST_BACKUP}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # 停止服务
        log_info "Stopping BeiJiXing Agent..."
        pkill -f "beijixing" 2>/dev/null || true
        
        # 恢复备份
        log_info "Restoring backup..."
        rm -rf "${INSTALL_DIR}"
        cp -r "${BACKUP_DIR}/${LATEST_BACKUP}" "${INSTALL_DIR}"
        
        # 重新安装
        log_info "Reinstalling..."
        cd "${INSTALL_DIR}"
        
        if [[ -d "venv" ]]; then
            source venv/bin/activate
            pip install -e .
        fi
        
        log_success "Rollback completed successfully!"
    else
        log_info "Rollback cancelled"
    fi
    
    echo ""
}

# 显示更新日志
show_changelog() {
    echo -e "${BOLD}${CYAN}BeiJiXing Agent Changelog${NC}"
    echo -e "${CYAN}================================${NC}"
    echo ""
    
    cat << 'EOF'
Version 1.0.0 (Current)
---------------------
Features:
  - Initial release
  - Core AI Agent functionality
  - Interactive CLI interface
  - Module system
  - Logo display module
  - Basic memory management
  - Performance monitoring
  - Exception handling

Coming Soon:
  - Advanced memory system
  - Multi-agent collaboration
  - Enhanced security features
  - API integration
  - Web search capabilities
  - File management
  - Data processing modules
EOF
    
    echo ""
}

# 主函数
main() {
    local option="${1:-}"
    
    case "$option" in
        --check|-c)
            check_latest_version
            ;;
        --latest|-l)
            upgrade_to_latest
            ;;
        --rollback|-r)
            rollback_version
            ;;
        --changelog|-ch)
            show_changelog
            ;;
        --version|-v)
            show_version
            ;;
        --help|-h)
            show_help
            ;;
        "")
            check_latest_version
            ;;
        *)
            log_error "Unknown option: $option"
            show_help
            exit 1
            ;;
    esac
}

# 运行主函数
main "$@"
