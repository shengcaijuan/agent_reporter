# AttributionAnalyzer.py
from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

"""输入&配置参数项"""
# 定义维度关系
class AttributionRelationType(str, Enum):
    ADDITIVE = "additive"
    MULTIPLICATIVE = "multiplicative"

class ContributionType(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"

class IndicatorType(str, Enum):
    PARENT = "parent_indicator"
    CHILD = "sub_indicator"

# 指标基本规格
class IndicatorSpec(BaseModel):
    name: str = Field(..., description="指标名称")
    current_value: float | int = Field(..., description="当前值")
    prior_value: float | int = Field(..., description="指标上一期值")
    coefficient: float = Field(1.0, description="指标的线性系数（+1 表示加项，-1 表示减项）")

# 维度归因分析块
class DimensionAttributionBlock(BaseModel):
    dim_name: str = Field(..., description="维度名称")
    dim_type: AttributionRelationType = Field(..., description="维度关系类型")
    parent_indicator: IndicatorSpec = Field(..., description="父指标")
    sub_indicators: List[IndicatorSpec] = Field(..., description="父指标该维度下的子指标")

# 父指标归因分析块
class ParentIndicatorAttributionBlock(BaseModel):
    parent_indicator_name: str = Field(..., description="父指标名称")
    dimension_attribution_blocks: List[DimensionAttributionBlock] = Field(..., description="维度归因分析块")

"""过程&输出参数项"""
# 子指标参数模型
class BasicIndicatorAttributionOutput(BaseModel):
    indicator_type: IndicatorType = Field(..., description="指标类型")
    indicator_name: str = Field(..., description="指标名称")
    change_value: float | int = Field(..., description="指标变化值")
    change_rate: float = Field(..., description="指标变化率")
    parent_indicator_name: Optional[str] = Field(None, description="父指标名称")
    change_contribution_type: Optional[ContributionType] = Field(None, description="子指标对父指标的变化贡献类型")
    change_contribution_value: Optional[float] = Field(None, description="子指标对父指标的变化贡献值")
    change_contribution_ratio: Optional[float] = Field(None, description="子指标对父指标的变化贡献占比")
    contribution_ratio: Optional[float] = Field(None, description="子指标对父指标值的贡献占比")

class DimensionAttributionOutput(BaseModel):
    parent_indicator: BasicIndicatorAttributionOutput = Field(..., description="父指标")
    dim_name: Optional[str] = Field(None, description="维度名称")
    positive_sub_indicators: List[BasicIndicatorAttributionOutput] = Field(..., description="正向子指标")
    negative_sub_indicators: List[BasicIndicatorAttributionOutput] = Field(..., description="负向子指标")

class ParentIndicatorAttributionOutput(BaseModel):
    parent_indicator_name: str = Field(..., description="父指标名称")
    dimension_attribution_outputs: List[DimensionAttributionOutput] = Field(..., description="各维度归因分析结果")


class AttributionAnalyzer:
    def __init__(self):
        pass

    @staticmethod
    def _calculate_change_rate(current_value: float | int, prior_value: float | int) -> float:
        """
        计算同比变化率
        规则：
        - 如果上期值为0，当期值不为0，则同比变化记为100%
        - 如果上期值为0，当期值也为0，则同比变化记为0%
        - 如果上期值不为0，则正常计算：(当期值 - 上期值) / 上期值 * 100
        :param current_value: 当期值
        :param prior_value: 上期值
        :return: 变化率（百分比）
        """
        if prior_value == 0:
            if current_value != 0:
                return 100.0
            else:
                return 0.0
        else:
            return (current_value - prior_value) / prior_value * 100


    # 通用加法关系拆解
    def _decompose_additive_effect(
            self,
            parent_indicator: IndicatorSpec,
            sub_indicators: List[IndicatorSpec],
    ) -> DimensionAttributionOutput:
        """
        通用加法关系拆解: 支持n个子指标
        对线性模型 parent = Σ(coef_i * sub_i) 进行归因。
        每个子指标的贡献 = coef * (current - prior)
        :param parent_indicator: 父指标
        :param sub_indicators: 子指标
        :return: DimensionAttributionOutput
        """
        # 计算父指标变化
        delta_parent_indicator = parent_indicator.current_value - parent_indicator.prior_value
        parent_indicator_change_rate = self._calculate_change_rate(
            parent_indicator.current_value, parent_indicator.prior_value
        )

        parent_indicator_attribution_output = BasicIndicatorAttributionOutput(
            indicator_type=IndicatorType.PARENT,
            indicator_name=parent_indicator.name,
            change_value=round(delta_parent_indicator, 2),
            change_rate=parent_indicator_change_rate
        )

        # 计算各个子指标贡献
        # 计算每个子指标的变化贡献值
        sub_indicator_change_contributions = []
        positive_contributions = []  # 正向贡献列表
        negative_contributions = []  # 负向贡献列表

        for sub_indicator in sub_indicators:
            # 计算子指标自身的变化值和变化率
            sub_change_value = sub_indicator.current_value - sub_indicator.prior_value
            sub_change_rate = self._calculate_change_rate(
                sub_indicator.current_value, sub_indicator.prior_value
            )

            # 计算子指标对父指标的变化贡献值
            change_contribution_value = sub_indicator.coefficient * sub_change_value

            # 判断贡献类型
            change_contribution_type = ContributionType.POSITIVE if change_contribution_value >= 0 else ContributionType.NEGATIVE

            sub_indicator_change_contributions.append({
                'sub_indicator': sub_indicator,
                'change_value': sub_change_value,
                'change_rate': sub_change_rate,
                'change_contribution_value': change_contribution_value,
                'change_contribution_type': change_contribution_type
            })

            # 收集正向和负向贡献
            if change_contribution_value > 0:
                positive_contributions.append(change_contribution_value)
            elif change_contribution_value < 0:
                negative_contributions.append(abs(change_contribution_value))

        # 计算正向和负向贡献的总和
        positive_total = sum(positive_contributions) if positive_contributions else 0
        negative_total = sum(negative_contributions) if negative_contributions else 0

        # 计算每个子指标的贡献占比和值贡献占比，并分类为正向和负向
        positive_sub_indicators = []
        negative_sub_indicators = []

        for item in sub_indicator_change_contributions:
            sub_indicator = item['sub_indicator']
            change_value = item['change_value']
            change_rate = item['change_rate']
            change_contribution_value = item['change_contribution_value']
            change_contribution_type = item['change_contribution_type']

            # 计算变化贡献占比（在同向贡献中的占比）
            change_contribution_ratio = None
            if change_contribution_type == ContributionType.POSITIVE and positive_total > 0:
                change_contribution_ratio = change_contribution_value / positive_total * 100
            elif change_contribution_type == ContributionType.NEGATIVE and negative_total > 0:
                change_contribution_ratio = abs(change_contribution_value) / negative_total * 100

            # 计算值贡献占比（对父指标当前值的贡献占比）
            # 值贡献 = coefficient * current_value
            value_contribution = sub_indicator.coefficient * sub_indicator.current_value
            contribution_ratio = (value_contribution / parent_indicator.current_value * 100) if parent_indicator.current_value != 0 else 0

            sub_indicator_output = BasicIndicatorAttributionOutput(
                indicator_type=IndicatorType.CHILD,
                indicator_name=sub_indicator.name,
                change_value=round(change_value, 2),
                change_rate=change_rate,
                parent_indicator_name=parent_indicator.name,
                change_contribution_type=change_contribution_type,
                change_contribution_value=round(change_contribution_value, 2),
                change_contribution_ratio=change_contribution_ratio,
                contribution_ratio=contribution_ratio
            )

            # 根据贡献类型分类到正向或负向列表
            if change_contribution_type == ContributionType.POSITIVE:
                positive_sub_indicators.append(sub_indicator_output)
            else:
                negative_sub_indicators.append(sub_indicator_output)

        return DimensionAttributionOutput(
            parent_indicator=parent_indicator_attribution_output,
            dim_name=None,  # 维度名称在此处暂不设置，由上层调用者设置
            positive_sub_indicators=positive_sub_indicators,
            negative_sub_indicators=negative_sub_indicators
        )

    # 通用乘法关系拆解
    def _decompose_multiplicative_effect(
            self,
            parent_indicator: IndicatorSpec,
            sub_indicators: List[IndicatorSpec],
    ) -> DimensionAttributionOutput:
        """
        通用乘法关系拆解: 仅支持2个子指标
        对乘法模型 parent_indicator = sub_indicator1 * sub_indicator2 进行归因。
        使用平均交叉法计算各子指标的贡献。
        :param parent_indicator: 父指标
        :param sub_indicators: 子指标(必须恰好2个)
        :return: DimensionAttributionOutput
        """
        # 验证子指标数量
        if len(sub_indicators) != 2:
            raise ValueError("乘法关系拆解需要恰好2个子指标")

        # 计算父指标变化
        delta_parent_indicator = parent_indicator.current_value - parent_indicator.prior_value
        parent_indicator_change_rate = self._calculate_change_rate(
            parent_indicator.current_value, parent_indicator.prior_value
        )

        parent_indicator_attribution_output = BasicIndicatorAttributionOutput(
            indicator_type=IndicatorType.PARENT,
            indicator_name=parent_indicator.name,
            change_value=round(delta_parent_indicator, 2),
            change_rate=parent_indicator_change_rate
        )

        # 提取两个子指标
        sub_indicator1 = sub_indicators[0]
        sub_indicator2 = sub_indicators[1]

        # 平均交叉法计算贡献
        # 1. 计算各指标的平均值
        avg_sub1 = (sub_indicator1.current_value + sub_indicator1.prior_value) / 2.0
        avg_sub2 = (sub_indicator2.current_value + sub_indicator2.prior_value) / 2.0

        # 2. 计算交叉贡献
        sub1_effect = (sub_indicator1.current_value - sub_indicator1.prior_value) * avg_sub2
        sub2_effect = (sub_indicator2.current_value - sub_indicator2.prior_value) * avg_sub1

        # 3. 计算残差并平分
        residual = delta_parent_indicator - (sub1_effect + sub2_effect)
        sub1_effect += residual / 2.0
        sub2_effect += residual / 2.0

        # 计算各子指标的变化值和变化率
        sub1_change_value = sub_indicator1.current_value - sub_indicator1.prior_value
        sub1_change_rate = self._calculate_change_rate(
            sub_indicator1.current_value, sub_indicator1.prior_value
        )

        sub2_change_value = sub_indicator2.current_value - sub_indicator2.prior_value
        sub2_change_rate = self._calculate_change_rate(
            sub_indicator2.current_value, sub_indicator2.prior_value
        )

        # 判断贡献类型
        sub1_contribution_type = ContributionType.POSITIVE if sub1_effect >= 0 else ContributionType.NEGATIVE
        sub2_contribution_type = ContributionType.POSITIVE if sub2_effect >= 0 else ContributionType.NEGATIVE

        # 收集正向和负向贡献
        positive_contributions = []
        negative_contributions = []
        if sub1_effect > 0:
            positive_contributions.append(sub1_effect)
        elif sub1_effect < 0:
            negative_contributions.append(abs(sub1_effect))

        if sub2_effect > 0:
            positive_contributions.append(sub2_effect)
        elif sub2_effect < 0:
            negative_contributions.append(abs(sub2_effect))

        # 计算正向和负向贡献的总和
        positive_total = sum(positive_contributions) if positive_contributions else 0
        negative_total = sum(negative_contributions) if negative_contributions else 0

        # 计算变化贡献占比（在同向贡献中的占比）
        sub1_change_contribution_ratio = None
        if sub1_contribution_type == ContributionType.POSITIVE and positive_total > 0:
            sub1_change_contribution_ratio = sub1_effect / positive_total * 100
        elif sub1_contribution_type == ContributionType.NEGATIVE and negative_total > 0:
            sub1_change_contribution_ratio = abs(sub1_effect) / negative_total * 100

        sub2_change_contribution_ratio = None
        if sub2_contribution_type == ContributionType.POSITIVE and positive_total > 0:
            sub2_change_contribution_ratio = sub2_effect / positive_total * 100
        elif sub2_contribution_type == ContributionType.NEGATIVE and negative_total > 0:
            sub2_change_contribution_ratio = abs(sub2_effect) / negative_total * 100

        # 计算值贡献占比（对父指标当前值的贡献占比）
        # 在乘法关系中，使用对数分解或简化为不计算（设为None）
        # 这里采用简化的方式：对于乘法关系，值贡献占比可能不太适用，设为None
        # 或者可以计算每个子指标变化率对父指标变化率的相对贡献
        # 为了保持一致性，这里设为None，表示在乘法关系中不适用
        sub1_contribution_ratio = None
        sub2_contribution_ratio = None

        # 创建子指标输出对象
        sub1_output = BasicIndicatorAttributionOutput(
            indicator_type=IndicatorType.CHILD,
            indicator_name=sub_indicator1.name,
            change_value=round(sub1_change_value, 2),
            change_rate=sub1_change_rate,
            parent_indicator_name=parent_indicator.name,
            change_contribution_type=sub1_contribution_type,
            change_contribution_value=round(sub1_effect, 2),
            change_contribution_ratio=sub1_change_contribution_ratio,
            contribution_ratio=sub1_contribution_ratio
        )

        sub2_output = BasicIndicatorAttributionOutput(
            indicator_type=IndicatorType.CHILD,
            indicator_name=sub_indicator2.name,
            change_value=round(sub2_change_value, 2),
            change_rate=sub2_change_rate,
            parent_indicator_name=parent_indicator.name,
            change_contribution_type=sub2_contribution_type,
            change_contribution_value=round(sub2_effect, 2),
            change_contribution_ratio=sub2_change_contribution_ratio,
            contribution_ratio=sub2_contribution_ratio
        )

        # 分类为正向和负向
        positive_sub_indicators = []
        negative_sub_indicators = []

        if sub1_contribution_type == ContributionType.POSITIVE:
            positive_sub_indicators.append(sub1_output)
        else:
            negative_sub_indicators.append(sub1_output)

        if sub2_contribution_type == ContributionType.POSITIVE:
            positive_sub_indicators.append(sub2_output)
        else:
            negative_sub_indicators.append(sub2_output)

        return DimensionAttributionOutput(
            parent_indicator=parent_indicator_attribution_output,
            dim_name=None,  # 维度名称在此处暂不设置，由上层调用者设置
            positive_sub_indicators=positive_sub_indicators,
            negative_sub_indicators=negative_sub_indicators
        )

    # 维度归因分析块
    def dimension_attribution_analysis(
            self,
            dimension_attribution_block: DimensionAttributionBlock
    ) -> DimensionAttributionOutput:
        """
        维度归因分析
        :param dimension_attribution_block: 维度归因分析块
        :return: DimensionAttributionOutput
        """
        # 维度归因分析块
        dim_name = dimension_attribution_block.dim_name
        dim_type = dimension_attribution_block.dim_type
        parent_indicator = dimension_attribution_block.parent_indicator
        sub_indicators = dimension_attribution_block.sub_indicators

        if dim_type == AttributionRelationType.ADDITIVE:
            result = self._decompose_additive_effect(parent_indicator, sub_indicators)
        elif dim_type == AttributionRelationType.MULTIPLICATIVE:
            result = self._decompose_multiplicative_effect(parent_indicator, sub_indicators)
        else:
            raise ValueError(f"不支持的维度关系类型: {dim_type}")

        # 设置维度名称
        result.dim_name = dim_name
        return result

    # 父指标归因分析块
    def parent_indicator_attribution_analysis(
            self,
            parent_indicator_attribution_block: ParentIndicatorAttributionBlock
    ) -> ParentIndicatorAttributionOutput:
        """
        父指标归因分析
        :param parent_indicator_attribution_block: 父指标归因分析块
        :return: ParentIndicatorAttributionOutput
        """
        # 父指标归因分析块
        parent_indicator_name = parent_indicator_attribution_block.parent_indicator_name
        dimension_attribution_blocks = parent_indicator_attribution_block.dimension_attribution_blocks

        # 维度归因分析
        dimension_attribution_outputs = []
        for dimension_attribution_block in dimension_attribution_blocks:
            dimension_attribution_output = self.dimension_attribution_analysis(dimension_attribution_block)
            dimension_attribution_outputs.append(dimension_attribution_output)

        # 创建父指标归因输出对象
        parent_indicator_attribution_output = ParentIndicatorAttributionOutput(
            parent_indicator_name=parent_indicator_name,
            dimension_attribution_outputs=dimension_attribution_outputs
        )
        return parent_indicator_attribution_output