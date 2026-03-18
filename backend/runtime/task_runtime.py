"""
任务运行时加载器 - 加载任务完整配置并组装运行时环境

核心功能：
1. 从配置目录加载任务配置（JSON/Markdown）
2. 将配置转换为 Python 对象（TaskRuntime、ChapterRuntime）
3. 支持枚举类型自动转换（AttributionRelationType、ThresholdType）
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional

from tools.attribution.contribution import AttributionRelationType
from tools.attribution.threshold import ThresholdType

from runtime.config import TaskRuntime, ChapterRuntime, GuidelineConfig, WrappingRequirementsConfig


class TaskRuntimeLoader:
    """任务运行时加载器"""

    # 配置文件基础路径: report_tasks/{task_id}/config_files/
    CONFIG_BASE_PATH = Path(__file__).parent.parent / "report_tasks"

    @classmethod
    def load_task(cls, task_id: str) -> TaskRuntime:
        """
        加载任务完整配置

        Args:
            task_id: 任务ID

        Returns:
            TaskRuntime: 任务运行时配置对象
        """
        task_dir = cls.CONFIG_BASE_PATH / task_id / "config_files"

        if not task_dir.exists():
            raise FileNotFoundError(f"任务配置目录不存在: {task_dir}")

        # 1. 加载任务元数据
        task_config = cls._load_json(task_dir / "task_config.json")

        # 2. 加载报告介绍（共享前缀）
        report_intro = cls._load_markdown(task_dir / "report_intro.md")

        # 3. 加载布局要求（优先JSON，回退MD）
        lay_out_requirements = cls._load_layout_requirements(task_dir)

        # 4. 加载章节结构
        chapters_config = cls._load_json(task_dir / "chapters.json")

        # 5. 组装章节运行时配置
        chapters = []
        for ch_config in chapters_config.get("chapters", []):
            chapter_id = ch_config["chapter_id"]

            # 加载章节guideline（优先JSON，回退MD）
            guideline = cls._load_guideline(
                task_dir=task_dir,
                chapter_id=chapter_id,
                report_intro=report_intro
            )

            # 加载工具配置
            tool_configs = []
            if ch_config.get("has_tools"):
                tool_config_path = task_dir / f"tool_agent_configs/chapter{chapter_id}.json"
                if tool_config_path.exists():
                    tool_config_data = cls._load_json(tool_config_path)
                    raw_tools = tool_config_data.get("tools", [])
                    # 转换枚举类型
                    tool_configs = cls._convert_tool_configs(raw_tools)


            chapter = ChapterRuntime(
                chapter_id=chapter_id,
                chapter_name=ch_config["chapter_name"],
                chapter_type=ch_config["chapter_type"],
                has_tools=ch_config.get("has_tools", False),
                guideline=guideline,
                tool_configs=tool_configs,
                summarize_chapters=ch_config.get("summarize_chapters", [])
            )
            chapters.append(chapter)

        return TaskRuntime(
            task_id=task_id,
            task_name=task_config["task_name"],
            business_department=task_config["business_department"],
            description=task_config.get("description", ""),
            report_intro=report_intro,
            chapters=chapters,
            data_source=task_config.get("data_source", {}),
            report_structure=task_config.get("report_structure", {}),
            lay_out_requirements=lay_out_requirements
        )

    @classmethod
    def list_tasks(cls) -> List[Dict[str, Any]]:
        """列出所有可用任务"""
        index_path = cls.CONFIG_BASE_PATH / "task_index.json"

        if not index_path.exists():
            # 如果索引不存在，扫描目录
            tasks = []
            for task_dir in cls.CONFIG_BASE_PATH.iterdir():
                config_dir = task_dir / "config_files"
                if task_dir.is_dir() and config_dir.is_dir() and (config_dir / "task_config.json").exists():
                    task_config = cls._load_json(config_dir / "task_config.json")
                    tasks.append({
                        "task_id": task_dir.name,
                        "task_name": task_config.get("task_name", task_dir.name),
                        "business_department": task_config.get("business_department", ""),
                        "chapter_count": len(cls._load_json(config_dir / "chapters.json").get("chapters", [])),
                        "status": "active"
                    })
            return tasks

        index_data = cls._load_json(index_path)
        return index_data.get("tasks", [])

    @classmethod
    def task_exists(cls, task_id: str) -> bool:
        """检查任务是否存在"""
        config_dir = cls.CONFIG_BASE_PATH / task_id / "config_files"
        return config_dir.exists() and (config_dir / "task_config.json").exists()

    @classmethod
    def _convert_tool_configs(cls, raw_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        转换工具配置中的枚举类型

        Args:
            raw_configs: 原始工具配置列表

        Returns:
            转换后的配置列表
        """
        converted = []
        for config in raw_configs:
            converted_config = dict(config)
            attr_type = config.get("attr_type", "")

            if "indicators_config" in converted_config:
                converted_config["indicators_config"] = cls._convert_indicators_config(
                    attr_type,
                    converted_config["indicators_config"]
                )

            converted.append(converted_config)

        return converted

    @classmethod
    def _convert_indicators_config(
        cls,
        attr_type: str,
        indicators_config: Any
    ) -> Any:
        """
        根据归因类型转换 indicators_config 中的枚举值
        """
        if attr_type == "contribution":
            config = dict(indicators_config)
            if "relation_type" in config:
                relation_type_str = config["relation_type"]
                config["relation_type"] = AttributionRelationType(relation_type_str)
            return config

        elif attr_type == "threshold":
            config_list = []
            for item in indicators_config:
                converted_item = dict(item)
                if "threshold_type" in converted_item:
                    threshold_type_str = converted_item["threshold_type"]
                    converted_item["threshold_type"] = ThresholdType(threshold_type_str)
                config_list.append(converted_item)
            return config_list

        elif attr_type == "variation":
            return indicators_config

        else:
            return indicators_config

    @staticmethod
    def _load_json(path: Path) -> Dict[str, Any]:
        """加载JSON文件"""
        if not path.exists():
            raise FileNotFoundError(f"配置文件不存在: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    @classmethod
    def _load_guideline(
        cls,
        task_dir: Path,
        chapter_id: int,
        report_intro: str = ""
    ) -> str:
        """
        加载章节guideline（优先JSON，回退MD）

        Args:
            task_dir: 任务配置目录
            chapter_id: 章节ID
            report_intro: 报告介绍（共享前缀）

        Returns:
            完整的markdown格式guideline
        """
        # 优先尝试加载JSON格式
        json_path = task_dir / f"guidelines/chapter{chapter_id}.json"
        if json_path.exists():
            try:
                guideline_data = cls._load_json(json_path)
                guideline_config = GuidelineConfig(**guideline_data)
                # 使用GuidelineConfig.to_markdown()生成完整guideline
                return guideline_config.to_markdown(task_prefix=report_intro)
            except Exception as e:
                # JSON解析失败，尝试回退到MD
                print(f"加载guideline JSON失败 ({json_path}): {e}")

        # 回退到MD格式
        md_path = task_dir / f"guidelines/guidelines_md/chapter{chapter_id}.md"
        guideline = cls._load_markdown(md_path)

        # 拼接报告介绍
        if report_intro and guideline:
            return f"{report_intro}\n\n---\n\n{guideline}"
        return guideline

    @classmethod
    def _load_layout_requirements(cls, task_dir: Path) -> str:
        """
        加载布局要求（优先JSON，回退MD）

        Args:
            task_dir: 任务配置目录

        Returns:
            str: 布局要求的markdown格式字符串
        """
        # 优先尝试加载JSON格式
        json_path = task_dir / "wrapping/wrapping.json"
        if json_path.exists():
            try:
                layout_data = cls._load_json(json_path)
                layout_config = WrappingRequirementsConfig(**layout_data)
                return layout_config.to_markdown()
            except Exception as e:
                print(f"加载布局要求JSON失败 ({json_path}): {e}")

        # 回退到MD格式（兼容旧配置）
        md_path = task_dir / "wrapping/lay_out_requirements.md"
        md_content = cls._load_markdown(md_path)
        if md_content:
            return md_content

        return ""

    @staticmethod
    def _load_markdown(path: Path) -> str:
        """加载Markdown文件"""
        if not path.exists():
            return ""

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    @classmethod
    def get_template_path(cls, task_id: str) -> Path:
        """
        获取任务的HTML模板路径

        Args:
            task_id: 任务ID

        Returns:
            Path: template.html的路径
        """
        return cls.CONFIG_BASE_PATH / task_id / "config_files" / "wrapping" / "template.html"

    @classmethod
    def load_sales_list(cls, task_id: str) -> List[Dict[str, Any]]:
        """
        加载任务的销售名单（从JSON文件）

        Args:
            task_id: 任务ID

        Returns:
            List[Dict[str, Any]]: 销售名单列表
            [
                {
                    "job_id": "00165",
                    "sale_name": "柳家华",
                    "sale_class": "传统经营导师",
                    "city_operation_department": "湖北省区直管",
                    "province": "湖北省区",
                    "region": "华中大区",
                    "business_department": "马上住焕新事业部"
                },
                ...
            ]
        """
        sales_path = cls.CONFIG_BASE_PATH / task_id / "config_files" / "sales" / "sales.json"

        if not sales_path.exists():
            return []

        try:
            sales_data = cls._load_json(sales_path)
            return sales_data.get("sales", [])
        except Exception as e:
            print(f"加载销售名单失败: {e}")
            return []

    @classmethod
    def load_province_sales_count(cls, task_id: str) -> Dict[str, int]:
        """
        加载任务的省份销售人员数量（从JSON文件）

        Args:
            task_id: 任务ID

        Returns:
            Dict[str, int]: 省份销售人员数量字典
            {
                "湖北省区": 10,
                "浙江省区": 15,
                ...
            }
        """
        sales_path = cls.CONFIG_BASE_PATH / task_id / "config_files" / "sales" / "sales.json"

        if not sales_path.exists():
            return {}

        try:
            sales_data = cls._load_json(sales_path)
            return sales_data.get("province_sales_count", {})
        except Exception as e:
            print(f"加载省份销售人员数量失败: {e}")
            return {}

    @classmethod
    def get_sale_config(cls, task_id: str, job_id: str) -> Optional[Dict[str, Any]]:
        """
        获取指定销售的配置信息

        Args:
            task_id: 任务ID
            job_id: 销售工号

        Returns:
            Dict[str, Any]: 销售配置，如果未找到返回 None
        """
        sales_list = cls.load_sales_list(task_id)
        for sale in sales_list:
            if sale.get("job_id") == job_id:
                return sale
        return None

    @classmethod
    def sales_list_exists(cls, task_id: str) -> bool:
        """检查任务是否有销售名单配置"""
        sales_path = cls.CONFIG_BASE_PATH / task_id / "config_files" / "sales" / "sales.json"
        return sales_path.exists()


# 便捷函数
def load_task_runtime(task_id: str) -> TaskRuntime:
    """加载任务运行时配置的便捷函数"""
    return TaskRuntimeLoader.load_task(task_id)


def list_available_tasks() -> List[Dict[str, Any]]:
    """列出所有可用任务的便捷函数"""
    return TaskRuntimeLoader.list_tasks()


def load_sales_list(task_id: str) -> List[Dict[str, Any]]:
    """加载销售名单的便捷函数"""
    return TaskRuntimeLoader.load_sales_list(task_id)


def load_province_sales_count(task_id: str) -> Dict[str, int]:
    """加载省份销售人员数量的便捷函数"""
    return TaskRuntimeLoader.load_province_sales_count(task_id)


def get_sale_config(task_id: str, job_id: str) -> Optional[Dict[str, Any]]:
    """获取指定销售配置的便捷函数"""
    return TaskRuntimeLoader.get_sale_config(task_id, job_id)


if __name__ == "__main__":
    # 测试任务加载
    print("=" * 50)
    print("任务运行时加载器测试")
    print("=" * 50)

    # 列出可用任务
    tasks = list_available_tasks()
    print(f"\n可用任务数量: {len(tasks)}")

    for task in tasks:
        print(f"  - {task.get('task_id', 'unknown')}: {task.get('task_name', 'unknown')}")

    # 尝试加载第一个任务
    if tasks:
        task_id = tasks[0].get("task_id")
        if task_id:
            print(f"\n加载任务: {task_id}")
            try:
                runtime = load_task_runtime(task_id)
                print(f"  任务名称: {runtime.task_name}")
                print(f"  事业部: {runtime.business_department}")
                print(f"  章节数: {runtime.chapter_count}")
                print(f"  带工具章节: {len(runtime.get_chapters_with_tools())}")
                for ch in runtime.chapters:
                    tools_count = len(ch.tool_configs)
                    print(f"    - 章节{ch.chapter_id}: {ch.chapter_name} (工具数: {tools_count})")
            except Exception as e:
                print(f"  加载失败: {e}")