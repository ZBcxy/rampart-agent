#!/usr/bin/env python3
"""BEI JI XING Agent One-Click Installation Script"""

import os
import sys
import subprocess
import platform
import urllib.request


def print_step(message):
    """Print installation step"""
    print(f"\n{'='*60}")
    print(f"🔧 {message}")
    print(f"{'='*60}")


def run_command(cmd, cwd=None):
    """Run command"""
    try:
        result = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"❌ Command failed: {cmd}")
            print(f"Error: {result.stderr}")
            return False, result.stderr
        return True, result.stdout
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False, str(e)


def check_python_version():
    """Check Python version"""
    version = sys.version_info
    if version < (3, 12):
        print(f"❌ Python version must be >= 3.12, current: {version.major}.{version.minor}.{version.micro}")
        return False
    print(f"✅ Python version: {version.major}.{version.minor}.{version.micro}")
    return True


def check_wsl():
    """Check if in WSL environment"""
    if platform.system() == 'Linux' and os.path.exists('/proc/version'):
        with open('/proc/version', 'r') as f:
            if 'microsoft' in f.read().lower():
                print("✅ WSL environment detected")
                return True
    print("⚠️ WSL environment is recommended for best experience")
    return False


def install_dependencies():
    """Install dependencies"""
    print_step("Installing dependencies")
    
    # Install base dependencies
    success, _ = run_command("pip install -e .")
    if not success:
        print("❌ Dependency installation failed")
        return False
    
    print("✅ Dependencies installed")
    return True


def create_shortcut():
    """Create shortcut command"""
    print_step("Creating shortcut command")
    
    # Add beijixing command to PATH
    success, _ = run_command("pip install -e .")
    if not success:
        print("❌ Cannot install command")
        return False
    
    print("✅ Shortcut command created")
    return True


def test_installation():
    """Test if installation is successful"""
    print_step("Testing installation")
    
    try:
        from core.logo import print_logo
        from core.planner import Planner
        
        print_logo()
        
        planner = Planner()
        plan = planner.generate_plan("Test task", {})
        print(f"✅ Planner test successful: {plan.id}")
        
        return True
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


def main():
    """Main installation flow"""
    print("""
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
                                                                                
                           One-Click Installation Script
    """)
    
    # Check environment
    if not check_python_version():
        sys.exit(1)
    
    check_wsl()
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create shortcut
    if not create_shortcut():
        sys.exit(1)
    
    # Test installation
    if not test_installation():
        sys.exit(1)
    
    print("\n🎉" * 10)
    print("🎉 BEI JI XING Agent installed successfully! 🎉")
    print("🎉" * 10)
    print("""

Usage:
  1. Command line mode:
     $ python cli/agent_cli.py
     
  2. Execute specific task:
     $ python cli/agent_cli.py "Analyze sales data"
     
  3. API service mode:
     $ python -m gateway.main
     Access: http://localhost:8000

View help:
  $ python cli/agent_cli.py --help
""")


if __name__ == "__main__":
    main()
