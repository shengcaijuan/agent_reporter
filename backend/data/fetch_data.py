import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any, List
from aiohttp import ClientTimeout, ClientSession

# 默认配置（向后兼容）
DEFAULT_API_KEY = "data_api_key"
DEFAULT_BASE_URL = "data_api_url"


async def fetch_raw_data(
        job_id: str,
        time: str,
        module: int,
        data_source_config: Optional[Dict[str, Any]] = None,
        api_key: str = DEFAULT_API_KEY,
        base_url: str = DEFAULT_BASE_URL,
        session: Optional[ClientSession] = None,
        timeout: int = 15
) -> Dict[str, Any]:
    """
    获取员工指标数据（支持动态数据源配置）

    :param job_id: 销售工号
    :param time: 计算月份 (CALMONTH)，格式为 YYYYMM
    :param module: 模块标识 (MOUDLE)，如1、2、3、4、5
    :param data_source_config: 数据源配置（优先使用），包含:
        - config: {base_url, api_key, auth_type, auth_key_name, timeout, ssl_verify}
        - request_params: {job_id_field, time_field, module_field}
    :param api_key: API密钥（向后兼容，当未提供data_source_config时使用）
    :param base_url: 接口基础URL（向后兼容）
    :param session: 可选的 aiohttp ClientSession，用于复用连接
    :param timeout: 请求超时时间（秒），默认15秒
    :return: 返回API响应的JSON数据或错误信息
    """

    # 从数据源配置获取参数（如果提供）
    if data_source_config:
        config = data_source_config.get("config", {})
        params = data_source_config.get("request_params", {})

        actual_base_url = config.get("base_url", base_url)
        actual_api_key = config.get("api_key", api_key)
        actual_timeout = config.get("timeout", timeout)
        ssl_verify = config.get("ssl_verify", False)

        # 获取请求参数字段名
        job_id_field = params.get("job_id_field", "ZEMPLOYEE")
        time_field = params.get("time_field", "CALMONTH")
        module_field = params.get("module_field", "MOUDLE")

        # 获取认证方式
        auth_type = config.get("auth_type", "url_param")
        auth_key_name = config.get("auth_key_name", "apikey")
    else:
        actual_base_url = base_url
        actual_api_key = api_key
        actual_timeout = timeout
        ssl_verify = False
        job_id_field = "ZEMPLOYEE"
        time_field = "CALMONTH"
        module_field = "MOUDLE"
        auth_type = "url_param"
        auth_key_name = "apikey"

    # 构建完整URL（根据认证方式）
    if auth_type == "url_param":
        full_url = f"{actual_base_url}?{auth_key_name}={actual_api_key}"
    else:
        full_url = actual_base_url

    # 请求体
    request_body = {
        job_id_field: job_id,
        time_field: time,
        module_field: str(module)
    }

    # 请求头
    headers = {"Content-Type": "application/json"}
    if auth_type == "header":
        headers[auth_key_name] = actual_api_key
    elif auth_type == "bearer":
        headers["Authorization"] = f"Bearer {actual_api_key}"

    # 是否由外部管理 session（用于批量请求时复用连接）
    should_close_session = session is None
    if session is None:
        session = ClientSession()

    try:
        async with session.post(
            url=full_url,
            json=request_body,
            headers=headers,
            timeout=ClientTimeout(total=actual_timeout),
            ssl=ssl_verify
        ) as response:

            # 解析JSON响应
            result = await response.json()
            return result

    except asyncio.TimeoutError:
        return {"error": "timeout", "message": "Request timed out"}
    except aiohttp.ClientError as e:
        return {"error": "connection_error", "message": str(e)}
    except json.JSONDecodeError as e:
        return {"error": "json_decode_error", "message": f"Invalid JSON response: {str(e)}"}
    except Exception as e:
        return {"error": "unknown_error", "message": str(e)}
    finally:
        # 如果 session 是内部创建则关闭
        if should_close_session:
            await session.close()

async def fetch_raw_data_batch(
        requests: List[Dict[str, Any]],
        data_source_config: Optional[Dict[str, Any]] = None,
        concurrent_limit: int = 5
) -> Dict[int, Dict[str, Any]]:
    """批量获取原始数据（支持动态数据源配置）

    :param requests: 请求列表，每个元素包含 job_id, time, module
    :param data_source_config: 数据源配置
    :param concurrent_limit: 并发限制，默认5
    :return: 返回响应列表
        数据异常（空白）返回：{
            "error": "data_blank",
            "message": "数据为空",
            "sale_id": job_id,
            "data": result
        }

        数据异常（其他）返回：{
            "error": "api_error",
            "status": response.status,
            "message": error_text,
            "sale_id": job_id
        }
    """
    semaphore = asyncio.Semaphore(concurrent_limit)

    async def _fetch_with_semaphore(req: Dict[str, Any], session: ClientSession) -> Dict[str, Any]:
        async with semaphore:
            return await fetch_raw_data(
                job_id=req["job_id"],
                time=req["time"],
                module=req["module"],
                data_source_config=data_source_config,
                session=session
            )

    async with ClientSession() as session:
        tasks = [_fetch_with_semaphore(req, session) for req in requests]
        results = await asyncio.gather(*tasks)
        return {
            i: result for i, result in enumerate(results, 1)
        }


if __name__ == "__main__":
    async def main():
        """# 方式1：单独请求（向后兼容原有用法）
        print("=== 单独请求示例 ===")
        start_time = time.time()
        for i in ["1", "2", "3", "4", "5"]:
            result = await fetch_data(employee_id="04490", time="202601", module=i)
            print(f"第 {i} 章节数据: \n{result}\n")
        end_time = time.time()
        print(f"单独请求时间: {end_time - start_time} 秒")
        # 方式2：批量请求
        print("\n=== 批量请求示例 ===")
        start_time = time.time()
        batch_requests = [
            {"job_id": "00165", "province": "湖北省区", "time": "202601", "module": i} # 105758 00165
            for i in [1, 2, 3, 4, 5]
        ]
        batch_results = await fetch_data_batch(
            requests=batch_requests,
            province_sales_count=province_sales_count,
            concurrent_limit=3
            )
        for i, result in enumerate(batch_results, 1):
            print(f"第 {i} 章节处理后数据: \n{result}\n")
        end_time = time.time()  
        print(f"批量请求时间: {end_time - start_time} 秒")"""

        for i in [1, 2, 3, 4, 5]:
            result = await fetch_raw_data(job_id="00165", time="202601", module=i)
            print(f"type(result): {type(result)}")
            print(f"第 {i} 章节原始数据: \n{result}\n")

    asyncio.run(main())
