import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any, List, Union
from aiohttp import ClientTimeout, ClientSession

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

if __name__ == "__main__":
    async def main():
        fetcher = SalesConigFetcher()
        all_sales_config = await fetcher.fetch_all_sales_config()
        print("="*60)
        print(f"销售人员数量: {len(all_sales_config)}")
        print("="*60)
        province_sales_count = await fetcher.count_province_sales()
        print(f"省份销售数量: {province_sales_count}")
        print("="*60)
    asyncio.run(main())