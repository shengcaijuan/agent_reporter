from pathlib import Path
from typing import Optional, Dict, Any
from agent_framework.messages import SystemMessage, HumanMessage
from datetime import datetime
import re, aiofiles
from model import AnaModel

class ReportDecorator:
    def __init__(
        self,
        llm: AnaModel,
        sale_name: str,
        initial_report: str,
        html_report_folder: Path,
        template_path: Path,
        sale_config: Optional[Dict[str, Any]] = None,
        lay_out_requirements: Optional[str] = None,
        time: Optional[str] = None
        ):
        """
        初始化报告装饰器

        Args:
            llm: 模型
            sale_name: 销售人员姓名
            initial_report: 初始报告内容（Markdown格式）
            html_report_folder: HTML报告文件夹
            template_path: 模板路径，从任务配置目录加载（如 report_tasks/{task_id}/config_files/wrapping/template.html）
            sale_config: 销售人员信息, 用于生成结构化header html内容
                - 示例：
                {
                    "sale_name": "张三",
                    "job_id": "04490",
                    "sale_class": "销售岗位", # move_right_away, pilot_4_provinces, traditional_mentor
                    "city_operation_department": "城市经营部",
                    "province": "省区",
                    "region": "大区",
                    "business_department": "事业部"
                }
            lay_out_requirements: 布局要求（Markdown格式），从任务运行时配置获取
            time: 报告时间（如 "202401"），用于HTML文件命名
        """
        self.llm = llm
        self.sale_name = sale_name
        self.sale_config = sale_config
        self.initial_report = initial_report
        self.template_path = template_path
        self.html_report_folder = html_report_folder
        self.lay_out_requirements = lay_out_requirements
        self.time = time or datetime.now().strftime('%Y%m')
        # TODO: report_time 需要从前端传入
        self.report_time = "2025年"

    async def read_template(self) -> str:
        """读取模板内容"""
        try:
            async with aiofiles.open(self.template_path, 'r', encoding='utf-8') as f:
                return await f.read()
        except FileNotFoundError:
            print(f"警告：{self.template_path}文件未找到")
            return ""
        except Exception as e:
            print(f"读取{self.template_path}时出错：{e}")
            return ""

    async def extract_css_from_template(self) -> str:
        """从模板中提取CSS样式"""
        try:
            template_content = await self.read_template()
            if not template_content:
                return ""
            # 提取<style>标签内的内容
            style_pattern = r'<style>(.*?)</style>'
            match = re.search(style_pattern, template_content, re.DOTALL)

            if match:
                return match.group(1)
            return ""
        except Exception as e:
            print(f"提取CSS时出错：{e}")
            return ""

    def postprocess_html(self, html_content: str) -> str:
        """后处理HTML内容，移除前后的```html和```标记"""
        if not html_content:
            return html_content
        # 移除开头的```html或```html+
        html_content = re.sub(r'^```html[+]?\s*\n?', '', html_content.strip())
        # 移除结尾的```
        html_content = re.sub(r'\n?```\s*$', '', html_content.strip())
        return html_content

    def _replace_header_html(self, html_content: str) -> str:
        """替换 HTML 中的 header 部分

        使用 HeaderGenerator 生成新的 header，并通过正则表达式替换
        LLM 生成的 HTML 中的 header 部分。

        Args:
            html_content: LLM 生成的完整 HTML

        Returns:
            替换 header 后的 HTML，如果替换失败则返回原始 HTML
        """
        # 如果没有提供销售信息，返回原始 HTML（向后兼容）
        if not self.sale_config:
            return html_content

        try:
            from .header_generator import HeaderGenerator

            # 创建 HeaderGenerator
            header_gen = HeaderGenerator(
                business_department=self.sale_config.get('business_department', ''),
                region=self.sale_config.get('region', ''),
                province=self.sale_config.get('province', ''),
                city_operation_department=self.sale_config.get('city_operation_department', ''),
                sale_name=self.sale_name,
                report_time=self.report_time
            )

            # 生成新的 header HTML
            new_header = header_gen.generate_header_html()

            # 使用正则表达式替换 <header>...</header> 部分
            # re.DOTALL 标志使 . 匹配包括换行符在内的所有字符
            # *? 表示非贪婪匹配，确保只匹配第一个 header
            pattern = r'<header>.*?</header>'
            replaced_html = re.sub(
                pattern,
                new_header,
                html_content,
                flags=re.DOTALL
            )

            return replaced_html

        except Exception as e:
            # 如果替换失败，记录错误并返回原始 HTML（降级处理）
            print(f"Header 替换失败：{e}")
            return html_content

    async def generate_wrapped_report(self) -> str:
        """使用包装模块生成完整HTML报告"""
        # 读取模板内容
        template_content = await self.read_template()
        if not template_content:
            return ""

        # 获取布局要求
        lay_out_req = self.lay_out_requirements

        system_message = SystemMessage(content=f"HTML报告范本：\n{template_content}")
        user_prompt = f"""
        请参考HTML报告范本，将下面的各章节报告进行包装，并生成完整的HTML报告。注意仅输出<!DOCTYPE html>和</html>之间的内容，不要输出多余的其他符号和内容。

        # 要点：
        1. **范本仅供参考**：范本中的内容结构和排版仅供参考，请根据实际报告内容进行灵活调整。
        2. **风格参考**：参考范本中的配色方案、字体风格、视觉设计风格等美学元素。
        3. **因地制宜排版**：根据报告的实际内容、章节结构、数据特点来设计最适合的排版布局，不需要完全照搬范本的版式。
        4. **行动指南**：行动指南部分需按点结构化地陈述，避免连续段落。

        # 各个章节的排版和内容展示的细节要求：

        {lay_out_req}

        初始报告内容：\n
        {self.initial_report}\n
        """
        user_message = HumanMessage(content=user_prompt)
        messages = [system_message, user_message]
        wrapped_report = await self.llm.ainvoke(messages)

        # 后处理HTML内容
        processed_html = self.postprocess_html(wrapped_report.content)

        return processed_html

    async def save_as_html(
        self,
        wrapped_report: str,
    ) -> Path:
        """保存包装后的HTML报告"""
        filename = f"{self.sale_name}_{self.time}.html"
        file_path = self.html_report_folder / filename

        async with aiofiles.open(file_path, 'w', encoding='utf-8') as f:
            await f.write(wrapped_report)

        return file_path

    async def wrapping_reports(self) -> Path:
        """
        包装报告为HTML格式

        Returns:
            Path: 生成的HTML文件路径
        """
        print(f"[开始包装报告] {self.sale_name} 的报告开始包装")

        # 包装报告
        wrapped_report = await self.generate_wrapped_report()
        # 替换 header
        wrapped_report = self._replace_header_html(wrapped_report)
        # 保存HTML报告
        html_file = await self.save_as_html(wrapped_report)

        print(f"[HTML报告保存完成] {self.sale_name} 的报告HTML报告保存完成")

        return html_file
