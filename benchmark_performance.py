#!/usr/bin/env python3
"""性能基准测试脚本"""

import time
from core.performance import benchmark, async_benchmark, performance_monitor
from core.planner import Planner
from core.memory import WorkingMemory, EpisodicMemory, SemanticMemory


def benchmark_plan_generation():
    """测试规划生成性能"""
    planner = Planner()

    def test_plan_generation():
        for _ in range(10):
            planner.generate_plan('分析销售数据并生成报告', {'history': []})

    result = benchmark(test_plan_generation, iterations=50)
    print('=== 规划生成性能基准 ===')
    print(f'迭代次数: {result.iterations}')
    print(f'平均时间: {result.mean_time*1000:.2f} ms')
    print(f'中位数时间: {result.median_time*1000:.2f} ms')
    print(f'P95时间: {result.p95_time*1000:.2f} ms')
    print(f'P99时间: {result.p99_time*1000:.2f} ms')
    print()


def benchmark_memory_operations():
    """测试记忆系统性能"""
    wm = WorkingMemory()

    def test_memory_add():
        for i in range(50):
            wm.add(f'Memory item {i}', importance=0.8)

    result = benchmark(test_memory_add, iterations=30)
    print('=== 工作记忆写入性能 ===')
    print(f'迭代次数: {result.iterations}')
    print(f'平均时间: {result.mean_time*1000:.2f} ms')
    print(f'中位数时间: {result.median_time*1000:.2f} ms')
    print()


def benchmark_memory_search():
    """测试记忆搜索性能"""
    sm = SemanticMemory()
    
    # 预先添加数据
    for i in range(100):
        sm.add(f'这是关于主题{i}的知识内容，包含关键词信息', tags=[f'tag_{i%10}'])

    def test_search():
        results = sm.search('关键词', limit=5)

    result = benchmark(test_search, iterations=100)
    print('=== 语义记忆搜索性能 ===')
    print(f'迭代次数: {result.iterations}')
    print(f'平均时间: {result.mean_time*1000:.2f} ms')
    print(f'中位数时间: {result.median_time*1000:.2f} ms')
    print()


def benchmark_confidence_evaluation():
    """测试置信度评估性能"""
    planner = Planner()
    plan = planner.generate_plan('生成一份市场分析报告', {'history': []})

    def test_evaluation():
        for _ in range(20):
            planner.evaluate_plan_confidence(plan)

    result = benchmark(test_evaluation, iterations=50)
    print('=== 置信度评估性能 ===')
    print(f'迭代次数: {result.iterations}')
    print(f'平均时间: {result.mean_time*1000:.2f} ms')
    print(f'中位数时间: {result.median_time*1000:.2f} ms')
    print()


def run_all_benchmarks():
    """运行所有性能基准测试"""
    print('=' * 60)
    print('BeiJiXing Agent 性能基准测试')
    print('=' * 60)
    print()

    benchmark_plan_generation()
    benchmark_memory_operations()
    benchmark_memory_search()
    benchmark_confidence_evaluation()

    print('=' * 60)
    print('性能测试完成')
    print('=' * 60)


if __name__ == '__main__':
    run_all_benchmarks()
