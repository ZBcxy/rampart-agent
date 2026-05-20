#!/usr/bin/env python3
"""BeiJiXing Agent 命令行接口"""

import argparse
import asyncio
import json
import sys
from typing import Optional

sys.path.insert(0, '..')

from core.planner import Planner
from core.memory import WorkingMemory, EpisodicMemory, SemanticMemory
from core.executor import DAGExecutor
from core.logo import print_logo


class AgentCLI:
    def __init__(self):
        self.planner = Planner()
        self.executor = DAGExecutor()
        self.working_memory = WorkingMemory()
        self.episodic_memory = EpisodicMemory()
        self.semantic_memory = SemanticMemory()

    def run_plan(self, goal: str, context: Optional[str] = None):
        """运行规划"""
        context_dict = json.loads(context) if context else {}
        plan = self.planner.generate_plan(goal, context_dict)
        
        print(f"\n规划ID: {plan.id}")
        print(f"置信度: {plan.confidence:.2%}")
        print("\n执行步骤:")
        self._print_plan_tree(plan.root, indent=0)
        
        result = self.executor.execute(plan)
        print("\n执行结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        self.episodic_memory.add(goal, str(result), success=result.get('success', False))
        return result

    def _print_plan_tree(self, node, indent=0):
        """打印规划树"""
        prefix = "  " * indent + "└─ " if indent > 0 else ""
        print(f"{prefix}{node.task}")
        if node.children:
            for child in node.children:
                self._print_plan_tree(child, indent + 1)

    def add_memory(self, content: str, memory_type: str = "working"):
        """添加记忆"""
        if memory_type == "working":
            item_id = self.working_memory.add(content)
            print(f"工作记忆添加成功，ID: {item_id}")
        elif memory_type == "episodic":
            episode_id = self.episodic_memory.add(content, "cli_input", True)
            print(f"情节记忆添加成功，ID: {episode_id}")
        elif memory_type == "semantic":
            memory_id = self.semantic_memory.add(content, tags=["cli"])
            print(f"语义记忆添加成功，ID: {memory_id}")

    def search_memory(self, query: str, memory_type: str = "all"):
        """搜索记忆"""
        if memory_type in ["working", "all"]:
            results = self.working_memory.search(query)
            if results:
                print("\n工作记忆搜索结果:")
                for item in results:
                    print(f"- {item.content[:50]}...")
        
        if memory_type in ["episodic", "all"]:
            results = self.episodic_memory.search(query)
            if results:
                print("\n情节记忆搜索结果:")
                for episode in results:
                    print(f"- {episode.input[:30]} -> {episode.output[:30]}")
        
        if memory_type in ["semantic", "all"]:
            results = self.semantic_memory.search(query)
            if results:
                print("\n语义记忆搜索结果:")
                for memory in results:
                    print(f"- {memory.content[:50]}...")

    def show_stats(self):
        """显示统计信息"""
        wm_stats = self.working_memory.get_statistics()
        em_stats = self.episodic_memory.get_statistics()
        sm_stats = self.semantic_memory.get_statistics()
        
        print("=== 记忆系统统计 ===")
        print(f"工作记忆 - 项目数: {wm_stats['total_items']}, 命中率: {wm_stats['hit_rate']:.2%}")
        print(f"情节记忆 - 记录数: {em_stats['total_episodes']}, 成功率: {em_stats['success_rate']:.2%}")
        print(f"语义记忆 - 知识数: {sm_stats['total_memories']}, 标签数: {sm_stats['total_tags']}")

    def chat(self):
        """交互式对话模式"""
        print_logo()
        print("欢迎使用 BeiJiXing Agent 对话模式！")
        print("输入 'exit' 或 'quit' 退出，输入 'stats' 查看统计信息\n")
        
        while True:
            try:
                user_input = input("你: ")
            except EOFError:
                print("\n再见！")
                break
            
            if user_input.lower() in ['exit', 'quit']:
                print("再见！")
                break
            
            if user_input.lower() == 'stats':
                self.show_stats()
                continue
            
            print(f"Agent: 正在处理您的请求...")
            result = self.run_plan(user_input)
            
            if result.get('success'):
                output = result.get('output', '任务已完成')
                print(f"Agent: {output}")
            else:
                error = result.get('error', '执行失败')
                print(f"Agent: 抱歉，执行失败: {error}")


def main():
    parser = argparse.ArgumentParser(description="BeiJiXing Agent 命令行工具")
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    run_parser = subparsers.add_parser('run', help='执行规划')
    run_parser.add_argument('goal', type=str, help='目标任务')
    run_parser.add_argument('--context', type=str, help='上下文JSON')

    memory_parser = subparsers.add_parser('memory', help='记忆管理')
    memory_subparsers = memory_parser.add_subparsers(dest='memory_command')
    
    add_parser = memory_subparsers.add_parser('add', help='添加记忆')
    add_parser.add_argument('content', type=str, help='内容')
    add_parser.add_argument('--type', type=str, choices=['working', 'episodic', 'semantic'], default='working')
    
    search_parser = memory_subparsers.add_parser('search', help='搜索记忆')
    search_parser.add_argument('query', type=str, help='搜索关键词')
    search_parser.add_argument('--type', type=str, choices=['working', 'episodic', 'semantic', 'all'], default='all')

    parser.add_argument('goal', nargs='?', type=str, help='目标任务（无命令时直接执行）')

    args = parser.parse_args()

    cli = AgentCLI()

    if args.command == 'run':
        cli.run_plan(args.goal, args.context)
    elif args.command == 'memory':
        if args.memory_command == 'add':
            cli.add_memory(args.content, args.type)
        elif args.memory_command == 'search':
            cli.search_memory(args.query, args.type)
        else:
            memory_parser.print_help()
    elif args.goal:
        cli.run_plan(args.goal)
    else:
        cli.chat()


if __name__ == '__main__':
    main()
