from typing import Dict, Any, Tuple
from pathlib import Path
import aiofiles

class ReportManager:
    """
    报告管理器
    1. 创建报告存储路径；
    2. 保存报告内容为markdown到报告存储路径；
    """
    def __init__(
        self,
        task_id: str,
        time: str,
        sale_config: Dict[str, Any],
        ):
        """
        初始化报告管理器

        Args:
            task_id: 任务ID，用于确定报告存储路径
            time: 报告时间
            sale_config: 销售人员配置
        """
        self.task_id = task_id
        self.time = time
        self.sale_config = sale_config
        self.sale_id = sale_config.get("job_id", "")
        self.sale_name = sale_config.get("sale_name", "")
        self.sale_class_folder_name = sale_config.get("sale_class", "")
        self.city_operation_department = sale_config.get("city_operation_department", "")
        self.province = sale_config.get("province", "")
        self.region = sale_config.get("region", "")
        self.business_department = sale_config.get("business_department", "")

    def create_report_directory(self) -> Tuple[Path, Path]:
        """
        创建报告目录结构
        层级结构:
            report_tasks/{task_id}/reports/
            ├── {time}/
            │   ├── {business_department}/
            │   │   ├── {region}/
            │   │   │   ├── {province}/
            │   │   │   │   ├── {city_operation_department}/
            │   │   │   │   │   ├── {sale_name}/
            │   │   │   │   │   │   ├── progress_report/    # 过程报告（各章节 md、html 等）
            │   │   │   │   │   │   └── final_report.pdf    # 最终 PDF

        :return: (report_dir, progress_report_dir)
        """

        report_dir = (
            Path("report_tasks") /
            self.task_id /
            "reports" /
            self.time /
            self.business_department /
            self.region /
            self.province /
            self.city_operation_department /
            f"{self.sale_name}"
        )
        report_dir.mkdir(parents=True, exist_ok=True)
        # 创建过程报告数据目录
        progress_report_dir = report_dir / "progress_report"
        progress_report_dir.mkdir(exist_ok=True)
        return report_dir, progress_report_dir

    async def save_chapter_content_as_markdown(
        self,
        chapter_num: int,
        chapter_content: str,
        progress_report_dir: Path
        ) -> str:
        """
        保存章节内容为Markdown文件
        :param chapter_num: 章节号
        :param chapter_content: 章节内容
        :param progress_report_dir: 过程报告目录
        :return: 章节文件路径
        """
        file_path = progress_report_dir / f"Chapter{chapter_num}_{self.sale_name}.md"
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            await f.write(chapter_content)
        return file_path

    
        