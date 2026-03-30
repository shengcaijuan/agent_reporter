# postprocess_data.py
"""
处理原始数据
"""
from typing import Dict, Any, List
from unittest import result
import re


def _clean_dict_keys(obj: Any) -> Any:
    """
    递归清理字典中所有键名的空白字符（去除所有空白，包括中间空格）
    兼容API返回数据中键名可能包含多余空白的问题，如 " 实际值"、"指标 数据" 等

    Args:
        obj: 要清理的对象（字典、列表或其他）

    Returns:
        清理后的对象
    """
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            # 去除键名中的所有空白字符（包括前、后、中间的空格、制表符、换行符等）
            clean_key = re.sub(r"\s+", "", key) if isinstance(key, str) else key
            # 递归清理值
            cleaned[clean_key] = _clean_dict_keys(value)
        return cleaned
    elif isinstance(obj, list):
        # 递归清理列表中的每个元素
        return [_clean_dict_keys(item) for item in obj]
    else:
        # 基本类型直接返回
        return obj

def postprocess_chapter1_data(
    data: Dict[str, Any],
    sale_province: str = "",
    province_sales_count: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    处理第1章节数据

    :param data: 第1章节原始数据，格式如：
        {
            'code': 1,
            'message': 'success',
            'data': {
                '月份': '202601',
                '部门编码': 'L11001A',
                ...
                '章节数据': [
                    {
                        '指标名称': '利润排名',
                        '指标路径': '...',
                        '指标数据': {...}
                    },
                    ...
                ]
            },
            'timestamp': ...,
            'executeTime': ...
        }
    :param sale_province: 销售所属省区
    :param province_sales_count: 省份销售人员数量字典，用于计算省份排名
    :return: 处理后的数据，只包含 data 字段的内容
    """
    if province_sales_count is None:
        province_sales_count = {}
    # 如果数据有错误，直接返回
    if isinstance(data, dict) and "error" in data:
        return data
    
    # 只保留'data'键的值
    if not isinstance(data, dict) or "data" not in data:
        return data
    
    # 用于存储新的/处理之后的数据
    processed_data: Dict[str, Any] = {}
    unqualified_project_loss_score: Dict[str, Any] = {} # 未达百绩效项目扣分
    achievement_score: Dict[str, Any] = {} # 达成率（项目实际值/目标值，而非项目分数/目标分数）

    chapter_data: List[Dict[str, Any]] = data['data']['章节数据']

    # 提取未达百绩效项目扣分
    for indicator in chapter_data:
        indicator_name = indicator['指标名称']
        indicator_path = indicator['指标路径']
        indicator_data: Dict[str, Any] = indicator['指标数据']
        if "未达百绩效项目_扣分" in indicator_path:
            unqualified_project_loss_score[indicator_name] = {
                "扣分值": indicator_data["实际值"]
            }
        elif "薪资绩效分析-考核指标" in indicator_path:
            achievement_score[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "目标值": indicator_data["目标值"],
                "达成率": indicator_data["达成率"]
            }
            
    # 处理其他数据
    for indicator in chapter_data:
        indicator_name = indicator['指标名称']
        indicator_path = indicator['指标路径']
        indicator_data: Dict[str, Any] = indicator['指标数据']
        # 剔除排名数据中冗余字段
        if indicator_name in ["利润排名", "销量排名"]:
            processed_data[indicator_name] = {
                "省区排名": indicator_data["省区排名"]
            }

        elif indicator_name in ['绩效总分']:
            processed_data[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "目标值": indicator_data["目标值"],
                "单位": indicator_data["单位"],
                "扣分值": indicator_data["扣分值"],
                "达成率": indicator_data["达成率"],
                "省区排名": indicator_data["省区排名"]
            }

        else:
            if "未达百绩效项目" in indicator_path and "未达百绩效项目_扣分" not in indicator_path:
                processed_data[indicator_name] = {
                    "指标性质": "未达百绩效项目",
                    "月均得分": round(float(indicator_data["实际值"]), 2),
                    "单位": indicator_data["单位"],
                    "目标值": indicator_data["目标值"],
                    "全年总扣分值": round(float(unqualified_project_loss_score[indicator_name]["扣分值"]), 2)
                }
                if indicator_name in achievement_score:
                    processed_data[indicator_name]["达成率"] = round(float(achievement_score[indicator_name]["达成率"]), 2)
                else:
                    processed_data[indicator_name]["达成率"] = "暂无数据"

    # 添加省份销售人员数量
    if sale_province and province_sales_count:
        processed_data["销售所属省区销售总人数"] = province_sales_count.get(sale_province, "无")

    return processed_data

def postprocess_chapter2_data(
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    处理第2章节数据
    :param data: 第2章节原始数据
    :return: 处理后的数据
    """
    # 如果数据有错误，直接返回
    if isinstance(data, dict) and "error" in data:
        return data
    
    # 只保留'data'键的值
    if not isinstance(data, dict) or "data" not in data:
        return data
    
    # 用于存储新的/处理之后的数据
    processed_data: Dict[str, Any] = {}
    channel_data: Dict[str, Any] = {}   # 渠道数据
    product_data: Dict[str, Any] = {}   # 产品数据
    customer_data: Dict[str, Any] = {}   # 客户数据
    income_data: Dict[str, Any] = {}   # 收入数据
    sales_volume_data: Dict[str, Any] = {}   # 销售量数据
    chapter_data: List[Dict[str, Any]] = data['data']['章节数据']
    for indicator in chapter_data:
        indicator_name = indicator['指标名称']
        indicator_path = indicator['指标路径']
        indicator_data: Dict[str, Any] = indicator['指标数据']
        
        if "各渠道收入" in indicator_path and "各渠道收入占比" not in indicator_path:
            channel_data[f"{indicator_name}收入"] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }

        elif "高值品" in indicator_path:
            product_data[f"{indicator_name}收入"] = {
                "实际值": indicator_data["实际值"],
                "目标值": indicator_data["目标值"],
                "达成率": indicator_data["达成率"],
                "单位": indicator_data["单位"]
            }

        elif "各产品的收入" in indicator_path:
            product_data[f"{indicator_name}产品收入"] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }
        
        elif "客户数" in indicator_name or "客均收入" in indicator_name:
            customer_data[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }

        elif "销售量" in indicator_path:
            sales_volume_data[f"{indicator_name}销售量"] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }

        elif indicator_name == "收入":
            income_data[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "目标值": indicator_data["目标值"],
                "达成率": indicator_data["达成率"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }

    processed_data = {
        "收入数据": income_data,
        "渠道数据": channel_data,
        "产品收入数据": product_data,
        "客户数据": customer_data,
        "销售量数据": sales_volume_data,
    }

    return processed_data

def postprocess_chapter3_data(
    data: Dict[str, Any],
    sale_province: str = "",
    province_sales_count: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    处理第3章节数据
    :param data: 第3章节原始数据
    :param sale_province: 销售所属省区
    :param province_sales_count: 省份销售人员数量字典，用于计算省份排名
    :return: 处理后的数据
    """
    if province_sales_count is None:
        province_sales_count = {}
    # 如果数据有错误，直接返回
    if isinstance(data, dict) and "error" in data:
        return data
    
    # 只保留'data'键的值
    if not isinstance(data, dict) or "data" not in data:
        return data
    
    # 用于存储新的/处理之后的数据
    processed_data: Dict[str, Any] = {}
    # 产品均价数据
    product_price_data: Dict[str, Any] = {}
    # 产品收入占比数据
    product_income_ratio_data: Dict[str, Any] = {}
    # 产品均价趋势数据
    product_avg_price_trend_data: Dict[str, Any] = {}
    # 产品收入占比排名数据
    product_income_ratio_rank_data: Dict[str, Any] = {}
    # 均价下降产品中收入占比前三的产品
    top3_falling_price_products: List[str] = []

    chapter_data: List[Dict[str, Any]] = data['data']['章节数据']
    for indicator in chapter_data:
        indicator_name = indicator['指标名称']
        indicator_path = indicator['指标路径']
        indicator_data: Dict[str, Any] = indicator['指标数据']
        
        if "各产品的均价" in indicator_path:
            product_price_data[f"{indicator_name}均价"] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }
        
        if "各产品的收入占比" in indicator_path:
            product_income_ratio_data[f"{indicator_name}收入占比"] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }
        
        if "排名" in indicator_path:
            if indicator_name == "毛利率排名":
                processed_data[indicator_name] = {
                    "省区排名": indicator_data["省区排名"],
                    "毛利率": round(float(indicator_data["实际值"]), 1)
                }

            elif indicator_name == "高值品收入占比排名":
                processed_data[indicator_name] = {
                    "省区排名": indicator_data["省区排名"],
                    "高值品收入占比": round(float(indicator_data["实际值"]), 1)
                }

            elif indicator_name == "艺术漆收入占比排名":
                processed_data[indicator_name] = {
                    "省区排名": indicator_data["省区排名"],
                    "艺术漆收入占比": round(float(indicator_data["实际值"]), 1)
                }
        
        if "一季度各产品的均价" in indicator_path:
            product_avg_price_trend_data[indicator_name] = {
                "2025年一季度均价": indicator_data["实际值"],
                "单位": indicator_data["单位"]
            }
        
        if "二季度各产品的均价" in indicator_path:
            if indicator_name in product_avg_price_trend_data:
                product_avg_price_trend_data[indicator_name].update({
                    "2025年二季度均价": indicator_data["实际值"],
                    "单位": indicator_data["单位"]
                })
            else:
                product_avg_price_trend_data[indicator_name] = {
                    "2025年二季度均价": indicator_data["实际值"],
                    "单位": indicator_data["单位"]
                }

        if "三季度各产品的均价" in indicator_path:
            if indicator_name in product_avg_price_trend_data:
                product_avg_price_trend_data[indicator_name].update({
                    "2025年三季度均价": indicator_data["实际值"],
                    "单位": indicator_data["单位"]
                })
            else:
                product_avg_price_trend_data[indicator_name] = {
                    "2025年三季度均价": indicator_data["实际值"],
                    "单位": indicator_data["单位"]
                }
        
        if "四季度各产品的均价" in indicator_path:
            if indicator_name in product_avg_price_trend_data:
                product_avg_price_trend_data[indicator_name].update({
                    "2025年四季度均价": indicator_data["实际值"],
                    "单位": indicator_data["单位"]
                })
            else:
                product_avg_price_trend_data[indicator_name] = {
                    "2025年四季度均价": indicator_data["实际值"],
                    "单位": indicator_data["单位"]
                }

    # 生成产品收入占比排名数据
    # 按"实际值"从高到低排序
    if product_income_ratio_data:
        # 提取产品名称和收入占比，转换为列表排序
        income_ratio_list = []
        for key, value in product_income_ratio_data.items():
            # 提取产品名称
            product_name = key.replace("收入占比", "")
            # 获取实际值，转换为float
            actual_value = float(value["实际值"])
            income_ratio_list.append({
                "product_name": product_name,
                "income_ratio": actual_value
            })

        income_ratio_list.sort(key=lambda x: x["income_ratio"], reverse=True)

        # 生成排名数据（处理并列排名）
        for i, item in enumerate(income_ratio_list, 1):
            product_income_ratio_rank_data[i] = item["product_name"]

    # 筛选"均价下降产品中收入占比前三的产品"
    # 1. 找出所有均价同比下降的产品（实际值 < 同期数）
    falling_price_products = []
    for key, value in product_price_data.items():
        actual_value = float(value["实际值"])
        same_period_value = float(value["同期数"])
        # 均价同比下降
        if actual_value < same_period_value:
            # 提取产品名称（去掉"均价"后缀）
            product_name = key.replace("均价", "")
            falling_price_products.append(product_name)

    # 2. 在均价下降的产品中，按收入占比排序，取前三
    if falling_price_products and product_income_ratio_data:
        # 构建均价下降产品的收入占比列表
        falling_income_list = []
        for product_name in falling_price_products:
            # 在收入占比数据中查找对应产品
            income_key = f"{product_name}收入占比"
            if income_key in product_income_ratio_data:
                income_value = float(product_income_ratio_data[income_key]["实际值"])
                falling_income_list.append({
                    "product_name": product_name,
                    "income_ratio": income_value
                })

        # 按收入占比从高到低排序
        falling_income_list.sort(key=lambda x: x["income_ratio"], reverse=True)

        # 取前三名（或更少，如果均价下降产品不足3个）
        top3_falling_price_products = [
            item["product_name"] for item in falling_income_list[:3]
        ]

    processed_data = {
        "指标排名": processed_data,
        "各产品的均价": product_price_data,
        "各产品的收入占比": product_income_ratio_data,
        "各产品收入占比排名": product_income_ratio_rank_data,
        "均价下降产品中收入占比前三产品": top3_falling_price_products,
        "各产品过去季度均价": product_avg_price_trend_data
    }

    # 添加省份销售人员数量
    if sale_province and province_sales_count:
        processed_data["销售所属省区销售总人数"] = province_sales_count.get(sale_province, "无")

    return processed_data

def postprocess_chapter4_data(
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    处理第4章节数据
    :param data: 第4章节原始数据
    :return: 处理后的数据
    """
    # 如果数据有错误，直接返回
    if isinstance(data, dict) and "error" in data:
        return data
    
    # 只保留'data'键的值
    if not isinstance(data, dict) or "data" not in data:
        return data
    
    # 用于存储新的/处理之后的数据
    processed_data: Dict[str, Any] = {}
    processed_indicator_data: Dict[str, Any] = {}
    travel_expense_data: Dict[str, Any] = {}
    receivable_data: Dict[str, Any] = {}
    chapter_data: List[Dict[str, Any]] = data['data']['章节数据']
    for indicator in chapter_data:
        indicator_name = indicator['指标名称']
        indicator_path = indicator['指标路径']
        indicator_data: Dict[str, Any] = indicator['指标数据']

        if "差旅费" in indicator_path:
            processed_indicator_data: Dict[str, Any] = {
                "实际值": indicator_data["实际值"],
                "同期数": indicator_data["同期数"],
                "单位": indicator_data["单位"]
            }
            travel_expense_data[indicator_name] = processed_indicator_data
        else:
            processed_indicator_data: Dict[str, Any] = {
                "实际值": indicator_data["实际值"],
                "单位": indicator_data["单位"]
            }
            receivable_data[indicator_name] = processed_indicator_data

    daily_travel_expense = float(travel_expense_data["其他费用/天"]['实际值']) + float(travel_expense_data["住宿费/天"]['实际值']) + float(travel_expense_data["车辆费/天"]['实际值']) + float(travel_expense_data["交通费/天"]['实际值'])
    travel_expense_data['每日花费金额（差旅费）'] = {
        "实际值": round(daily_travel_expense, 1),
        "单位": "元"
    }

    processed_data = {
        "与人相关费用数据": travel_expense_data,
        "应收账款数据": receivable_data,
    }
    return processed_data

def postprocess_chapter5_data(
    data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    处理第5章节数据
    :param data: 第5章节原始数据
    :return: 处理后的数据
    """
    # 如果数据有错误，直接返回
    if isinstance(data, dict) and "error" in data:
        return data
    
    # 只保留'data'键的值
    if not isinstance(data, dict) or "data" not in data:
        return data
    
    # 用于存储新的/处理之后的数据
    processed_data: Dict[str, Any] = {}
    visit_count_data: Dict[str, Any] = {}
    visit_time_allocation_data: Dict[str, Any] = {}

    chapter_data: List[Dict[str, Any]] = data['data']['章节数据']
    for indicator in chapter_data:
        indicator_name = indicator['指标名称']
        indicator_path = indicator['指标路径']
        indicator_data: Dict[str, Any] = indicator['指标数据']

        if "月有效拜访量" in indicator_path:
            visit_count_data[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "单位": indicator_data["单位"]
            }
        elif "时间分配" in indicator_path:
            visit_time_allocation_data[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "单位": indicator_data["单位"]
            }
        elif "网点拜访率" in indicator_path:
            processed_data[indicator_name] = {
                "实际值": indicator_data["实际值"],
                "单位": indicator_data["单位"]
            }

    processed_data.update({
        "月有效拜访量数据": visit_count_data,
        "拜访时间分配数据": visit_time_allocation_data,
    })
    return processed_data

def postproces_chapter_data(
    module: int,
    data: Dict[str, Any],
    sale_province: str = "",
    province_sales_count: Dict[str, int] = None
) -> Dict[str, Any]:
    """
    第一次数据处理，用于处理章节数据
    :param module: 模块编号, 如1、2、3、4、5
    :param data: 每章节原始数据
    :param sale_province: 销售所属省区
    :param province_sales_count: 省份销售人员数量字典
    :return: 处理后的数据
    """
    if province_sales_count is None:
        province_sales_count = {}

    if module == 1:
        return postprocess_chapter1_data(data, sale_province, province_sales_count)
    elif module == 2:
        return postprocess_chapter2_data(data)
    elif module == 3:
        return postprocess_chapter3_data(data, sale_province, province_sales_count)
    elif module == 4:
        return postprocess_chapter4_data(data)
    elif module == 5:
        return postprocess_chapter5_data(data)
    else:
        raise ValueError(f"Invalid module argument: {module}")
        
def postprocess_data(
    raw_data: Dict[int, Dict[str, Any]],
    sale_province: str,
    province_sales_count: Dict[str, int]
) -> Dict[int, Any]:
    """
    数据后处理
    :param raw_data: 原始数据
    :param sale_province: 销售所属省区
    :param province_sales_count: 省份销售人员数量，用于计算省份排名，格式为 {"省份": 销售人员数量}，如 {"湖北省区": 100}
    :return: 处理后的数据
    """
    # 一次性清理所有原始数据中的键名空白字符（兼容API返回数据中键名可能包含多余空白的问题）
    cleaned_raw_data = {i: _clean_dict_keys(data) for i, data in raw_data.items()}

    processed_data = {}
    for i, data in cleaned_raw_data.items():
        # 剔除冗余数据并处理数据（省份销售人数已在内部处理）
        processed_chapter_data = postproces_chapter_data(
            i, data, sale_province, province_sales_count
        )
        processed_data[i] = processed_chapter_data

    return processed_data

if __name__ == "__main__":
    data = {'code': 1, 'message': 'success', 'data': {'月份': '202601', '部门编码': 'L11001A', '区域经理工号': '00165', '部门名称': '马上住焕新事业部', '区域经理姓名': '柳家华', '岗位名称': '传统经营导师', '章节名称': '一、薪资绩效分析', '章节数据': [{'指标名称': '高值品销量', '指标路径': '一、薪资绩效分析-未达百绩效项目-高值品销量', '指标数据': {'实际值': '6.800', '目标值': 10.0, '同期数': 0.0, '扣分值': 3.2, '达成率': '0.680', '权重分数': '10.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部 门排名': 0}}, {'指标名称': '高值品销量', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-高值品销量', '指标数据': {'实际值': '35.240', '目标值': 110.0, '同期数': 0.0, '扣分值': 74.76, '达成率': '0.320', '权重分数': '110.000', '单位': '分', '分 部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '艺术漆销量', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-艺术漆销量', '指标数据': {'实际值': '46.170', '目标值': 110.0, '同期数': 0.0, '扣分值': 63.83, '达成率': '0.420', '权重分数': '110.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '艺术漆销量', '指标路径': '一、薪资绩效分析-未达百绩效项目-艺术漆销量', '指标数据': {'实际值': '5.800', '目标值': 10.0, '同期数': 0.0, '扣分值': 4.2, '达成率': '0.580', '权重分数': '10.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '马上住建店', '指标路径': '一、薪资绩效分析-未达百绩效项目-马上住建店', '指标数据': {'实际值': '8.600', '目标值': 11.36, '同期数': 0.0, '扣分值': 2.76, '达成率': '0.757', '权重分数': '11.360', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '网点', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-网点', '指标数据': {'实际值': '48.900', '目标值': 110.0, '同期数': 0.0, '扣分值': 61.1, '达成率': '0.445', '权重分数': '110.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '马上住建店', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-马上住建店', '指标数据': {'实际值': '30.370', '目标值': 125.0, '同期数': 0.0, '扣分值': 94.63, '达成率': '0.243', '权重分数': '125.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '招商', '指标路径': '一、薪资绩效分析-未达百绩效项目-招商', '指标数据': {'实际值': '5.250', '目标值': 10.0, '同期数': 0.0, '扣分值': 4.75, '达成率': '0.525', '权重分数': '10.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '网点', '指标路径': '一、薪资绩效分析-未达百绩效项目-网点', '指标数据': {'实际值': '5.550', '目标值': 10.0, '同期数': 0.0, '扣分值': 4.45, '达成率': '0.555', '权重分数': '10.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '招商', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-招商', '指标数据': {'实际值': '52.200', '目标值': 110.0, '同期数': 0.0, '扣分值': 57.8, '达成率': '0.475', '权重分数': '110.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '马上住签单达成率', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-马上住签单达成率', '指标数据': {'实际值': '15.700', '目标值': 80.0, '同期数': 0.0, '扣分值': 64.3, '达成率': '0.196', '权重分数': '80.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '马上住签单达成率', '指标路径': '一、薪资绩效分析-未达百绩效项目-马上住签单达成率', '指标数据': {'实际值': '8.040', '目标值': 10.0, '同期数': 0.0, '扣分值': 1.96, '达成率': '0.804', '权重分数': '10.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '马上住总销量', '指标路径': '一、薪资绩效分析-未达百绩效项目-马上住总销量', '指标数据': {'实际值': '7.290', '目标值': 11.36, '同期数': 0.0, '扣分值': 4.07, '达成率': '0.642', '权重分数': '11.360', '单位': '分', '分部 排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '马上住总销量', '指标路径': '一、薪资绩效分析-未达百绩效项目_扣分-马上住总销量', '指标数据': {'实际值': '44.760', '目标值': 125.0, '同期数': 0.0, '扣分值': 80.24, '达成率': '0.358', '权重分数': '125.000', '单位': '分', '分部排名': 0, '省区排名': 0, '部门排名': 0}}, {'指标名称': '利润排名', '指标路径': '一、薪资绩效分析-利润排名', '指标数据': {'实际值': '-474370.840', '目标值': 0.0, '同期数': 0.0, '扣分值': 474370.84, '达成率': '0.000', '权重分数': '0.000', '单位': '', '分部排名': 9, '省区排名': 14, '部门排名': 404}}, {'指标名称': '销量排名', '指标路径': '一、薪资绩效分析-销量排名', '指标数据': {'实际值': '3990163.860', '目标值': 4106675.22, '同期数': 0.0, '扣分值': 116511.36, '达成率': '97.000', '权重分数': '0.000', '单位': '', '分部排名': 6, '省区排名': 11, '部门排名': 228}}, {'指标名称': '绩效总分', '指标路径': '一、薪资绩效分析-绩效总分', '指标数据': {'实际值': '77.780', '目标值': 100.0, '同期数': 0.0, '扣分值': 22.22, '达成率': '0.778', '权重分数': '0.000', '单位': '分', '分部排名': 5, '省区排名': 9, '部门排名': 239}}]}, 'timestamp': 1768981395119, 'executeTime': 11}
    result = postproces_chapter_data(1, data)
    print(result)