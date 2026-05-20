#!/bin/bash
# =============================================================================
# BeiJiXing Agent - Module Configuration Script
# 
# 功能：
#   1. 添加模块 - 添加新的功能模块
#   2. 移除模块 - 移除已安装的模块
#   3. 启用模块 - 启用指定的模块
#   4. 禁用模块 - 禁用指定的模块
#   5. 列出模块 - 列出所有可用和已安装的模块
#
# 使用方法：
#   beijixing config add <module_name>    - 添加模块
#   beijixing config remove <module_name>  - 移除模块
#   beijixing config enable <module_name>  - 启用模块
#   beijixing config disable <module_name> - 禁用模块
#   beijixing config list                  - 列出所有模块
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
CONFIG_DIR="${HOME}/.beijixing"
MODULES_DIR="${CONFIG_DIR}/modules"
MODULE_CONFIG="${CONFIG_DIR}/module_config.json"
AVAILABLE_MODULES=(
    "code_analysis"
    "web_search"
    "file_manager"
    "data_processing"
    "api_integration"
    "monitoring"
)

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
    echo -e "${BOLD}BeiJiXing Agent Module Configuration${NC}"
    echo ""
    echo -e "${CYAN}Usage:${NC}"
    echo -e "  beijixing config <command> [module_name]"
    echo ""
    echo -e "${CYAN}Commands:${NC}"
    echo -e "  ${GREEN}list${NC}                     List all modules"
    echo -e "  ${GREEN}add <module_name>${NC}          Add a new module"
    echo -e "  ${GREEN}remove <module_name>${NC}       Remove an installed module"
    echo -e "  ${GREEN}enable <module_name>${NC}        Enable a module"
    echo -e "  ${GREEN}disable <module_name>${NC}       Disable a module"
    echo -e "  ${GREEN}status [module_name]${NC}        Show module status"
    echo ""
    echo -e "${CYAN}Available Modules:${NC}"
    for module in "${AVAILABLE_MODULES[@]}"; do
        echo -e "  - ${module}"
    done
    echo ""
}

# 列出所有模块
list_modules() {
    echo -e "${BOLD}${CYAN}Available Modules:${NC}"
    echo "========================================"
    
    for module in "${AVAILABLE_MODULES[@]}"; do
        if [[ -d "${MODULES_DIR}/${module}" ]]; then
            if [[ -f "${MODULES_DIR}/${module}/enabled" ]]; then
                echo -e "  ${GREEN}✓${NC} ${module} (enabled)"
            else
                echo -e "  ${YELLOW}○${NC} ${module} (disabled)"
            fi
        else
            echo -e "  ${BLUE}·${NC} ${module} (not installed)"
        fi
    done
    
    echo ""
}

# 添加模块
add_module() {
    local module_name="$1"
    
    if [[ -z "$module_name" ]]; then
        log_error "Module name is required"
        return 1
    fi
    
    # 检查模块是否在可用列表中
    local found=0
    for module in "${AVAILABLE_MODULES[@]}"; do
        if [[ "$module" == "$module_name" ]]; then
            found=1
            break
        fi
    done
    
    if [[ $found -eq 0 ]]; then
        log_error "Unknown module: ${module_name}"
        log_info "Use 'beijixing config list' to see available modules"
        return 1
    fi
    
    # 检查是否已安装
    if [[ -d "${MODULES_DIR}/${module_name}" ]]; then
        log_warning "Module '${module_name}' is already installed"
        return 1
    fi
    
    log_info "Installing module: ${module_name}..."
    
    # 创建模块目录
    mkdir -p "${MODULES_DIR}/${module_name}"
    
    # 创建模块配置
    cat > "${MODULES_DIR}/${module_name}/config.json" << EOF
{
    "name": "${module_name}",
    "version": "1.0.0",
    "enabled": true,
    "installed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    
    # 默认启用
    touch "${MODULES_DIR}/${module_name}/enabled"
    
    log_success "Module '${module_name}' installed successfully"
}

# 移除模块
remove_module() {
    local module_name="$1"
    
    if [[ -z "$module_name" ]]; then
        log_error "Module name is required"
        return 1
    fi
    
    # 检查是否已安装
    if [[ ! -d "${MODULES_DIR}/${module_name}" ]]; then
        log_error "Module '${module_name}' is not installed"
        return 1
    fi
    
    log_info "Removing module: ${module_name}..."
    
    # 移除模块目录
    rm -rf "${MODULES_DIR}/${module_name}"
    
    log_success "Module '${module_name}' removed successfully"
}

# 启用模块
enable_module() {
    local module_name="$1"
    
    if [[ -z "$module_name" ]]; then
        log_error "Module name is required"
        return 1
    fi
    
    # 检查是否已安装
    if [[ ! -d "${MODULES_DIR}/${module_name}" ]]; then
        log_error "Module '${module_name}' is not installed"
        log_info "Use 'beijixing config add ${module_name}' to install it"
        return 1
    fi
    
    # 启用模块
    touch "${MODULES_DIR}/${module_name}/enabled"
    
    log_success "Module '${module_name}' enabled successfully"
}

# 禁用模块
disable_module() {
    local module_name="$1"
    
    if [[ -z "$module_name" ]]; then
        log_error "Module name is required"
        return 1
    fi
    
    # 检查是否已安装
    if [[ ! -d "${MODULES_DIR}/${module_name}" ]]; then
        log_error "Module '${module_name}' is not installed"
        return 1
    fi
    
    # 禁用模块
    rm -f "${MODULES_DIR}/${module_name}/enabled"
    
    log_success "Module '${module_name}' disabled successfully"
}

# 显示模块状态
show_status() {
    local module_name="$1"
    
    if [[ -z "$module_name" ]]; then
        # 显示所有模块状态
        echo -e "${BOLD}${CYAN}Module Status:${NC}"
        echo "========================================"
        
        for module in "${AVAILABLE_MODULES[@]}"; do
            if [[ -d "${MODULES_DIR}/${module}" ]]; then
                if [[ -f "${MODULES_DIR}/${module}/enabled" ]]; then
                    echo -e "  ${GREEN}✓${NC} ${module} - enabled"
                else
                    echo -e "  ${YELLOW}○${NC} ${module} - disabled"
                fi
            else
                echo -e "  ${BLUE}·${NC} ${module} - not installed"
            fi
        done
    else
        # 显示指定模块状态
        if [[ -d "${MODULES_DIR}/${module_name}" ]]; then
            echo -e "${BOLD}Module: ${module_name}${NC}"
            echo "--------------------------------"
            
            if [[ -f "${MODULES_DIR}/${module_name}/config.json" ]]; then
                cat "${MODULES_DIR}/${module_name}/config.json"
            fi
            
            if [[ -f "${MODULES_DIR}/${module_name}/enabled" ]]; then
                echo -e "Status: ${GREEN}enabled${NC}"
            else
                echo -e "Status: ${YELLOW}disabled${NC}"
            fi
        else
            log_error "Module '${module_name}' is not installed"
        fi
    fi
    
    echo ""
}

# 主函数
main() {
    local command="${1:-}"
    local module_name="${2:-}"
    
    # 确保配置目录存在
    mkdir -p "${MODULES_DIR}"
    
    case "$command" in
        list)
            list_modules
            ;;
        add)
            add_module "$module_name"
            ;;
        remove)
            remove_module "$module_name"
            ;;
        enable)
            enable_module "$module_name"
            ;;
        disable)
            disable_module "$module_name"
            ;;
        status)
            show_status "$module_name"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            show_help
            ;;
    esac
}

# 运行主函数
main "$@"
