#!/usr/bin/env python3
"""
BEI JI XING Agent - GitHub One-Click Installer

Usage:
  curl -sSL https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -
  or
  wget -qO- https://raw.githubusercontent.com/954510662-bot/beijixing-Agent/main/installer.py | python3 -

Features:
  - Auto clone repository
  - Create virtual environment
  - Install dependencies
  - Configure environment
  - Start service
"""

import os
import sys
import subprocess
import platform
import tempfile


def print_logo():
    """Print Logo"""
    logo = r"""
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║   ██████╗ ███████╗██╗     ███████╗██╗     ███████╗██████╗  ██████╗         ║
║   ██╔══██╗██╔════╝██║     ██╔════╝██║     ██╔════╝██╔══██╗██╔═══██╗        ║
║   ██████╔╝█████╗  ██║     █████╗  ██║     █████╗  ██████╔╝██║   ██║        ║
║   ██╔══██╗██╔══╝  ██║     ██╔══╝  ██║     ██╔══╝  ██╔══██╗██║   ██║        ║
║   ██████╔╝███████╗███████╗███████╗███████╗███████╗██║  ██║╚██████╔╝        ║
║   ╚═════╝ ╚══════╝╚══════╝╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝         ║
║                                                                            ║
╚══════════════════════════════════════════════════════════════════════════╝
"""
    print(logo)


def run_cmd(cmd, cwd=None, quiet=False):
    """Run command"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            if not quiet:
                print(f"❌ Command failed: {cmd}")
                print(f"Error: {result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        if not quiet:
            print(f"❌ Exception: {e}")
        return False, str(e)


def check_prerequisites():
    """Check prerequisites"""
    print("🔍 Checking system environment...")
    
    # Check Python version
    if sys.version_info < (3, 12):
        print(f"❌ Python version must be >= 3.12, current: {sys.version_info.major}.{sys.version_info.minor}")
        return False
    print("✅ Python 3.12+")
    
    # Check git
    success, _ = run_cmd("git --version", quiet=True)
    if not success:
        print("❌ Please install git first")
        return False
    print("✅ Git")
    
    # Check pip
    success, _ = run_cmd("pip --version", quiet=True)
    if not success:
        print("❌ Please install pip first")
        return False
    print("✅ pip")
    
    # Check WSL environment
    if platform.system() == 'Linux' and os.path.exists('/proc/version'):
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                print("✅ WSL environment detected")
            else:
                print("⚠️ WSL environment is recommended for best experience")
    
    return True


def clone_repository(repo_url, target_dir):
    """Clone repository"""
    print(f"\n📥 Cloning repository: {repo_url}")
    
    if os.path.exists(target_dir):
        print("⚠️ Directory already exists, updating code...")
        success, _ = run_cmd("git pull", cwd=target_dir)
    else:
        success, _ = run_cmd(f"git clone {repo_url} {target_dir}")
    
    if success:
        print(f"✅ Repository cloned successfully: {target_dir}")
        return True
    print("❌ Repository clone failed")
    return False


def create_venv(target_dir):
    """Create virtual environment"""
    print("\n🧪 Creating virtual environment")
    
    venv_path = os.path.join(target_dir, ".venv")
    
    if os.path.exists(venv_path):
        print("⚠️ Virtual environment already exists")
        return True
    
    success, _ = run_cmd(f"python -m venv {venv_path}")
    if success:
        print(f"✅ Virtual environment created: {venv_path}")
        return True
    print("❌ Virtual environment creation failed")
    return False


def install_dependencies(target_dir):
    """Install dependencies"""
    print("\n📦 Installing dependencies")
    
    venv_pip = os.path.join(target_dir, ".venv", "bin", "pip")
    
    success, _ = run_cmd(f"{venv_pip} install -e .", cwd=target_dir)
    if success:
        print("✅ Dependencies installed")
        return True
    print("❌ Dependency installation failed")
    return False


def setup_commands(target_dir):
    """Setup command aliases"""
    print("\n🔗 Setting up command aliases")
    
    beijixing_script = os.path.join(target_dir, "beijixing")
    script_content = f"""#!/bin/bash
cd {target_dir}
source .venv/bin/activate
python cli/agent_cli.py "$@"
"""
    
    with open(beijixing_script, 'w') as f:
        f.write(script_content)
    
    run_cmd(f"chmod +x {beijixing_script}")
    
    print(f"✅ Command script created: {beijixing_script}")
    print(f"💡 Add to PATH:")
    print(f"   echo 'export PATH=\"{target_dir}:$PATH\"' >> ~/.bashrc")
    print(f"   source ~/.bashrc")
    print(f"   Then use: beijixing")
    
    return True


def test_installation(target_dir):
    """Test installation"""
    print("\n🧪 Testing installation")
    
    venv_python = os.path.join(target_dir, ".venv", "bin", "python")
    
    test_code = """
from core.logo import print_logo
from core.planner import Planner

print_logo()
planner = Planner()
plan = planner.generate_plan("Test installation", {})
print(f"✅ Planner test successful: {plan.id}")
"""
    
    success, output = run_cmd(f'{venv_python} -c "{test_code}"', cwd=target_dir)
    if success:
        print(output)
        return True
    print("❌ Test failed")
    return False


def main():
    """Main function"""
    print_logo()
    print("🚀 BEI JI XING Agent GitHub One-Click Installer")
    print("="*60)
    
    REPO_URL = "https://github.com/954510662-bot/beijixing-Agent.git"
    TARGET_DIR = os.path.join(os.path.expanduser("~"), "beijixing-agent")
    
    # Check environment
    if not check_prerequisites():
        sys.exit(1)
    
    # Clone repository
    if not clone_repository(REPO_URL, TARGET_DIR):
        sys.exit(1)
    
    # Create virtual environment
    if not create_venv(TARGET_DIR):
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies(TARGET_DIR):
        sys.exit(1)
    
    # Setup commands
    setup_commands(TARGET_DIR)
    
    # Test installation
    if not test_installation(TARGET_DIR):
        sys.exit(1)
    
    print("\n🎉" * 15)
    print("🎉 BEI JI XING Agent installed successfully! 🎉")
    print("🎉" * 15)
    print(f"""

📁 Installation directory: {TARGET_DIR}

🚀 Quick Start:

  1. Interactive mode:
     cd {TARGET_DIR}
     source .venv/bin/activate
     python cli/agent_cli.py

  2. Set PATH for direct usage:
     echo 'export PATH="{TARGET_DIR}:$PATH"' >> ~/.bashrc
     source ~/.bashrc
     beijixing

  3. Start API server:
     cd {TARGET_DIR}
     source .venv/bin/activate
     python -m gateway.main
     Access: http://localhost:8000

📖 Documentation:
  - Technical docs: docs/TECHNICAL_DOCUMENTATION.md
  - User manual: docs/USER_MANUAL.md

💡 Tip: WSL Ubuntu 22.04+ is recommended for best experience
""")


if __name__ == "__main__":
    main()
