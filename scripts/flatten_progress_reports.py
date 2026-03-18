#!/usr/bin/env python3
"""
脚本：将 progress_report 目录中的文件移动到上级目录，并删除 progress_report 目录

目录结构示例：
report_tasks/{task_id}/reports/
    └── {time}/
        └── {business_department}/
            └── {region}/
                └── {province}/
                    └── {city_operation_department}/
                        └── {sale_name}/
                            ├── progress_report/    # 过程报告（各章节 md 等）
                            │   ├── chapter1.md
                            │   └── ...
                            └── final_report.pdf    # 最终 PDF

执行后：
report_tasks/{task_id}/reports/
    └── {time}/
        └── {business_department}/
            └── {region}/
                └── {province}/
                    └── {city_operation_department}/
                        └── {sale_name}/
                            ├── chapter1.md         # 从 progress_report 移出
                            ├── ...
                            └── final_report.pdf
"""

import os
import shutil
from pathlib import Path


def flatten_progress_reports(base_dir: str = "backend\\report_tasks\\mashangzhu\\reports\\2025111") -> int:
    """
    遍历 report_tasks 目录，找到所有 progress_report 目录，
    将其中的文件移动到上级目录，然后删除空的 progress_report 目录。

    Args:
        base_dir: 基础目录路径，默认为 "report_tasks"

    Returns:
        处理的 progress_report 目录数量
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        print(f"错误：目录 {base_dir} 不存在")
        return 0

    count = 0

    # 查找所有名为 progress_report 的目录
    for progress_dir in base_path.rglob("progress_report"):
        if not progress_dir.is_dir():
            continue

        parent_dir = progress_dir.parent
        print(f"\n处理: {progress_dir}")

        # 移动 progress_report 中的所有文件到上级目录
        moved_files = []
        for item in progress_dir.iterdir():
            target_path = parent_dir / item.name

            # 如果目标文件已存在，跳过或重命名
            if target_path.exists():
                print(f"  警告: {item.name} 已存在于目标目录，跳过")
                continue

            try:
                shutil.move(str(item), str(target_path))
                moved_files.append(item.name)
                print(f"  移动: {item.name} -> {target_path}")
            except Exception as e:
                print(f"  错误: 移动 {item.name} 失败 - {e}")

        # 检查 progress_report 目录是否为空，如果为空则删除
        remaining_items = list(progress_dir.iterdir())
        if not remaining_items:
            try:
                progress_dir.rmdir()
                print(f"  删除空目录: progress_report")
                count += 1
            except Exception as e:
                print(f"  警告: 删除目录失败 - {e}")
        else:
            print(f"  警告: progress_report 目录非空，保留目录")
            print(f"  剩余文件: {[item.name for item in remaining_items]}")

    return count


def main():
    print("=" * 60)
    print("progress_report 目录扁平化脚本")
    print("=" * 60)

    processed_count = flatten_progress_reports()

    print("\n" + "=" * 60)
    print(f"完成！共处理 {processed_count} 个 progress_report 目录")
    print("=" * 60)


if __name__ == "__main__":
    main()