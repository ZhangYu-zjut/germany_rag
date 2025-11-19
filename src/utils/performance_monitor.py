"""
性能监控工具
用于监控RAG系统各个环节的耗时情况
"""

import time
import functools
from typing import Dict, List, Any, Optional
from collections import defaultdict
from ..utils.logger import logger


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        """初始化性能监控器"""
        self.timings: Dict[str, List[float]] = defaultdict(list)
        self.current_session: Dict[str, float] = {}
        self.session_start_time: Optional[float] = None
        self.session_end_time: Optional[float] = None
        
    def start_session(self):
        """开始一个新的监控会话"""
        self.session_start_time = time.time()
        self.session_end_time = None
        self.current_session.clear()
        logger.debug("[Performance] 性能监控会话开始")
    
    def end_session(self):
        """结束当前监控会话"""
        self.session_end_time = time.time()
        logger.debug("[Performance] 性能监控会话结束")
    
    def record_timing(self, stage_name: str, duration: float):
        """记录某个阶段的耗时"""
        self.timings[stage_name].append(duration)
        self.current_session[stage_name] = duration
        logger.debug(f"[Performance] {stage_name}: {duration:.3f}s")
    
    def get_session_report(self) -> Dict[str, Any]:
        """获取当前会话的性能报告"""
        if not self.session_start_time:
            return {"error": "没有活跃的监控会话"}
        
        total_time = (self.session_end_time or time.time()) - self.session_start_time
        
        report = {
            "total_time": total_time,
            "stages": {},
            "summary": {}
        }
        
        # 计算各阶段耗时和占比
        stage_total = sum(self.current_session.values())
        
        for stage_name, duration in self.current_session.items():
            percentage = (duration / total_time * 100) if total_time > 0 else 0
            report["stages"][stage_name] = {
                "duration": duration,
                "percentage": percentage
            }
        
        # 添加摘要信息
        report["summary"] = {
            "measured_time": stage_total,
            "unmeasured_time": total_time - stage_total,
            "measurement_coverage": (stage_total / total_time * 100) if total_time > 0 else 0
        }
        
        return report
    
    def print_session_report(self):
        """打印当前会话的性能报告"""
        report = self.get_session_report()
        
        if "error" in report:
            print(f"❌ {report['error']}")
            return
        
        print("\n" + "="*50)
        print("🕐 问答性能分析报告")
        print("="*50)
        print(f"总耗时: {report['total_time']:.2f}秒")
        print("-" * 50)
        
        # 按耗时排序显示各阶段
        stages = sorted(report["stages"].items(), key=lambda x: x[1]["duration"], reverse=True)
        
        for stage_name, stats in stages:
            duration = stats["duration"]
            percentage = stats["percentage"]
            print(f"{stage_name:15s}: {duration:6.2f}秒 ({percentage:5.1f}%)")
        
        print("-" * 50)
        
        # 显示摘要
        summary = report["summary"]
        print(f"已测量时间     : {summary['measured_time']:.2f}秒 ({summary['measurement_coverage']:.1f}%)")
        print(f"未测量时间     : {summary['unmeasured_time']:.2f}秒")
        
        # 瓶颈识别
        if stages:
            bottleneck = stages[0]
            print(f"🎯 瓶颈识别    : {bottleneck[0]} (耗时最长)")
            
            if bottleneck[1]["percentage"] > 40:
                print(f"💡 优化建议    : {bottleneck[0]}环节占比过高，建议优先优化")
            elif summary["unmeasured_time"] > 2.0:
                print(f"💡 优化建议    : 存在较多未测量时间，可能存在其他性能瓶颈")
        
        print("="*50)


def performance_timer(stage_name: str, monitor: PerformanceMonitor):
    """性能计时装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                end_time = time.time()
                duration = end_time - start_time
                monitor.record_timing(stage_name, duration)
        return wrapper
    return decorator


# 全局性能监控器实例
global_monitor = PerformanceMonitor()


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return global_monitor


if __name__ == "__main__":
    # 测试性能监控器
    import time
    
    monitor = PerformanceMonitor()
    monitor.start_session()
    
    # 模拟一些操作
    @performance_timer("测试阶段1", monitor)
    def test_stage1():
        time.sleep(0.1)
        return "stage1 done"
    
    @performance_timer("测试阶段2", monitor)
    def test_stage2():
        time.sleep(0.2)
        return "stage2 done"
    
    @performance_timer("测试阶段3", monitor)
    def test_stage3():
        time.sleep(0.05)
        return "stage3 done"
    
    test_stage1()
    test_stage2()
    test_stage3()
    
    monitor.end_session()
    monitor.print_session_report()
