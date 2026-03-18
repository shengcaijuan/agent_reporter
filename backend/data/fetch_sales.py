import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any, List, Union
from aiohttp import ClientTimeout, ClientSession
from pathlib import Path
from datetime import datetime

# API 字段名到内部键名的映射
FIELD_MAPPING: Dict[str, str] = {
    "CALMONTH": "calmonth",
    "ZEMPLOYEE": "job_id",
    "ZEMP_CD": "sale_name",
    "ZGWMC": "sale_class",
    "ZORGWB6": "city_operation_department",
    "ZORGWB5": "province",
    "ZORGWB4": "region",
    "ZORGWB3": "business_department",
}

class SalesConigFetcher:
    def __init__(
        self, 
        session: Optional[ClientSession] = None,
        timeout: int = 15
        ):
        self.session = session
        self.timeout = timeout
        
        # 缓存字典：使用 job_id 作为键
        self._sales_config_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """转换单条记录的键名，将 API 字段映射为内部字段"""
        return {FIELD_MAPPING.get(k, k): v for k, v in record.items()}

    async def fetch_all_sales_config(self) -> Union[List[Dict], Dict]:
        """
        获取销售人员组织结构信息
        return: 
        List[Dict[str, Any]]
        [
            {
                "time": "202601", //月份
                "job_id": "86001087", //工号
                "sale_name": "谢虎生", //姓名
                "sale_class": "传统经营导师", //岗位名称
                "city_operation_department": "西南大区办公室", //分部
                "province": "西南大区办公室", //省区
                "region": "西南大区", //大区
                "business_department": "马上住焕新事业部" //事业部
            },
            ...
        ]
        # 抓取的原始数据:
        {
            "code": int,
            "message": str,
            "data": [
                {
                    "time": "202601", //月份
                    "job_id": "86001087", //工号
                    "sale_name": "谢虎生", //姓名
                    "sale_class": "传统经营导师", //岗位名称
                    "city_operation_department": "西南大区办公室", //分部
                    "province": "西南大区办公室", //省区
                    "region": "西南大区", //大区
                    "business_department": "马上住焕新事业部" //事业部
                }
            ],
            "timestamp": 1768209953488,
            "executeTime": 89,
        }
        """

        post = "https://apidev.skshu.com/test/skshu-bi-api/biapitoxt/getAiEmployeeOrg?apikey=05b65dfd5ee44f2a21f2312372b76f75"

        headers = {
            "Content-Type": "application/json"
        }

        # 是否由外部管理 session（用于批量请求时复用连接）
        # 检查session是否已关闭
        if self.session is None or self.session.closed:
            should_close_session = True
            self.session = ClientSession()
        else:
            should_close_session = False

        try:
            async with self.session.post(
                url=post,
                json=None,
                headers=headers,
                timeout=ClientTimeout(total=self.timeout),
                ssl=False  # 注：生产环境开启SSL验证, 设置为True
            ) as response:
                # 检查HTTP状态码
                if response.status != 200:
                    error_text = await response.text()
                    return {
                        "error": "http_error",
                        "status": response.status,
                        "message": error_text
                    }

                # 解析JSON响应
                result = await response.json()

                # 检查响应格式是否正确
                if not isinstance(result, dict):
                    return {"error": "invalid_response", "message": "API返回格式错误：响应不是字典类型"}

                if "data" not in result:
                    return {"error": "invalid_response", "message": f"API返回格式错误：缺少data字段，返回内容：{result}"}

                if not isinstance(result["data"], list):
                    return {"error": "invalid_response", "message": f"API返回格式错误：data不是列表类型，实际类型：{type(result['data']).__name__}"}

                # 转换 data 中的字段名
                result["data"] = [self._transform_record(item) for item in result["data"]]

                return result["data"]

        except asyncio.TimeoutError:
            return {"error": "timeout", "message": "Request timed out"}
        except aiohttp.ClientError as e:
            return {"error": "connection_error", "message": str(e)}
        except json.JSONDecodeError as e:
            return {"error": "json_decode_error", "message": f"Invalid JSON response: {str(e)}"}
        except Exception as e:
            return {"error": "unknown_error", "message": str(e)}
        finally:
            # 如果 session 是内部创建的，则关闭它
            if should_close_session:
                await self.session.close()
                self.session = None  # 关闭后设置为None，避免后续使用已关闭的session

    def _build_sales_config_dict(
        self, 
        all_sales_config: List[Dict[str, Any]]
        ) -> Dict[str, Dict[str, Any]]:
        """
        构建销售人员配置字典，使用 job_id 作为键
        """
        return {
            sale_config["job_id"]: sale_config
            for sale_config in all_sales_config
            if isinstance(sale_config, dict) and "job_id" in sale_config
        }

    async def fetch_sale_config(
        self,
        job_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        获取单个销售人员配置
        
        Args:
            job_id: 销售工号
            sale_name: 销售姓名
            
        Returns:
            Dict[str, Any]: 销售人员配置，如果未找到返回 None
        """
        # 如果缓存为空，先获取所有数据并构建字典
        if self._sales_config_cache is None:
            all_sales_config = await self.fetch_all_sales_config()
            # 检查返回的是否是错误信息
            if isinstance(all_sales_config, dict) and "error" in all_sales_config:
                return None
            # 确保是列表类型
            if not isinstance(all_sales_config, list):
                return None
            self._sales_config_cache = self._build_sales_config_dict(all_sales_config)
        
        return self._sales_config_cache.get(job_id)
    
    def clear_cache(self):
        """清除缓存，强制下次调用时重新获取数据"""
        self._sales_config_cache = None

    async def count_province_sales(self) -> Dict[str, Any]:
        """
        统计销售配置中的省份信息和每个省份的销售数量
        
        Returns:
            Dict[str, int]
            Example:
                {
                    "西南大区办公室": 10,
                    "华东大区办公室": 15,
                    "华北大区办公室": 8
                }
        """
        # 优先使用缓存数据，避免重复请求
        if self._sales_config_cache is None:
            sales_config = await self.fetch_all_sales_config()
        else:
            # 从缓存中获取数据
            sales_config = list(self._sales_config_cache.values())
        # 检查是否错误响应
        if isinstance(sales_config, dict) and "error" in sales_config:
            return {
                "error": sales_config.get("error"),
                "message": sales_config.get("message", "获取销售配置失败")
            }

        # 确保是列表类型
        if not isinstance(sales_config, list):
            return {
                "error": "invalid_data",
                "message": "销售配置数据格式不正确"
            }

        # 统计每个省份的销售数量
        province_sales_count: Dict[str, int] = {}
        
        for sale_config in sales_config:
            if not isinstance(sale_config, dict):
                continue
            
            province = sale_config.get("province")
            if province:
                # 统计每个省份的销售数量
                province_sales_count[province] = province_sales_count.get(province, 0) + 1
        
        return province_sales_count

    async def update_sales_config_file(
        self,
        config_file_path: str,
        task_id: str = "mashangzhu",
        task_name: str = "马上住焕新事业部销售报告",
        description: str = "马上住焕新事业部销售人员月度分析报告生成任务的销售名单"
    ) -> Dict[str, Any]:
        """
        更新销售配置文件，获取最新的销售名单并统计省份销售人员数量

        Args:
            config_file_path: 配置文件路径
            task_id: 任务ID
            task_name: 任务名称
            description: 任务描述

        Returns:
            Dict[str, Any]: 更新结果，包含成功/失败信息和统计数据
        """
        # 1. 获取最新的销售名单
        all_sales_config = await self.fetch_all_sales_config()

        # 检查是否获取成功
        if isinstance(all_sales_config, dict) and "error" in all_sales_config:
            return {
                "success": False,
                "error": all_sales_config.get("error"),
                "message": all_sales_config.get("message", "获取销售配置失败")
            }

        if not isinstance(all_sales_config, list):
            return {
                "success": False,
                "error": "invalid_data",
                "message": "销售配置数据格式不正确"
            }

        # 2. 统计各省份销售人员数量
        province_sales_count: Dict[str, int] = {}
        for sale_config in all_sales_config:
            if not isinstance(sale_config, dict):
                continue
            province = sale_config.get("province")
            if province:
                province_sales_count[province] = province_sales_count.get(province, 0) + 1

        # 3. 准备要保存的数据
        config_data = {
            "task_id": task_id,
            "task_name": task_name,
            "description": description,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "province_sales_count": province_sales_count,
            "sales": all_sales_config
        }

        # 4. 保存到配置文件
        config_path = Path(config_file_path)

        # 确保目录存在
        config_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "message": f"销售配置文件更新成功",
                "total_sales": len(all_sales_config),
                "province_count": len(province_sales_count),
                "config_file": str(config_path)
            }
        except Exception as e:
            return {
                "success": False,
                "error": "file_write_error",
                "message": f"写入配置文件失败: {str(e)}"
            }


def load_sales_config(config_file_path: str) -> Dict[str, Any]:
    """
    从配置文件加载销售配置

    Args:
        config_file_path: 配置文件路径

    Returns:
        Dict[str, Any]: 销售配置，包含 sales 列表和 province_sales_count 字典
    """
    config_path = Path(config_file_path)

    if not config_path.exists():
        return {
            "error": "file_not_found",
            "message": f"配置文件不存在: {config_file_path}"
        }

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)

        return config_data
    except json.JSONDecodeError as e:
        return {
            "error": "json_decode_error",
            "message": f"配置文件JSON解析失败: {str(e)}"
        }
    except Exception as e:
        return {
            "error": "file_read_error",
            "message": f"读取配置文件失败: {str(e)}"
        }


def get_province_sales_count(config_file_path: str) -> Dict[str, int]:
    """
    从配置文件获取省份销售人员数量

    Args:
        config_file_path: 配置文件路径

    Returns:
        Dict[str, int]: 省份销售人员数量字典，如果出错返回空字典
    """
    config_data = load_sales_config(config_file_path)

    if isinstance(config_data, dict) and "error" in config_data:
        return {}

    return config_data.get("province_sales_count", {})


def get_sales_list(config_file_path: str) -> List[Dict[str, Any]]:
    """
    从配置文件获取销售人员列表

    Args:
        config_file_path: 配置文件路径

    Returns:
        List[Dict[str, Any]]: 销售人员列表，如果出错返回空列表
    """
    config_data = load_sales_config(config_file_path)

    if isinstance(config_data, dict) and "error" in config_data:
        return []

    return config_data.get("sales", [])

# 默认配置文件路径
DEFAULT_SALES_CONFIG_PATH = "report_tasks/mashangzhu/config_files/sales/sales.json"

if __name__ == "__main__":
    async def main():
        import sys

        fetcher = SalesConigFetcher()

        # 检查是否传入命令行参数
        if len(sys.argv) > 1 and sys.argv[1] == "--update":
            # 更新模式：获取最新销售名单并更新配置文件
            print("="*60)
            print("开始更新销售配置文件...")
            print("="*60)

            # 获取配置文件路径（可选参数）
            config_path = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_SALES_CONFIG_PATH

            result = await fetcher.update_sales_config_file(config_path)

            print("="*60)
            if result.get("success"):
                print(f"更新成功!")
                print(f"  - 总销售人员数: {result.get('total_sales')}")
                print(f"  - 省份数量: {result.get('province_count')}")
                print(f"  - 配置文件: {result.get('config_file')}")
            else:
                print(f"更新失败: {result.get('error')}")
                print(f"  错误信息: {result.get('message')}")
            print("="*60)
        else:
            # 测试模式：获取并显示销售配置信息
            print("="*60)
            print("测试模式 - 获取销售配置信息")
            print("="*60)

            all_sales_config = await fetcher.fetch_all_sales_config()
            print(f"获取销售配置信息:\n{all_sales_config}")
            if isinstance(all_sales_config, dict) and "error" in all_sales_config:
                print(f"获取失败: {all_sales_config.get('error')}")
                print(f"错误信息: {all_sales_config.get('message')}")
            else:
                print(f"销售人员数量: {len(all_sales_config)}")
                print("-"*60)

                # 统计省份销售数量
                province_sales_count = await fetcher.count_province_sales()
                print("各省份销售人员数量:")
                for province, count in sorted(province_sales_count.items(), key=lambda x: x[1], reverse=True):
                    print(f"  {province}: {count}人")

            print("="*60)
            print("提示: 使用 --update 参数更新配置文件")
            print("示例: python fetch_sales.py --update")
            print("="*60)

    asyncio.run(main())