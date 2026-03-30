#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
批量删除HTML文件中的趋势图div部分
删除类似以下格式的HTML块：
    <div style="text-align: center; margin: 20px 0;">
        <img src="product_trend_*.png" alt="第三章趋势图" ...>
    </div>
"""

import os
import re
from pathlib import Path


def remove_trend_div(content: str) -> str:
    """
    删除HTML中的趋势图div部分

    Args:
        content: HTML文件内容

    Returns:
        删除趋势图后的HTML内容
    """
    # 正则匹配趋势图div块
    # 匹配模式：<div style="text-align: center; margin: 20px 0;">...<img src="product_trend_*.png" alt="第三章趋势图"...>...</div>
    pattern = r'\s*<div style="text-align: center; margin: 20px 0;">\s*<img src="product_trend_[^"]+\.png" alt="第三章趋势图"[^>]*>\s*</div>'

    # 执行替换
    new_content = re.sub(pattern, '', content)

    return new_content


def process_html_files(directory: str) -> dict:
    """
    递归处理目录及子目录中的所有HTML文件

    Args:
        directory: HTML文件所在根目录

    Returns:
        处理结果统计
    """
    dir_path = Path(directory)
    # 递归查找所有HTML文件
    html_files = list(dir_path.rglob('*.html'))

    stats = {
        'total': len(html_files),
        'modified': 0,
        'not_modified': 0,
        'error': 0,
        'files': []
    }

    for html_file in html_files:
        try:
            # 读取文件内容
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 删除趋势图div
            new_content = remove_trend_div(content)

            if content != new_content:
                # 写回文件
                with open(html_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                stats['modified'] += 1
                stats['files'].append(f"[已修改] {html_file.relative_to(dir_path)}")
            else:
                stats['not_modified'] += 1
                stats['files'].append(f"[无需修改] {html_file.relative_to(dir_path)}")

        except Exception as e:
            stats['error'] += 1
            stats['files'].append(f"[错误] {html_file.name}: {str(e)}")

    return stats


def main():
    # 目标目录
    target_dir = Path(__file__).parent.parent / 'report_tasks' / 'mashangzhu' / 'reports' / '202512'

    if not target_dir.exists():
        print(f"错误: 目录不存在 - {target_dir}")
        return

    print(f"开始处理目录: {target_dir}")
    print("-" * 50)

    # 处理HTML文件
    stats = process_html_files(str(target_dir))

    # 输出结果
    print(f"\n处理完成!")
    print(f"总文件数: {stats['total']}")
    print(f"已修改: {stats['modified']}")
    print(f"无需修改: {stats['not_modified']}")
    print(f"错误: {stats['error']}")
    print("\n详细结果:")
    for file_info in stats['files']:
        print(f"  {file_info}")


if __name__ == '__main__':
    main()