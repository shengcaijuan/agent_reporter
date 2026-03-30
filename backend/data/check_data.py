# check_data.py
"""
检查数据是否为空
输入数据示例：
{
    "code": 1,
    "message": "success",
    "data": {
        "月份": "202601",
        "部门编码": "L11001A",
        "区域经理工号": "1234567890",
        "部门名称": "马上住焕新事业部",
        "区域经理姓名": "张三",
        "岗位名称": "传统经营导师",
        "章节名称": "三、毛利率与产品结构",
        "章节数据": [
            {
                "指标名称": "销售金额",
                "指标路径": 10000,
                "指标数据": {"实际值": 10000, "目标值": 10000,"同期数": 1000, ...}
            }, ...
        ]
    },
    "timestamp": 1768879232115,
    "executTime": 124
}
"""
from typing import Dict, Any, Tuple

_CHAPTER_DATA_KEY = "章节数据"

def check_data(
    raw_data: Dict[str, Any],
    module: int
    ) -> Tuple[bool, str]:
    """
    判断 data 内层 '章节数据' 是否为空
    Args:
        raw_data: dict, 原始数据
        - 正常: { "code": 1, "message": "success", "data": { "月份": "202601", ..., "章节数据": [{...}] }, ... }
        - 失败样式: { "code": 1, "message": "success", "data": { "月份": "", ..., "章节数据": [] }, ... }
        - 请求错误: { "error": "http_error"|"timeout"|..., "message": "..." }
        module: int, 章节号
    Returns:
        Tuple[bool, str]: (是否数据异常, 处理结果消息)
    """
    # 检查 raw_data 是否为字典
    if not isinstance(raw_data, dict):
        return True, f"第{module}章数据异常: 原始数据不是字典类型。原始数据为：\n{raw_data}"

    # 检查是否有 data 字段
    if "data" not in raw_data:
        return True, f"第{module}章数据异常: 缺少 data 字段。原始数据为：\n{raw_data}"

    data = raw_data.get("data")

    # 检查 data 是否为 None
    if data is None:
        return True, f"第{module}章数据异常: data 字段为空。原始数据为：\n{raw_data}"

    # 检查 data 是否为字典
    if not isinstance(data, dict):
        return True, f"第{module}章数据异常: data 不是字典类型。原始数据为：\n{raw_data}"

    chapter = data.get(_CHAPTER_DATA_KEY)

    # 检查章节数据是否为空列表
    if isinstance(chapter, list) and len(chapter) == 0:
        return True, f"第{module}章数据异常: 章节数据为空。原始数据为：\n{raw_data}"

    return False, "数据正常"

    