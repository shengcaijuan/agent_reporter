"""
公共工具函数模块
提供归因分析模块中通用的辅助函数
"""
from pypinyin import lazy_pinyin, Style


def snake_to_pascal(snake_str: str) -> str:
    """
    将 snake_case 转换为 PascalCase

    :param snake_str: snake_case格式的字符串
    :return: PascalCase格式的字符串

    示例：
        snake_to_pascal('income_traditional_channel') -> 'IncomeTraditionalChannel'
    """
    return ''.join(word.capitalize() for word in snake_str.split('_'))


def _contains_chinese(text: str) -> bool:
    """
    检测字符串是否包含中文字符

    :param text: 待检测的字符串
    :return: 如果包含中文字符返回True，否则返回False
    """
    return any('\u4e00' <= char <= '\u9fff' for char in text)


def name_to_snake_key(name: str) -> str:
    """
    将名称转换为snake_case格式的key
    支持英文和中文名称：
    - 如果名称已经是snake_case格式, 直接返回
    - 如果包含中文, 使用pypinyin转换为拼音
    - 如果是英文，进行简单的格式转换

    :param name: 指标名称（可以是中文或英文）
    :return: snake_case格式的key

    示例：
        name_to_snake_key("传统渠道收入") -> "chuan_tong_qu_dao_shou_ru"
        name_to_snake_key("income_traditional_channel") -> "income_traditional_channel"
        name_to_snake_key("Online Income") -> "online_income"
    """
    # 如果已经是snake_case格式（包含下划线且为小写字母数字组合），直接使用
    if '_' in name and name.replace('_', '').replace(' ', '').islower() and not _contains_chinese(name):
        return name

    # 如果包含中文，使用pypinyin转换
    if _contains_chinese(name):
        # 转换为拼音，然后转为snake_case
        pinyin_list = lazy_pinyin(name, style=Style.NORMAL)
        # 过滤空字符串，并用下划线连接，转为小写
        key = '_'.join(word.lower().strip() for word in pinyin_list if word.strip())
        # 移除非字母数字和下划线的字符（包括中文标点、括号等）
        key = ''.join(char for char in key if char.isalnum() or char == '_')
        # 移除连续的下划线
        while "__" in key:
            key = key.replace("__", "_")
        return key.strip("_")
    else:
        # 非中文：简单转换（移除特殊字符，用下划线替换空格和特殊符号，转为小写）
        key = name.lower().replace(" ", "_").replace("/", "_").replace("-", "_")
        # 移除连续的下划线
        while "__" in key:
            key = key.replace("__", "_")
        # 移除首尾下划线
        return key.strip("_")

