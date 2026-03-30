# main.py
"""
智能销售报告生成系统 - 主入口
用于批量生成销售人员月度分析报告
支持并发运行多个销售的报告分析工作

支持失败恢复和重试机制：
- 失败记录持久化到 failed_sales.json
- 支持从失败记录恢复运行
- 每个销售最多重试 max_retries 次
- 区分临时性失败和永久性失败
"""
import asyncio
import sys
from typing import Dict, Any
from datetime import datetime

from ReportGenerator import ReportGenerator
from AnaModel import Qwen_model
from SupTool import TimerDisplay
from Data import SalesConigFetcher

# 运行时支持模块
from RuntimeSupport import (
    ANALYSIS_RECORDS_DIR,
    MAX_RETRIES,
    RETRY_DELAY,
    BACKOFF_FACTOR,
    classify_error,
    is_retryable_error,
    AnalysisRecordManager,
    ReportGenerationStats,
    DataBlankError
)


# 单个报告生成
async def generate_single_report(
    time: str,
    sale_config: Dict[str, Any],
    semaphore: asyncio.Semaphore,
    stats: ReportGenerationStats,
    record_manager: AnalysisRecordManager,
    province_sales_count: Dict[str, int],
    retry_count: int = 0
) -> bool:
    """
    生成单个销售人员的报告（带并发控制和重试）

    Args:
        time: 计算月份
        sale_config: 销售人员配置
        semaphore: 信号量，用于控制并发数
        stats: 统计信息对象
        record_manager: 记录管理器
        retry_count: 当前重试次数

    Returns:
        是否成功
    """
    sale_name = sale_config["sale_name"]
    sale_id = sale_config["job_id"]

    async with semaphore:
        try:
            retry_info = f" (第{retry_count + 1}次尝试)" if retry_count > 0 else ""
            print(f"\n[开始] 正在生成 {sale_name} 的报告{retry_info}...")
            generator = ReportGenerator(
                llm=Qwen_model,
                time=time,
                report_time="2025年",
                sale_config=sale_config,
                province_sales_count=province_sales_count
            )

            pdf_path = await generator.run_async()

            stats.increment_completed(sale_id, sale_name, pdf_path)
            record_manager.save_completed_record(sale_config, pdf_path)
            print(f"\n[完成] {sale_name} 的报告已生成: {pdf_path}")
            return True
        
        except DataBlankError as e:
            """数据为空错误,处理策略: 记录数据为空的销售信息, 不重试, 直接返回False"""
            record_manager.save_data_blank_records(sale_config, e.message)
            stats.increment_failed(sale_name, e.message)
            print(f"\n[数据为空] {sale_name} 的报告生成失败: {e}")
            return False

        except Exception as e:
            error_type = classify_error(e)
            error_msg = f"{type(e).__name__}: {str(e)}"

            # 打印详细错误堆栈用于调试
            import traceback
            print(f"\n[详细错误信息] {sale_name} 的错误堆栈:")
            traceback.print_exc()

            # 判断是否需要重试
            if is_retryable_error(error_type) and retry_count < MAX_RETRIES:
                # 保存失败记录
                record_manager.save_failed_record(sale_config, e, retry_count)
                stats.increment_failed(sale_name, error_msg)
                print(f"\n[失败] {sale_name} 的报告生成失败: {error_msg}")
                # 计算重试延迟（指数退避）
                delay = RETRY_DELAY * (BACKOFF_FACTOR ** retry_count)
                # 重试
                if retry_count < MAX_RETRIES:
                    print(f"[重试] {sale_name} 将在 {delay:.1f} 秒后进行第 {retry_count + 2} 次尝试...")
                    await asyncio.sleep(delay)
                    return await generate_single_report(
                        time, sale_config, semaphore, stats, record_manager, province_sales_count, retry_count + 1
                    )
            else:
                # 不可重试的错误或达到最大重试次数
                record_manager.save_failed_record(sale_config, e, retry_count)
                stats.increment_failed(sale_name, error_msg)

                if not is_retryable_error(error_type):
                    print(f"\n[永久失败] {sale_name} 的报告生成失败: {error_msg}")
                else:
                    print(f"\n[达到最大重试次数] {sale_name} 的报告生成失败: {error_msg}")

            return False


# 主函数
async def main(
    time: str = "202601",
    max_concurrent: int = 50,
    resume: bool = False
):
    """
    主函数：并发生成所有销售人员的报告

    Args:
        time: 计算月份 (格式: YYYYMM)
        max_concurrent: 最大并发数
        resume: 是否从失败记录恢复
    """
    print(f"{'='*60}")
    print(f"智能销售报告生成系统")
    print(f"{'='*60}")
    print(f"计算月份: {time}")
    print(f"最大报告分析并发数: {max_concurrent}")
    print(f"最大重试次数: {MAX_RETRIES}")
    print(f"记录目录: {ANALYSIS_RECORDS_DIR}/{time}_analysis_records/")
    
    # 初始化记录管理器
    record_manager = AnalysisRecordManager(time)

    # 获取销售列表
    if resume:
        # 从失败和未完成记录恢复
        sale_configs = record_manager.load_unfinished_records()
        if not sale_configs:
            print("\n[提示] 没有需要重试的销售记录")
            record_manager.print_summary()
            return
        print(f"从记录恢复: {len(sale_configs)} 个销售需要重试")
        
    else:
        # 获取全部销售列表
        sale_configs = await SalesConigFetcher().fetch_all_sales_config()
        print(f"销售人员数量: {len(sale_configs)}")
        # 过滤掉已完成的销售
        completed_ids = record_manager.get_completed_sale_ids()
        if completed_ids:
            sale_configs = [s for s in sale_configs if s["job_id"] not in completed_ids]
            print(f"已完成: {len(completed_ids)} 个，待处理: {len(sale_configs)} 个")
            if len(sale_configs) == 0:
                print("\n[提示] 所有销售已完成，无需重新生成")
                record_manager.print_summary()
                return

    print(f"{'='*60}\n")

    # 启动计时器
    timer = TimerDisplay()
    timer.start()

    # 创建统计对象
    stats = ReportGenerationStats(total=len(sale_configs))

    # 计算各省区销售数量
    province_sales_count = await SalesConigFetcher().count_province_sales()

    # 创建信号量控制并发数
    semaphore = asyncio.Semaphore(max_concurrent)

    # 跟踪已完成的销售ID
    completed_sale_ids = set(record_manager.get_completed_sale_ids())

    # 创建所有任务
    tasks = [
        asyncio.create_task(generate_single_report(time, sales_config, semaphore, stats, record_manager, province_sales_count))
        for sales_config in sale_configs
    ]

    # 并发执行所有任务
    try:
        # 使用 asyncio.wait 等待所有任务完成
        # - generate_single_report 内部已处理所有普通异常并保存到 failed.json
        # - Ctrl+C 时 asyncio.run() 会取消任务，导致 wait() 抛出 CancelledError
        await asyncio.wait(tasks, return_when=asyncio.ALL_COMPLETED)

    except (KeyboardInterrupt, asyncio.CancelledError):
        print("\n\n[中断] 用户中断了报告生成过程，正在取消任务并保存状态...")

        # 取消所有正在运行的任务
        all_tasks = [t for t in tasks if not t.done()]
        if all_tasks:
            print(f"[提示] 正在取消 {len(all_tasks)} 个正在运行的任务...")
            for task in all_tasks:
                task.cancel()

            # 等待所有任务被取消（使用 timeout 防止无限等待）
            try:
                await asyncio.wait_for(asyncio.gather(*all_tasks, return_exceptions=True), timeout=5.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass  # 忽略超时和取消错误

        # 停止计时器
        timer.stop()
        # 保存当前状态
        current_completed_ids = record_manager.get_completed_sale_ids()
        record_manager.save_pending_records(sale_configs, current_completed_ids)

        unfinished_count = len(sale_configs) - len(current_completed_ids)
        print(f"[提示] 已保存 {unfinished_count} 个未完成的销售记录")
        print(f"[提示] 可以使用 --resume 参数继续运行未完成的报告")
        record_manager.print_summary()
        sys.exit(1)

    except Exception as e:
        print(f"\n\n[错误] 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        
        # 停止计时器
        timer.stop()
        
        # 保存所有未完成的销售
        record_manager.save_pending_records(sale_configs, completed_sale_ids)
        record_manager.print_summary()
        sys.exit(1)

    # 停止计时器
    timer.stop()

    # 打印最终统计
    stats.print_summary()

    # 打印记录摘要
    record_manager.print_summary()

    # 如果有失败的销售，提示如何重试
    if record_manager.failed_records or record_manager.pending_records:
        print("\n[提示] 可以使用以下命令重新运行失败的销售:")
        print(f"  python main.py --resume --time {time}")
        print(f"  或者在代码中设置: resume=True")
    
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="智能销售报告生成系统")
    parser.add_argument("--resume", action="store_true", help="从失败记录恢复运行")
    parser.add_argument("--time", type=str, default="202601", help="计算月份 (格式: YYYYMM, 默认为当前月份)")
    parser.add_argument("--concurrent", type=int, default=50, help="最大并发数 (默认: 3)")
    args = parser.parse_args()

    asyncio.run(main(time=args.time, max_concurrent=args.concurrent, resume=args.resume))
