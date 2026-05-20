#!/usr/bin/env python3
"""BeiJiXing Agent Logo Display Module

该模块负责在终端启动时展示视觉效果良好的品牌标识，
包含动态/静态logo呈现、版本信息显示以及简短的欢迎语。
参考 Claude Code、OpenClaw、Hermes 等主流智能体的设计风格。
"""

import os
import sys
import time
import shutil
from datetime import datetime
from typing import Optional, List


__version__ = "1.0.0"
__author__ = "BeiJiXing Team"


class LogoConfig:
    """Logo 配置类"""
    
    VERSION = __version__
    BUILD_DATE = "2026-05-21"
    AUTHOR = "BeiJiXing Team"
    WELCOME_MESSAGE = "Welcome to BeiJiXing Agent!"
    SUBTITLE = "Your Intelligent AI Assistant"
    
    # 支持的终端颜色
    COLORS = {
        'HEADER': '\033[95m',
        'BLUE': '\033[94m',
        'CYAN': '\033[96m',
        'GREEN': '\033[92m',
        'YELLOW': '\033[93m',
        'WARNING': '\033[93m',
        'FAIL': '\033[91m',
        'RED': '\033[91m',
        'ENDC': '\033[0m',
        'BOLD': '\033[1m',
        'UNDERLINE': '\033[4m',
    }
    
    # 检测终端是否支持颜色
    SUPPORTS_COLOR = (
        hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()
    ) or os.environ.get('FORCE_COLOR', False)


def get_terminal_width() -> int:
    """获取终端宽度"""
    try:
        width = shutil.get_terminal_size().columns
        return width if width > 0 else 80
    except:
        return 80


def get_static_logo() -> str:
    """获取静态 ASCII Art Logo
    
    Returns:
        str: 格式化的 logo 字符串
    """
    width = get_terminal_width()
    
    logo = f"""
{LogoConfig.COLORS['CYAN']}{'=' * min(width, 100)}{LogoConfig.COLORS['ENDC']}

{LogoConfig.COLORS['BOLD']}{LogoConfig.COLORS['GREEN']}
    ██████╗ ███████╗██╗   ██╗███████╗██████╗  ██████╗ ███╗   ██╗
    ██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝██╔══██╗██╔═══██╗████╗  ██║
    ██████╔╝█████╗   ╚████╔╝ █████╗  ██████╔╝██║   ██║██╔██╗ ██║
    ██╔═══╝ ██╔══╝    ╚██╔╝  ██╔══╝  ██╔══██╗██║   ██║██║╚██╗██║
    ██║     ███████╗   ██║   ███████╗██║  ██║╚██████╔╝██║ ╚████║
    ╚═╝     ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝
{LogoConfig.COLORS['ENDC']}

{LogoConfig.COLORS['CYAN']}{'=' * min(width, 100)}{LogoConfig.COLORS['ENDC']}

{LogoConfig.COLORS['YELLOW']}  Version: {LogoConfig.VERSION}    |    Build: {LogoConfig.BUILD_DATE}{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['GREEN']}  {LogoConfig.WELCOME_MESSAGE}{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['BLUE']}  {LogoConfig.SUBTITLE}{LogoConfig.COLORS['ENDC']}

{LogoConfig.COLORS['CYAN']}{'=' * min(width, 100)}{LogoConfig.COLORS['ENDC']}
"""
    return logo


def get_minimal_logo() -> str:
    """获取简洁版 Logo
    
    Returns:
        str: 简洁的 logo 字符串
    """
    return f"""{LogoConfig.COLORS['BOLD']}{LogoConfig.COLORS['GREEN']}
    ██████╗ ███████╗██╗   ██╗███████╗
    ██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝
    ██████╔╝█████╗   ╚████╔╝ █████╗
    ██╔═══╝ ██╔══╝    ╚██╔╝  ██╔══╝
    ██║     ███████╗   ██║   ███████╗
    ╚═╝     ╚══════╝   ╚═╝   ╚══════╝
{LogoConfig.COLORS['ENDC']}
"""


def get_box_logo() -> str:
    """获取方框版 Logo
    
    Returns:
        str: 方框风格的 logo 字符串
    """
    width = get_terminal_width()
    border = "=" * (min(width, 80) - 2)
    
    return f"""{LogoConfig.COLORS['CYAN']}+{border}+{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}                                                                                          {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['GREEN']}██████╗ ███████╗██╗   ██╗███████╗██████╗  ██████╗ ███╗   ██╗{LogoConfig.COLORS['ENDC']}         {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['GREEN']}██╔══██╗██╔════╝╚██╗ ██╔╝██╔════╝██╔══██╗██╔═══██╗████╗  ██║{LogoConfig.COLORS['ENDC']}         {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['GREEN']}██████╔╝█████╗   ╚████╔╝ █████╗  ██████╔╝██║   ██║██╔██╗ ██║{LogoConfig.COLORS['ENDC']}         {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['GREEN']}██╔═══╝ ██╔══╝    ╚██╔╝  ██╔══╝  ██╔══██╗██║   ██║██║╚██╗██║{LogoConfig.COLORS['ENDC']}         {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['GREEN']}██║     ███████╗   ██║   ███████╗██║  ██║╚██████╔╝██║ ╚████║{LogoConfig.COLORS['ENDC']}         {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['GREEN']}╚═╝     ╚══════╝   ╚═╝   ╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝{LogoConfig.COLORS['ENDC']}         {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}                                                                                          {LogoConfig.COLORS['CYAN']}|{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}+{border}+{LogoConfig.COLORS['ENDC']}
"""


def animate_loading(duration: float = 1.0, frames: int = 10) -> None:
    """动态加载动画
    
    Args:
        duration: 动画持续时间（秒）
        frames: 动画帧数
    """
    if not LogoConfig.SUPPORTS_COLOR:
        return
    
    symbols = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    
    interval = duration / frames
    for i in range(frames):
        symbol = symbols[i % len(symbols)]
        print(f"\r{LogoConfig.COLORS['CYAN']}{symbol} {LogoConfig.WELCOME_MESSAGE}{LogoConfig.COLORS['ENDC']}", end='', flush=True)
        time.sleep(interval)
    
    print(f"\r{' ' * 50}\r", end='')


def display_splash(animate: bool = False, style: str = 'default') -> None:
    """显示启动画面
    
    Args:
        animate: 是否显示动态效果
        style: Logo 样式 ('default', 'minimal', 'box')
    """
    if animate and LogoConfig.SUPPORTS_COLOR:
        animate_loading(duration=0.5)
    
    if style == 'minimal':
        print(get_minimal_logo())
    elif style == 'box':
        print(get_box_logo())
    else:
        print(get_static_logo())


def display_version_info() -> None:
    """显示版本信息"""
    print(f"""
{LogoConfig.COLORS['CYAN']}┌{'─' * 50}┐{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  {LogoConfig.COLORS['BOLD']}BeiJiXing Agent{LogoConfig.COLORS['ENDC']} {' ' * 24}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}├{'─' * 50}┤{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  Version:    {LogoConfig.VERSION:<32}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  Build Date: {LogoConfig.BUILD_DATE:<32}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  Author:     {LogoConfig.AUTHOR:<32}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  Python:     {sys.version.split()[0]:<32}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}└{'─' * 50}┘{LogoConfig.COLORS['ENDC']}
""")


def display_welcome() -> None:
    """显示欢迎信息"""
    width = get_terminal_width()
    
    print(f"""
{LogoConfig.COLORS['BOLD']}{LogoConfig.COLORS['GREEN']}{'=' * min(width, 80)}{LogoConfig.COLORS['ENDC']}

    {LogoConfig.COLORS['BOLD']}{LogoConfig.COLORS['GREEN']}{LogoConfig.WELCOME_MESSAGE}{LogoConfig.COLORS['ENDC']}

    {LogoConfig.COLORS['BLUE']}Type 'beijixing --help' for usage information.{LogoConfig.COLORS['ENDC']}

{LogoConfig.COLORS['BOLD']}{LogoConfig.COLORS['GREEN']}{'=' * min(width, 80)}{LogoConfig.COLORS['ENDC']}
""")


def display_info_panel(model: str = "default", status: str = "Ready", mode: str = "Interactive") -> None:
    """显示信息面板
    
    Args:
        model: 当前使用的模型名称
        status: 系统状态
        mode: 运行模式
    """
    import getpass
    
    user = getpass.getuser()
    workspace = os.path.basename(os.getcwd())
    width = get_terminal_width()
    
    print(f"""
{LogoConfig.COLORS['CYAN']}┌{'─' * (min(width, 70) - 2)}┐{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  [Model]    {model:<30} [Status]  {status:<15}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  [User]     {user:<30} [Mode]    {mode:<15}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}  [Workspace] {workspace:<28} [Version] {LogoConfig.VERSION:<14}{LogoConfig.COLORS['CYAN']}│{LogoConfig.COLORS['ENDC']}
{LogoConfig.COLORS['CYAN']}└{'─' * (min(width, 70) - 2)}┘{LogoConfig.COLORS['ENDC']}
""")


class BeiJiXingLogo:
    """BeiJiXing Logo 显示类"""
    
    def __init__(self, style: str = 'default', animate: bool = False, show_info: bool = True):
        """初始化 Logo 显示
        
        Args:
            style: Logo 样式 ('default', 'minimal', 'box')
            animate: 是否显示动态效果
            show_info: 是否显示信息面板
        """
        self.style = style
        self.animate = animate and LogoConfig.SUPPORTS_COLOR
        self.show_info = show_info
    
    def display(self) -> None:
        """显示启动画面"""
        os.system('cls' if os.name == 'nt' else 'clear')
        display_splash(animate=self.animate, style=self.style)
        
        if self.show_info:
            display_info_panel()
    
    def display_version(self) -> None:
        """显示版本信息"""
        display_version_info()
    
    def display_welcome(self) -> None:
        """显示欢迎信息"""
        display_welcome()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='BeiJiXing Agent Logo Display',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Display logo with animation
  %(prog)s --no-animate       Display logo without animation
  %(prog)s --style minimal    Display minimal logo
  %(prog)s --style box        Display box-style logo
  %(prog)s --version          Display version information
  %(prog)s --info             Display information panel
        """
    )
    
    parser.add_argument(
        '--animate', '-a',
        action='store_true',
        default=True,
        help='Enable animation (default: True)'
    )
    
    parser.add_argument(
        '--no-animate',
        action='store_true',
        help='Disable animation'
    )
    
    parser.add_argument(
        '--style', '-s',
        choices=['default', 'minimal', 'box'],
        default='default',
        help='Logo style (default: default)'
    )
    
    parser.add_argument(
        '--version', '-v',
        action='store_true',
        help='Display version information'
    )
    
    parser.add_argument(
        '--info', '-i',
        action='store_true',
        help='Display information panel'
    )
    
    parser.add_argument(
        '--welcome', '-w',
        action='store_true',
        help='Display welcome message'
    )
    
    args = parser.parse_args()
    
    if args.no_animate:
        args.animate = False
    
    if args.version:
        display_version_info()
    elif args.welcome:
        display_welcome()
    elif args.info:
        display_info_panel()
    else:
        logo = BeiJiXingLogo(style=args.style, animate=args.animate)
        logo.display()


if __name__ == '__main__':
    main()
