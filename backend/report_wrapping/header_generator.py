# header_generator.py
from datetime import datetime

class HeaderGenerator:
    """报告头部信息生成器

    负责将销售信息转换为标准格式的 HTML header
    """

    def __init__(
        self,
        business_department: str,
        region: str,
        province: str,
        city_operation_department: str,
        sale_name: str,
        report_time: str
    ):
        """
        Args:
            business_department: 事业部（如 "马上住焕新事业部"）
            region: 大区（如 "华中大区"）
            province: 省区（如 "湖北省区"）
            city_operation_department: 城市经营部（如 "湖北省区直管"）
            sale_name: 销售姓名
            report_time: 报告分析的时间，直接作为报告中标题部分，如"2025年、2025年12月"
        """
        self.business_department = business_department or ''
        self.region = region or ''
        self.province = province or ''
        self.city_operation_department = city_operation_department or ''
        self.sale_name = sale_name or ''
        self.report_time = report_time or ''

    def _build_department_hierarchy(self) -> str:
        """构建部门层级字符串

        格式：事业部 > 大区 > 省区 > 城市经营部 岗位 姓名
        示例：马上住焕新事业部 > 华中大区 > 湖北省区 > 湖北省区直管 传统经营导师 谢虎生

        自动过滤空值，确保层级连续性

        Returns:
            完整的标题字符串
        """
        # 组合部门层级（自动过滤空值）
        department_parts = []
        if self.business_department:
            department_parts.append(self.business_department)
        if self.region:
            department_parts.append(self.region)
        if self.province:
            department_parts.append(self.province)
        if self.city_operation_department:
            department_parts.append(self.city_operation_department)

        # 用 " > " 连接部门层级
        hierarchy = " > ".join(department_parts)

        # 添加岗位和姓名
        full_title = f"{hierarchy} {self.sale_name}".strip()

        return full_title

    def generate_header_html(self) -> str:
        """生成完整的 header HTML

        Returns:
            符合模板格式的 header HTML 字符串
        """
        # 构建标题
        full_title = self._build_department_hierarchy()
        report_title = f"{self.report_time}单兵分析报告"

        # 生成 HTML（保持与模板一致的缩进和格式）
        header_html = f"""   
        <header>
            <div>
                <h1>{report_title}</h1>
                <div style="font-size: 12px; color: var(--primary-color);">{full_title}</div>
            </div>
            <div class="subtitle">
                <p>日期: {datetime.now().strftime('%Y/%m/%d')}</p>
                <p>范围: {self.report_time}</p>
            </div>
        </header>"""

        return header_html