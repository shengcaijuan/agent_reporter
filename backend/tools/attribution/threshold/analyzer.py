from pydantic import BaseModel, Field
from typing import List, Union, Optional, Tuple, Iterator
from enum import Enum

""" 阈值配置项 """
class ThresholdType(str, Enum):
    """阈值类型"""
    TARGET_ACHIEVEMENT = "TARGET_ACHIEVEMENT"   # 目标达成率
    TOTAL_PERFORMANCE_SCORE = "TOTAL_PERFORMANCE_SCORE" # 绩效总分
    RECEIVABLES_CONCENTRATION_RATE = "RECEIVABLES_CONCENTRATION_RATE" # 应收集中率
    DUE_RECEIVABLES_COLLECTION_RATE = "DUE_RECEIVABLES_COLLECTION_RATE" # 当月到期回款率
    HISTORICAL_OVERDUE_RECEIVABLES_COLLECTION_RATE = "HISTORICAL_OVERDUE_RECEIVABLES_COLLECTION_RATE" # 历史逾期回款率
    RATIO_OF_OVERDUE_RECEIVABLES_EXCEEDING_30_DAYS = "RATIO_OF_OVERDUE_RECEIVABLES_EXCEEDING_30_DAYS" # 逾期超过30天比例
    AVERAGE_DEALER_CREDIT_LIMIT_PER_HOUSEHOLD = "AVERAGE_DEALER_CREDIT_LIMIT_PER_HOUSEHOLD" # 户均经销授信金额/事业部均值
    PROBABILITY_OF_OVERDUE_IN_THE_CURRENT_YEAR = "PROBABILITY_OF_OVERDUE_IN_THE_CURRENT_YEAR" # 当前年度逾期概率
    OUTLET_VISIT_COVERAGE = "OUTLET_VISIT_COVERAGE" # 网点拜访覆盖率

""" 输入参数项 """
# 输入参数模型
class ThresholdBasedIndicatorSpec(BaseModel):
    indicator_name: str = Field(..., description="指标名称")
    indicator_value: Union[float, int] = Field(..., description="指标值")
    baseline_name: Optional[str] = Field(None, description="基准指标名称")
    baseline_value: Optional[Union[float, int]] = Field(None, description="基准值")
    threshold_type: ThresholdType = Field(..., description="阈值类型")

class ThresholdBasedIndicatorsBlock(BaseModel):
    indicators: List[ThresholdBasedIndicatorSpec] = Field(..., description="指标列表")
    
    def iter_indicators(self) -> Iterator[ThresholdBasedIndicatorSpec]:
        for indicator in self.indicators:
            yield indicator

""" 过程参数项 """
class ThresholdBasedIndicatorAttrOutput(BaseModel):
    indicator_name: str = Field(..., description="指标名称")
    indicator_value: float = Field(..., description="指标值")
    baseline_name: Optional[str] = Field(None, description="基准指标名称")
    baseline_value: Optional[Union[float, int]] = Field(None, description="基准值")
    status_label: str = Field(..., description="状态标签（如：合格/不合格、无预警/一般预警/较大预警/重大预警）")
    is_negative: Optional[bool] = Field(None, description="是否为负向/风险指标")

""" 输出参数项 """
class ThresholdBasedAttrOutput(BaseModel):
    """过程参数模型"""
    indicators: List[ThresholdBasedIndicatorAttrOutput] = Field(..., description="指标列表")
    negative_indicators: Optional[List[ThresholdBasedIndicatorAttrOutput]] = Field(None, description="负向指标列表")
    positive_indicators: Optional[List[ThresholdBasedIndicatorAttrOutput]] = Field(None, description="正向指标列表")

class ThresholdBasedAttrAnalyzer:
    """ 基于阈值指标(达成率)的指标归因分析工具 """
    def __init__(self):
        pass

    @staticmethod
    def evaluate_status_label(
            value: Union[float, int],
            threshold_type: ThresholdType,
            relative_threshold: Optional[Union[float, int]] = None # 相对阈值（如：事业部逾期概率）
    ) -> Union[str, Tuple[str, bool]]:
        def _achievement_rate_label(_value: Union[float, int]):
            """ 计算【达成率】标签 """
            if _value < 60:
                return "未达标-不及格"
            elif 60 <= _value < 80:
                return "未达标-合格"
            elif 80 <= _value < 100:
                return "未达标-良好"
            else:  # value >= 100
                return "达标-优秀"

        def _total_performance_score_label(_value: Union[float, int]):
            """计算【绩效总分】标签"""
            if _value <= 20:  # 前20%，即TPO20%
                return "优秀"
            elif 20 < _value <= 50:  # 20%-50%
                return "良好"
            elif 50 < _value <= 80:  # 50%-80%
                return "中游水平"
            else:  # value > 80，即后20%
                return "落后-待改进"

        def _receivables_concentration_rate_label(_value: Union[float, int]):
            """计算【应收集中率】标签"""
            if _value < 30:
                return "无预警"
            elif 30 <= _value <= 45:
                return "一般预警"
            elif 45 < _value <= 60:
                return "较大预警"
            else:  # value > 60
                return "重大预警"
        
        def _due_receivables_collection_rate_label(_value: Union[float, int]):
            """计算【当月到期回款率】标签"""
            if _value > 85:
                return "无预警"
            elif 75 <= _value <= 85:
                return "一般预警"
            elif 60 <= _value <= 75:
                return "较大预警"
            else:  # value <= 60
                return "重大预警"

        def _historical_overdue_receivables_collection_rate_label(_value: Union[float, int]):
            """计算历史逾期回款率标签"""
            if _value > 70:
                return "无预警"
            elif 60 <= _value <= 70:
                return "一般预警"
            elif 50 <= _value <= 60:
                return "较大预警"
            else:  # value <= 50
                return "重大预警"
        
        def _ratio_of_overdue_receivables_exceeding_30_days_label(_value: Union[float, int]):
            """计算【逾期超过30天比例】标签"""
            if _value == 0:
                return "无预警"
            elif 0 < _value <= 30:
                return "一般预警"
            elif 30 < _value <= 50:
                return "较大预警"
            else:  # value > 50
                return "重大预警"

        def _average_dealer_credit_limit_per_household_label(
            _value: Union[float, int], 
            _relative_threshold: Union[float, int] = 65
            ) -> str:
            """计算【户均经销授信金额】标签，相对阈值为【事业部均值】，单位：万元"""
            if _value <= _relative_threshold * 1.2:
                return "无预警"
            elif _relative_threshold * 1.2 < _value <= _relative_threshold * 1.5:
                return "一般预警"
            elif _relative_threshold * 1.5 < _value <= _relative_threshold * 2:
                return "较大预警"
            else:  # value > _relative_threshold * 2
                return "重大预警"

        def _probability_of_overdue_in_the_current_year_label(
            _value: Union[float, int], 
            _relative_threshold: Union[float, int] = 50
            ) -> str:
            """计算【当年逾期概率】标签，相对阈值为【事业部逾期概率】"""
            if _value == 0:
                return "无预警"
            elif 0 < _value <= _relative_threshold + 5:
                return "一般预警"
            elif _relative_threshold + 5 < _value <= _relative_threshold + 10:
                return "较大预警"
            else:  # value > _relative_threshold + 10
                return "重大预警"

        def _outlet_visit_coverage_label(_value: Union[float, int]):
            """计算【网点拜访覆盖率】标签"""
            if 90<=_value<100:
                return "扣绩效5分，无绩效人员捐款50元"
            elif 80<=_value<90:
                return "扣绩效8分，无绩效人员捐款100元"
            elif 60<=_value<80:
                return "扣绩效10分，无绩效人员捐款150元"
            else:  # value < 60
                return "扣绩效15分，无绩效人员捐款200元"

        # 根据阈值类型选择对应的标签计算函数
        if threshold_type == ThresholdType.TARGET_ACHIEVEMENT:
            return _achievement_rate_label(value)
        elif threshold_type == ThresholdType.TOTAL_PERFORMANCE_SCORE:
            return _total_performance_score_label(value)
        elif threshold_type == ThresholdType.RECEIVABLES_CONCENTRATION_RATE:
            return _receivables_concentration_rate_label(value)
        elif threshold_type == ThresholdType.DUE_RECEIVABLES_COLLECTION_RATE:
            return _due_receivables_collection_rate_label(value)
        elif threshold_type == ThresholdType.HISTORICAL_OVERDUE_RECEIVABLES_COLLECTION_RATE:
            return _historical_overdue_receivables_collection_rate_label(value)
        elif threshold_type == ThresholdType.RATIO_OF_OVERDUE_RECEIVABLES_EXCEEDING_30_DAYS:
            return _ratio_of_overdue_receivables_exceeding_30_days_label(value)
        elif threshold_type == ThresholdType.AVERAGE_DEALER_CREDIT_LIMIT_PER_HOUSEHOLD:
            return _average_dealer_credit_limit_per_household_label(value)
        elif threshold_type == ThresholdType.PROBABILITY_OF_OVERDUE_IN_THE_CURRENT_YEAR:
            return _probability_of_overdue_in_the_current_year_label(value)
        elif threshold_type == ThresholdType.OUTLET_VISIT_COVERAGE:
            return _outlet_visit_coverage_label(value)
        else:
            raise ValueError(f"Invalid threshold type: {threshold_type}")
    
    def _evaluate_single_indicator(
            self,
            indicator: ThresholdBasedIndicatorSpec
    ) -> ThresholdBasedIndicatorAttrOutput:
        """对单个指标进行归因分析"""
        threshold_type = indicator.threshold_type
        # 目标达成率
        if threshold_type == ThresholdType.TARGET_ACHIEVEMENT:
            # 达成率
            if indicator.baseline_value is None:
                status_label = self.evaluate_status_label(indicator.indicator_value, threshold_type)
                is_negative = True if status_label.startswith("未达标") else False
                return ThresholdBasedIndicatorAttrOutput(
                    indicator_name=indicator.indicator_name,
                    indicator_value=indicator.indicator_value,
                    status_label=status_label,
                    is_negative=is_negative
                )
                
            # 指标值 / 目标值
            else:
                achievement_rate = (indicator.indicator_value / indicator.baseline_value) * 100
                status_label = self.evaluate_status_label(achievement_rate, threshold_type)
                is_negative = True if status_label.startswith("未达标") else False
                return ThresholdBasedIndicatorAttrOutput(
                    indicator_name=indicator.indicator_name,
                    indicator_value=indicator.indicator_value,
                    baseline_name=indicator.baseline_name,
                    baseline_value=indicator.baseline_value,
                    status_label=status_label,
                    is_negative=is_negative
                )

        # 户均经销授信金额或当年逾期概率
        elif threshold_type == ThresholdType.AVERAGE_DEALER_CREDIT_LIMIT_PER_HOUSEHOLD or threshold_type == ThresholdType.PROBABILITY_OF_OVERDUE_IN_THE_CURRENT_YEAR:
            status_label = self.evaluate_status_label(indicator.indicator_value, threshold_type, indicator.baseline_value)
            is_negative = True if status_label == "重大预警" or status_label == "较大预警" else False
            return ThresholdBasedIndicatorAttrOutput(
                indicator_name=indicator.indicator_name,
                indicator_value=indicator.indicator_value,
                baseline_name=indicator.baseline_name,
                baseline_value=indicator.baseline_value,
                status_label=status_label,
                is_negative=is_negative
            )

        else: # 绩效总分、应收集中率、当月到期回款率、历史逾期回款率、逾期超过30天比例
            status_label = self.evaluate_status_label(indicator.indicator_value, threshold_type)
            return ThresholdBasedIndicatorAttrOutput(
                indicator_name=indicator.indicator_name,
                indicator_value=indicator.indicator_value,
                status_label=status_label
            )

    def evaluate_indicators(
            self,
            _indicators: ThresholdBasedIndicatorsBlock
    ) -> ThresholdBasedAttrOutput:
        """对指标列表进行归因分析"""
        analyzed_indicators = []
        negative_indicators = []
        positive_indicators = []
        for indicator in _indicators.iter_indicators():
            analyzed_indicator = self._evaluate_single_indicator(indicator)
            analyzed_indicators.append(analyzed_indicator)
            # 指标分析是否具备正负向属性（修复：检查 analyzed_indicator 而不是 indicator）
            if analyzed_indicator.is_negative is not None:
                if analyzed_indicator.is_negative:
                    negative_indicators.append(analyzed_indicator)
                else:
                    positive_indicators.append(analyzed_indicator)
        return ThresholdBasedAttrOutput(
            indicators=analyzed_indicators,
            negative_indicators=negative_indicators if negative_indicators else None,
            positive_indicators=positive_indicators if positive_indicators else None
        )



