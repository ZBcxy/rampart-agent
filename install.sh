#!/bin/bash
# =============================================================================
# BeiJiXing Agent - Linux Terminal CLI Installation Script
# 
# 功能：
#   1. 全局安装功能 - 单条命令即可完成全局安装
#   2. 自动检测环境 - 自动检测并一键配置所有缺失的运行环境
#   3. 系统依赖 - 自动安装系统依赖及第三方库
#   4. 快捷启动 - 配置 'beijixing' 命令行快捷启动
#
# 使用方法：
#   curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/install.sh | bash
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
NC='\033[0m' # No Color

# 配置变量
REPO_URL="https://github.com/954510662-bot/beijixing-Agent.git"
INSTALL_DIR="${HOME}/.beijixing"
BIN_DIR="${HOME}/.local/bin"
VERSION="1.0.0"
PYTHON_MIN_VERSION="3.8"

# Logo 显示
show_logo() {
    echo -e "${CYAN}"
    cat << 'EOF'
    ██████╗ ███████╗██╗   ██╗███████╗██████╗  ██████╗ ███╗   ██╗
    ██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝██╔══██╗██╔═══██╗████╗  ██║
    ██████╔╝█████╗   ╚████╔╝ █████╗  ██████╔╝██║   ██║██╔██╗ ██║
    ██╔═══╝ ██╔══╝    ╚██╔╝  ██╔══╝  ██╔══██╗██║   ██║██║╚██╗██║
    ██║     ███████╗   ██║   ███████╗██║  ██║╚██████╔╝██║ ╚████║
    ╚═╝     ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
EOF
    echo -e "${NC}"
    echo -e "${BOLD}${GREEN}BeiJiXing Agent v${VERSION}${NC}"
    echo -e "${CYAN}Your Intelligent AI Assistant${NC}"
    echo ""
}

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

# 检测操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if command -v apt-get &> /dev/null; then
            PKG_MANAGER="apt-get"
            OS_NAME="Ubuntu/Debian"
        elif command -v yum &> /dev/null; then
            PKG_MANAGER="yum"
            OS_NAME="CentOS/RHEL"
        elif command -v dnf &> /dev/null; then
            PKG_MANAGER="dnf"
            OS_NAME="Fedora"
        elif command -v pacman &> /dev/null; then
            PKG_MANAGER="pacman"
            OS_NAME="Arch Linux"
        else
            PKG_MANAGER="unknown"
            OS_NAME="Linux (unknown)"
        fi
    else
        log_error "This script only supports Linux systems!"
        exit 1
    fi
    
    log_info "Detected OS: ${OS_NAME} (${PKG_MANAGER})"
}

# 检测 Python 版本
check_python() {
    log_info "Checking Python installation..."
    
    if ! command -v python3 &> /dev/null; then
        log_warning "Python3 not found. Installing Python3..."
        install_python
    else
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
        PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
        
        if [[ $PYTHON_MAJOR -lt 3 ]] || ([[ $PYTHON_MAJOR -eq 3 ]] && [[ $PYTHON_MINOR -lt 8 ]]); then
            log_error "Python 3.8 or higher is required. Found: Python ${PYTHON_VERSION}"
            log_info "Please upgrade your Python installation."
            exit 1
        fi
        
        log_success "Python ${PYTHON_VERSION} detected"
    fi
}

# 安装 Python
install_python() {
    log_info "Installing Python3..."
    
    case $PKG_MANAGER in
        apt-get)
            sudo apt-get update
            sudo apt-get install -y python3 python3-pip python3-venv
            ;;
        yum)
            sudo yum install -y python3 python3-pip
            ;;
        dnf)
            sudo dnf install -y python3 python3-pip
            ;;
        pacman)
            sudo pacman -Sy --noconfirm python python-pip
            ;;
        *)
            log_error "Unsupported package manager: ${PKG_MANAGER}"
            exit 1
            ;;
    esac
    
    log_success "Python3 installed successfully"
}

# 检测 Git
check_git() {
    if ! command -v git &> /dev/null; then
        log_warning "Git not found. Installing Git..."
        
        case $PKG_MANAGER in
            apt-get)
                sudo apt-get update
                sudo apt-get install -y git
                ;;
            yum)
                sudo yum install -y git
                ;;
            dnf)
                sudo dnf install -y git
                ;;
            pacman)
                sudo pacman -Sy --noconfirm git
                ;;
        esac
        
        log_success "Git installed successfully"
    else
        log_success "Git detected"
    fi
}

# 检测 pip
check_pip() {
    if ! command -v pip3 &> /dev/null; then
        log_warning "pip3 not found. Installing pip3..."
        
        case $PKG_MANAGER in
            apt-get)
                sudo apt-get update
                sudo apt-get install -y python3-pip
                ;;
            yum)
                sudo yum install -y python3-pip
                ;;
            dnf)
                sudo dnf install -y python3-pip
                ;;
            pacman)
                sudo pacman -Sy --noconfirm python-pip
                ;;
        esac
        
        log_success "pip3 installed successfully"
    else
        log_success "pip3 detected"
    fi
}

# 创建安装目录
setup_directories() {
    log_info "Setting up installation directories..."
    
    mkdir -p "${INSTALL_DIR}"
    mkdir -p "${BIN_DIR}"
    mkdir -p "${HOME}/.beijixing/modules"
    mkdir -p "${HOME}/.beijixing/config"
    mkdir -p "${HOME}/.beijixing/logs"
    mkdir -p "${HOME}/.beijixing/data"
    
    log_success "Directories created successfully"
}

# 克隆仓库
clone_repository() {
    log_info "Cloning BeiJiXing Agent repository..."
    
    if [[ -d "${INSTALL_DIR}/.git" ]]; then
        log_warning "BeiJiXing Agent already installed. Updating..."
        cd "${INSTALL_DIR}"
        git pull origin main
    else
        git clone "${REPO_URL}" "${INSTALL_DIR}"
    fi
    
    log_success "Repository cloned successfully"
}

# 安装依赖
install_dependencies() {
    log_info "Installing Python dependencies..."
    
    cd "${INSTALL_DIR}"
    
    # 创建虚拟环境
    if [[ ! -d "venv" ]]; then
        python3 -m venv venv
        log_success "Virtual environment created"
    fi
    
    # 激活虚拟环境并安装依赖
    source venv/bin/activate
    pip install --upgrade pip
    pip install -e .
    
    log_success "Dependencies installed successfully"
}

# 创建命令行脚本
create_cli_script() {
    log_info "Creating CLI launcher script..."
    
    cat > "${BIN_DIR}/beijixing" << 'SCRIPT'
#!/bin/bash
# BeiJiXing Agent CLI Launcher

INSTALL_DIR="${HOME}/.beijixing"
BIN_DIR="${HOME}/.local/bin"

# 激活虚拟环境
if [[ -f "${INSTALL_DIR}/venv/bin/activate" ]]; then
    source "${INSTALL_DIR}/venv/bin/activate"
fi

# 运行 CLI
if [[ -f "${INSTALL_DIR}/cli/beijixing_cli.py" ]]; then
    python3 "${INSTALL_DIR}/cli/beijixing_cli.py" "$@"
else
    echo "Error: CLI not found. Please reinstall BeiJiXing Agent."
    exit 1
fi
SCRIPT
    
    chmod +x "${BIN_DIR}/beijixing"
    
    log_success "CLI launcher script created"
}

# 配置环境变量
configure_environment() {
    log_info "Configuring environment variables..."
    
    # 添加到 .bashrc
    BASHRC_LINE="export PATH=\"${BIN_DIR}:\$PATH\""
    
    if ! grep -q "${BIN_DIR}" "${HOME}/.bashrc" 2>/dev/null; then
        echo "" >> "${HOME}/.bashrc"
        echo "# BeiJiXing Agent" >> "${HOME}/.bashrc"
        echo "${BASHRC_LINE}" >> "${HOME}/.bashrc"
        log_success "Added to ~/.bashrc"
    fi
    
    # 添加到 .zshrc (如果使用 zsh)
    if [[ -f "${HOME}/.zshrc" ]]; then
        if ! grep -q "${BIN_DIR}" "${HOME}/.zshrc" 2>/dev/null; then
            echo "" >> "${HOME}/.zshrc"
            echo "# BeiJiXing Agent" >> "${HOME}/.zshrc"
            echo "${BASHRC_LINE}" >> "${HOME}/.zshrc"
            log_success "Added to ~/.zshrc"
        fi
    fi
    
    # 立即生效
    export PATH="${BIN_DIR}:${PATH}"
    
    log_success "Environment configured successfully"
}

# 创建别名
create_alias() {
    log_info "Creating shell aliases..."
    
    ALIAS_LINE="alias beijixing='${BIN_DIR}/beijixing'"
    
    if ! grep -q "alias beijixing" "${HOME}/.bashrc" 2>/dev/null; then
        echo "${ALIAS_LINE}" >> "${HOME}/.bashrc"
    fi
    
    log_success "Shell alias created"
}

# 运行测试
run_tests() {
    log_info "Running installation tests..."
    
    cd "${INSTALL_DIR}"
    source venv/bin/activate
    
    # 测试 CLI
    if command -v "${BIN_DIR}/beijixing" &> /dev/null; then
        log_success "CLI command test passed"
    else
        log_warning "CLI command test failed"
    fi
    
    # 测试 Python 模块
    if python3 -c "import beijixing" 2>/dev/null; then
        log_success "Python module test passed"
    else
        log_warning "Python module test failed"
    fi
}

# 显示完成信息
show_completion() {
    echo ""
    echo -e "${BOLD}${GREEN}========================================${NC}"
    echo -e "${BOLD}${GREEN}  BeiJiXing Agent Installation Complete!${NC}"
    echo -e "${BOLD}${GREEN}========================================${NC}"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo -e "  1. Restart your terminal or run:"
    echo -e "     ${BOLD}source ~/.bashrc${NC}"
    echo ""
    echo -e "  2. Start BeiJiXing Agent:"
    echo -e "     ${BOLD}beijixing${NC}"
    echo ""
    echo -e "  3. Or use full path:"
    echo -e "     ${BOLD}${BIN_DIR}/beijixing${NC}"
    echo ""
    echo -e "${CYAN}Useful Commands:${NC}"
    echo -e "  ${BOLD}beijixing --help${NC}         Show help"
    echo -e "  ${BOLD}beijixing --version${NC}      Show version"
    echo -e "  ${BOLD}beijixing --logo${NC}          Display logo"
    echo -e "  ${BOLD}beijixing --modules${NC}       List modules"
    echo ""
    echo -e "${CYAN}Configuration:${NC}"
    echo -e "  Config Directory: ${INSTALL_DIR}"
    echo -e "  Modules Directory: ${INSTALL_DIR}/modules"
    echo ""
    echo -e "${GREEN}Thank you for installing BeiJiXing Agent!${NC}"
    echo ""
}

# 主函数
main() {
    echo ""
    show_logo
    
    log_info "Starting BeiJiXing Agent installation..."
    echo ""
    
    # 环境检测
    detect_os
    check_python
    check_git
    check_pip
    
    # 安装步骤
    setup_directories
    clone_repository
    install_dependencies
    create_cli_script
    configure_environment
    create_alias
    
    # 测试
    run_tests
    
    # 完成
    show_completion
}

# 运行主函数
main "$@"
