"""运行时配置"""

import sys
import os
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional

# 添加项目根目录到路径以导入 app.schemas
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from app.schemas.data_source import DataSource


# 默认Role（可被任务配置覆盖）
DEFAULT_ROLE = "你是一位资深的销售业绩数据分析师，主要面向一线销售的数据分析报告场景，为销售个人提供一份专属的、数据驱动的业绩分析与行动指南。"

class GuidelineSection(BaseModel):
    """guideline小节配置"""
    section_name: str = Field(description="小节名称")
    requirements: List[str] = Field(default_factory=list)


class GuidelineConfig(BaseModel):
    """
    guideline JSON配置模型

    用于前后端共享的guideline数据结构，包含：
    - 章节结构描述
    - 各小节分析要求
    - 语言风格要求
    - 输出示例
    """
    chapter_id: int
    chapter_name: str
    structure_intro: str = ""  # 章节结构描述，如"第一章分为三个部分：..."
    sections: List[GuidelineSection] = Field(default_factory=list)
    style_requirements: List[str] = Field(default_factory=list)
    output_example: str = ""

    def to_markdown(self, role: str = DEFAULT_ROLE, task_prefix: str = "") -> str:
        """
        将JSON配置转换为markdown格式的guideline

        Args:
            role: 角色定义（默认使用DEFAULT_ROLE）
            task_prefix: 任务前缀（报告介绍，会插入到guideline前面）

        Returns:
            完整的markdown格式guideline
        """
        lines = []

        # 1. Role部分
        lines.append("# Role\n")
        lines.append(role)
        lines.append("")

        # 2. 任务部分
        lines.append("# 任务\n")
        lines.append(f"请你完成第{self._get_chinese_number(self.chapter_id)}章节{self.chapter_name}的智能报告分析工作。")
        lines.append("")
        if self.structure_intro:
            lines.append(self.structure_intro)
            lines.append("")

        # 3. 各小节分析要求
        for section in self.sections:
            lines.append(f"## {section.section_name}\n")
            for i, req in enumerate(section.requirements, 1):
                lines.append(f"{i}. {req}")
            lines.append("")

        # 4. 语言风格要求
        lines.append("# 语言风格、内容结构及样式要求\n")
        for i, style in enumerate(self.style_requirements, 1):
            lines.append(f"{i}. {style};")
        lines.append("")

        # 5. 输出示例
        lines.append("# 输出示例\n")
        lines.append("```markdown")
        lines.append(self.output_example)
        lines.append("```")

        guideline_content = "\n".join(lines)

        # 如果有任务前缀，拼接到前面
        if task_prefix:
            return f"{task_prefix}\n\n---\n\n{guideline_content}"
        return guideline_content

    @staticmethod
    def _get_chinese_number(num: int) -> str:
        """将数字转换为中文数字"""
        chinese_nums = ["零", "一", "二", "三", "四", "五", "六", "七", "八", "九", "十"]
        if num <= 10:
            return chinese_nums[num]
        elif num < 20:
            return f"十{chinese_nums[num - 10]}"
        else:
            return str(num)

class WrappingRequirement(BaseModel):
    """章节布局要求"""
    chapter_id: int
    chapter_name: str = ""
    requirements: List[str] = Field(default_factory=list)


class WrappingRequirementsConfig(BaseModel):
    """布局要求配置"""
    task_id: str
    lay_out_requirements: List[WrappingRequirement] = Field(default_factory=list)

    def get_chapter_requirements(self, chapter_id: int) -> List[str]:
        """获取指定章节的布局要求"""
        for layout in self.lay_out_requirements:
            if layout.chapter_id == chapter_id:
                return layout.requirements
        return []

    def to_markdown(self) -> str:
        """转换为markdown格式"""
        lines = []
        for layout in self.lay_out_requirements:
            if layout.requirements:
                lines.append(f"## 第{GuidelineConfig._get_chinese_number(layout.chapter_id)}章节：{layout.chapter_name}")
                for i, req in enumerate(layout.requirements, 1):
                    lines.append(f"{i}. {req}")
                lines.append("")
        return "\n".join(lines)


class ChapterRuntime(BaseModel):
    chapter_id: int = Field(description="章节号")
    chapter_name: str = Field(description="章节名称")
    chapter_type: str = Field(description="章节类型，分为simple, with_tools, summary")
    has_tools: bool = Field(description="是否需要工具函数")
    guideline: str = Field(description="分析指导文档")
    tool_configs: List[Dict[str, Any]] = Field(default_factory=list, description="工具函数配置")
    summarize_chapters: List[int] = Field(default_factory=list, description="总结章节需要汇总的章节ID列表")


class TaskRuntime(BaseModel):
    """任务运行时配置"""
    task_id: str
    task_name: str
    business_department: str
    description: str
    report_intro: str
    chapters: List[ChapterRuntime]
    data_source: Optional[DataSource] = Field(None, description="数据源配置")
    report_structure: Dict[str, Any] = Field(default_factory=dict)
    lay_out_requirements: str = ""  # 布局要求

    @property
    def chapter_count(self) -> int:
        return len(self.chapters)

    def get_chapter(self, chapter_id: int) -> Optional[ChapterRuntime]:
        """获取指定章节配置"""
        for chapter in self.chapters:
            if chapter.chapter_id == chapter_id:
                return chapter
        return None

    def get_chapters_with_tools(self) -> List[ChapterRuntime]:
        """获取需要执行工具的章节"""
        return [ch for ch in self.chapters if ch.has_tools]

    def get_summary_chapter(self) -> Optional[ChapterRuntime]:
        """获取总结章节"""
        for chapter in self.chapters:
            if chapter.chapter_type == "summary":
                return chapter
        return None