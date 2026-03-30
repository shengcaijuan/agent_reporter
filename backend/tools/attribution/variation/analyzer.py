from pydantic import BaseModel, Field
from typing import List, Union, Iterator

""" 输入参数项 """
class VariationBasedIndicatorSpec(BaseModel):
    indicator_name: str = Field(..., description="指标名称")
    current_value: Union[float, int] = Field(..., description="当期值")
    prior_value: Union[float, int] = Field(..., description="上期值")

class VariationBasedIndicatorsBlock(BaseModel):
    indicators: List[VariationBasedIndicatorSpec] = Field(..., description="指标列表")
    def iter_indicators(self) -> Iterator[VariationBasedIndicatorSpec]:
        for indicator in self.indicators:
            yield indicator

""" 过程参数项 """
class VariationBasedIndicatorAttrOutput(BaseModel):
    indicator_name: str = Field(..., description="指标名称")
    current_value: Union[float, int] = Field(..., description="当期值")
    prior_value: Union[float, int] = Field(..., description="上期值")
    change_value: Union[float, int] = Field(..., description="绝对变化值")
    change_rate: float = Field(..., description="相对变化率")

""" 输出参数项 """
class VariationBasedAttrOutput(BaseModel):
    indicators: List[VariationBasedIndicatorAttrOutput] = Field(..., description="指标列表")
    negative_indicators: List[VariationBasedIndicatorAttrOutput] = Field(..., description="负向指标列表")
    positive_indicators: List[VariationBasedIndicatorAttrOutput] = Field(..., description="正向指标列表")

class VariationBasedAttrAnalyzer:
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


    def _evaluate_single_indicator(
        self,
        indicator: VariationBasedIndicatorSpec
        ) -> VariationBasedIndicatorAttrOutput:
        """对单个指标进行归因分析"""
        change_value = indicator.current_value - indicator.prior_value
        change_rate = self._calculate_change_rate(indicator.current_value, indicator.prior_value)
        return VariationBasedIndicatorAttrOutput(
            indicator_name=indicator.indicator_name,
            current_value=indicator.current_value,
            prior_value=indicator.prior_value,
            change_value=round(change_value, 2),
            change_rate=round(change_rate, 2)
        )

    def evaluate_indicators(
        self,
        _indicators: VariationBasedIndicatorsBlock
    ) -> VariationBasedAttrOutput:
        """对指标列表进行归因分析"""
        analyzed_indicators = []
        negative_indicators = []
        positive_indicators = []
        for indicator in _indicators.iter_indicators():
            analyzed_indicator = self._evaluate_single_indicator(indicator)
            analyzed_indicators.append(analyzed_indicator)
            if analyzed_indicator.change_value < 0:
                negative_indicators.append(analyzed_indicator)
            else:
                positive_indicators.append(analyzed_indicator)
        return VariationBasedAttrOutput(
            indicators=analyzed_indicators, 
            negative_indicators=negative_indicators, 
            positive_indicators=positive_indicators
            )
