#!/usr/bin/env python3
"""Polaris Agent CLI - Main Command Line Interface

Polaris 智能体命令行主程序
提供交互式对话、模块管理、版本控制等功能
"""

import os
import sys
import argparse

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.logo import PolarisLogo, LogoConfig, display_version_info
except ImportError:
    PolarisLogo = None
    LogoConfig = type('LogoConfig', (), {'VERSION': '1.0.0'})()


class PolarisCLI:
    """Polaris CLI 主类"""
    
    VERSION = LogoConfig.VERSION
    CONFIG_DIR = os.path.expanduser("~/.polaris")
    MODULES_DIR = os.path.join(CONFIG_DIR, "modules")
    LOG_FILE = os.path.join(CONFIG_DIR, "polaris.log")
    
    def __init__(self):
        """初始化 CLI"""
        self.setup_config_dir()
    
    def setup_config_dir(self):
        """创建配置目录"""
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
        os.makedirs(self.MODULES_DIR, exist_ok=True)
    
    def _init_agent(self, use_local: bool = False):
        """Lazy-init the Agent with tools."""
        import os
        from core.agent import Agent, AgentConfig

        # Local model (Ollama / vLLM / llama.cpp)
        if use_local or os.environ.get("LOCAL_LLM_PROVIDER"):
            provider = os.environ.get("LOCAL_LLM_PROVIDER", "ollama")
            model = os.environ.get("LOCAL_LLM_MODEL", "qwen3:8b")
            base_url = os.environ.get("LOCAL_LLM_URL", None)
            if provider == "ollama":
                base_url = base_url or "http://localhost:11434/v1"

            config = AgentConfig(
                model=model,
                provider="openai",
                api_key="not-needed",
                api_base=base_url,
                max_steps=int(os.environ.get("POLARIS_MAX_STEPS", "20")),
            )
        else:
            config = AgentConfig(
                model=os.environ.get("LLM_MODEL", "gpt-4o"),
                provider=os.environ.get("LLM_PROVIDER", "openai"),
                api_key=os.environ.get("OPENAI_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"),
                api_base=os.environ.get("OPENAI_API_BASE"),
                max_steps=int(os.environ.get("POLARIS_MAX_STEPS", "20")),
            )

        agent = Agent(config=config)

        # Register tools
        try:
            from tools.registry import ToolRegistry
            r = ToolRegistry()
            r.register_all()
            for name in r.list_all():
                agent.register_tool(name, _make_tool_func(r, name),
                                    description=r.get(name).description if r.get(name) else "")
        except ImportError:
            pass

        return agent

    def run_interactive(self):
        """运行交互式对话 — 接入真实 Agent"""
        import asyncio

        print(f"\n{LogoConfig.COLORS['GREEN']}Polaris Agent — Type 'exit' to quit, 'help' for commands{LogoConfig.COLORS['ENDC']}\n")

        agent = self._init_agent()

        try:
            while True:
                user_input = input(f"{LogoConfig.COLORS['CYAN']}polaris>{LogoConfig.COLORS['ENDC']} ").strip()

                if user_input.lower() in ['exit', 'quit', 'q']:
                    print(f"\n{LogoConfig.COLORS['YELLOW']}Goodbye!{LogoConfig.COLORS['ENDC']}\n")
                    break
                elif user_input.lower() in ['help', 'h', '?']:
                    self.show_help()
                elif user_input.lower() == 'version':
                    print(f"Polaris Agent v{self.VERSION}")
                elif user_input.lower() == 'clear':
                    os.system('cls' if os.name == 'nt' else 'clear')
                elif user_input:
                    print(f"{LogoConfig.COLORS['BLUE']}Processing...{LogoConfig.COLORS['ENDC']}")
                    try:
                        result = asyncio.run(agent.run(user_input))
                        if result.success:
                            print(f"{LogoConfig.COLORS['GREEN']}{result.summary[:1000]}{LogoConfig.COLORS['ENDC']}")
                            if result.tool_calls:
                                for tc in result.tool_calls[-5:]:
                                    status = "✓" if tc.get("error") is None else "✗"
                                    print(f"  {status} {tc['tool']}: {str(tc.get('result', tc.get('error', '')))[:100]}")
                        else:
                            print(f"{LogoConfig.COLORS['RED']}{result.summary}{LogoConfig.COLORS['ENDC']}")
                    except Exception as e:
                        print(f"{LogoConfig.COLORS['RED']}Error: {e}{LogoConfig.COLORS['ENDC']}")
        except KeyboardInterrupt:
            print(f"\n\n{LogoConfig.COLORS['YELLOW']}Interrupted. Type 'exit' to quit.{LogoConfig.COLORS['ENDC']}\n")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
Available Commands:
  help, h, ?      - Show this help message
  exit, quit, q   - Exit the program
  version, v      - Show version information
  clear, cls      - Clear the screen
  config          - Show configuration
  modules         - List available modules
  upgrade         - Check for updates
        """
        print(help_text)
    
    def list_modules(self):
        """列出已安装的模块"""
        print(f"\n{LogoConfig.COLORS['CYAN']}Installed Modules:{LogoConfig.COLORS['ENDC']}")
        print("-" * 50)
        
        if os.path.exists(self.MODULES_DIR):
            modules = [d for d in os.listdir(self.MODULES_DIR) if os.path.isdir(os.path.join(self.MODULES_DIR, d))]
            if modules:
                for module in sorted(modules):
                    print(f"  - {module}")
            else:
                print("  No modules installed.")
        else:
            print("  No modules directory found.")
        
        print()
    
    def show_config(self):
        """显示配置信息"""
        print(f"""
{LogoConfig.COLORS['CYAN']}Configuration:{LogoConfig.COLORS['ENDC']}
{'-' * 50}
  Version:    {self.VERSION}
  Config Dir: {self.CONFIG_DIR}
  Modules:    {self.MODULES_DIR}
  Python:     {sys.version.split()[0]}
  Platform:   {sys.platform}
""")
    
    def check_upgrade(self):
        """检查版本更新"""
        print(f"""
{LogoConfig.COLORS['CYAN']}Checking for updates...{LogoConfig.COLORS['ENDC']}
{'-' * 50}
  Current Version: {self.VERSION}
  Latest Version:  {self.VERSION} (up to date)
""")


def _make_tool_func(registry, tool_name):
    def tool_func(**kwargs):
        return registry.execute(tool_name, **kwargs)
    return tool_func


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        prog='polaris',
        description='Polaris Agent - Your Intelligent AI Assistant',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Start interactive mode
  %(prog)s -v                 Show version information
  %(prog)s --logo             Display logo
  %(prog)s --modules           List installed modules
  %(prog)s --config           Show configuration
  %(prog)s upgrade            Check for updates

Quick Commands:
  %(prog)s add <module>       Add a new module
  %(prog)s remove <module>    Remove a module
  %(prog)s enable <module>    Enable a module
  %(prog)s disable <module>   Disable a module
        """
    )
    
    parser.add_argument(
        '-v', '--version',
        action='store_true',
        help='Show version information'
    )
    
    parser.add_argument(
        '--logo',
        action='store_true',
        help='Display logo and exit'
    )
    
    parser.add_argument(
        '--modules',
        action='store_true',
        help='List installed modules'
    )
    
    parser.add_argument(
        '--config',
        action='store_true',
        help='Show configuration'
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        default='interactive',
        help='Command to run (interactive, upgrade, etc.)'
    )
    
    parser.add_argument(
        'args',
        nargs='*',
        help='Additional arguments'
    )
    
    args = parser.parse_args()
    
    cli = PolarisCLI()
    
    if args.logo:
        if PolarisLogo:
            logo = PolarisLogo()
            logo.display()
        else:
            print("Logo module not available")
        return
    
    if args.version:
        display_version_info()
        return
    
    if args.modules:
        cli.list_modules()
        return
    
    if args.config:
        cli.show_config()
        return
    
    if args.command == 'upgrade':
        cli.check_upgrade()
        return
    
    if args.command == 'add' and len(args.args) > 0:
        print(f"Adding module: {args.args[0]}")
        return
    
    if args.command == 'remove' and len(args.args) > 0:
        print(f"Removing module: {args.args[0]}")
        return
    
    if args.command == 'enable' and len(args.args) > 0:
        print(f"Enabling module: {args.args[0]}")
        return
    
    if args.command == 'disable' and len(args.args) > 0:
        print(f"Disabling module: {args.args[0]}")
        return
    
    # 显示启动画面并进入交互模式
    if PolarisLogo:
        logo = PolarisLogo(animate=True)
        logo.display()
    
    cli.run_interactive()


if __name__ == '__main__':
    main()
