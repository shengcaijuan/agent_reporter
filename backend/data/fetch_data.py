import aiohttp
import asyncio
import json
from typing import Optional, Dict, Any, List
from aiohttp import ClientTimeout, ClientSession

async def fetch_raw_data(
        job_id: str,        
        time: str,
        module: int,
        api_key: str = "05b65dfd5ee44f2a21f2312372b76f75",
        base_url: str = "https://apidev.skshu.com/test/skshu-bi-api/biapitoxt/getEmployeeIndexAi",
        session: Optional[ClientSession] = None,
        timeout: int = 15
) -> Dict[str, Any]:
    """
    获取员工指标数据

    :param job_id: 销售工号
    :param time: 计算月份 (CALMONTH)，格式为 YYYYMM
    :param module: 模块标识 (MOUDLE)，如1、2、3、4、5
    :param api_key: API密钥，默认已提供
    :param base_url: 接口基础URL，默认已提供
    :param session: 可选的 aiohttp ClientSession，用于复用连接
    :param timeout: 请求超时时间（秒），默认15秒
    :return: 返回API响应的JSON数据或错误信息
    """

    # 构造完整URL
    full_url = f"{base_url}?apikey={api_key}"

    # 请求体
    request_body = {
        "ZEMPLOYEE": job_id,
        "CALMONTH": time,
        "MOUDLE": str(module)
    }

    # 请求头
    headers = {
        "Content-Type": "application/json"
    }

    # 是否由外部管理 session（用于批量请求时复用连接）
    should_close_session = session is None
    if session is None:
        session = ClientSession()

    try:
        async with session.post(
            url=full_url,
            json=request_body,
            headers=headers,
            timeout=ClientTimeout(total=timeout),
            ssl=False  # 注：生产环境开启SSL验证, 设置为True
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
        concurrent_limit: int = 5
) -> Dict[int, Dict[str, Any]]:
    """批量获取原始数据（复用同一个 ClientSession 提高性能）

    :param requests: 请求列表，每个元素包含 job_id, time, module
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