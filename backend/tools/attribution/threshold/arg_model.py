# ThresholdArgModel.py
from pydantic import BaseModel, Field, create_model
from typing import List, Union, Dict, Any, Type
from .analyzer import ThresholdType, ThresholdBasedIndicatorSpec, ThresholdBasedIndicatorsBlock
from tools.attribution.utils import name_to_snake_key

class ThresholdArgModel:
    def __init__(
            self,
            model_name_root: str,
            indicators_config: List[Dict[str, Any]]
    ):
        """
        初始化
        :param model_name_root: 参数模型命名词根，采用pascal case
        :param indicators_config: 基于阈值分析的参数模型指标配置
            - 示例：
            [
            {
                "indicator": "高值品收入",
                "baseline": "高值品收入目标",
                "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
            },
            {
                "indicator": "真时丽产品收入",
                "baseline": "真时丽产品收入目标",
                "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
            },
            {
                "indicator": "绩效总分",
                "threshold_type": ThresholdType.TOTAL_PERFORMANCE_SCORE
            }
            ]
        """
        self.model_name_root = model_name_root
        self.indicators_config: List[Dict[str, Any]] = indicators_config
        self.processed_config = self._create_indicators_config()
        # 缓存属性初始化
        self._cached_args_model4llm = None
        self._cached_args_model = None

    def _create_indicators_config(self) -> List[Dict[str, Any]]:
        """
        创建结构化配置
        :return processed_config:
            - 示例：
            [
            {
                "indicator_name": "高值品收入",
                "indicator_key": "gao_zhi_pin_shou_ru",
                "baseline_name": "高值品收入目标",
                "baseline_key": "gao_zhi_pin_shou_ru_mu_biao",
                "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
            },
            {
                "indicator_name": "真时丽产品收入",
                "indicator_key": "zhen_shi_li_chan_pin_shou_ru",
                "baseline_name": "真时丽产品收入目标",
                "baseline_key": "zhen_shi_li_chan_pin_shou_ru_mu_biao",
                "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
            },
            {
                "indicator_name": "绩效总分",
                "indicator_key": "ji_xiao_zong_fen",
                "threshold_type": ThresholdType.TOTAL_PERFORMANCE_SCORE
            }
            ]
        """
        processed_config = []
        for indicator_config in self.indicators_config:
            indicator_name = indicator_config.get("indicator", None)
            threshold_type = indicator_config.get("threshold_type", None)
            # 验证字段存在
            assert indicator_name is not None, "indicator_name is required"
            assert threshold_type is not None, "threshold_type is required"

            # 获取可选字段
            indicator_key = indicator_config.get("indicator_key", None)
            baseline_name = indicator_config.get("baseline", None)
            baseline_key = indicator_config.get("baseline_key", None)

            # 自动生成或使用提供的key
            if indicator_key is None:
                # indicator_name 已在第99行断言确保不为 None
                indicator_key = name_to_snake_key(indicator_name)  # type: ignore[arg-type]
            if baseline_key is None and baseline_name is not None:
                baseline_key = name_to_snake_key(baseline_name)  # type: ignore[arg-type]

            # 构建配置字典
            config_item = {
                "indicator_name": indicator_name,
                "indicator_key": indicator_key,
                "threshold_type": threshold_type
            }
            # 若存在分母项则补充
            if baseline_name is not None:
                config_item["baseline_name"] = baseline_name
                config_item["baseline_key"] = baseline_key

            processed_config.append(config_item)

        return processed_config

    def create_args_model4llm(self) -> Type[BaseModel]:
        """
        创建LLM输入参数模型
        :return: LLM输入模型类
        """
        # 如果已经创建过，直接返回缓存的模型
        if self._cached_args_model4llm:
            return self._cached_args_model4llm

        fields_4llm = {}
        for config in self.processed_config:
            indicator_name = config.get("indicator_name", "未命名指标")
            indicator_key = config.get("indicator_key", name_to_snake_key(indicator_name))
            fields_4llm[indicator_key] = (
                Union[float, int],
                Field(..., description=f"{indicator_name}")
            )
            if "baseline_key" in config:
                baseline_name = config.get("baseline_name", "未命名指标")
                baseline_key = config.get("baseline_key", name_to_snake_key(baseline_name))
                fields_4llm[baseline_key] = (
                    Union[float, int],
                    Field(..., description=f"{baseline_name}")
                )
        # 创建并缓存模型
        class_name = f"{self.model_name_root}DataInput4LLM"
        self._cached_args_model4llm = create_model(class_name, **fields_4llm, __base__=BaseModel)
        return self._cached_args_model4llm

    def create_args_model(self) -> Type[BaseModel]:
        """
        创建参数模型
        将LLM输入转换为ThresholdBasedIndicatorSpec对象
        :return: 内部输入模型类
        """
        if self._cached_args_model is not None:
            return self._cached_args_model

        # 创建指标字段
        fields = {}
        for indicator_config in self.processed_config:
            indicator_name = indicator_config.get("indicator_name", "未命名指标")
            indicator_key = indicator_config.get("indicator_key", name_to_snake_key(indicator_name))
            fields[indicator_key] = (
                ThresholdBasedIndicatorSpec,
                Field(description=f"{indicator_name}指标")
            )

        def from_llm(cls, llm_input: BaseModel) -> BaseModel:
            """从LLM输入转换为内部输入模型"""
            indicators = {}
            for config in cls.config:
                _indicator_name = config.get("indicator_name", "未命名指标")
                _indicator_key = config.get("indicator_key", name_to_snake_key(_indicator_name))
                _indicator_value = getattr(llm_input, _indicator_key)

                # 验证是否存在分母项
                _baseline_name = config.get("baseline_name", None)
                _baseline_value = None

                if _baseline_name is not None:
                    _baseline_key = config.get("baseline_key", name_to_snake_key(_baseline_name)) # type: ignore[arg-type]
                    _baseline_value = getattr(llm_input, _baseline_key)

                indicators[_indicator_key] = ThresholdBasedIndicatorSpec(
                    indicator_name=_indicator_name,
                    indicator_value=_indicator_value,
                    baseline_name=_baseline_name,
                    baseline_value=_baseline_value,
                    threshold_type=config.get("threshold_type", None)
                )
            return cls(**indicators)

        # 创建模型类
        class_name = f"{self.model_name_root}DataInput"
        input_para_model_class  = create_model(class_name, **fields, __base__=BaseModel)
        # 注入类属性和类方法
        input_para_model_class.config = self.processed_config
        input_para_model_class.from_llm = classmethod(from_llm)
        # 模型缓存
        self._cached_args_model = input_para_model_class
        return self._cached_args_model

    def get_llm_input_schema(self) -> Dict[str, Any]:
        """
        获取LLM输入参数模型的schema信息
        包括参数名称、类型、描述等，用于查看LLM调用函数时看到的参数结构

        :return: 包含参数schema信息的字典
        """
        llm_input_class = self.create_args_model4llm()
        schema = llm_input_class.model_json_schema()

        # 提取并格式化参数信息
        properties = schema.get("properties", {})
        required = schema.get("required", [])

        schema_info = {
            "class_name": schema.get("title", llm_input_class.__name__),
            "description": schema.get("description", ""),
            "parameters": {}
        }

        # 从模型字段注解中获取类型信息
        model_fields = llm_input_class.model_fields

        for param_name, param_info in properties.items():
            # 尝试从字段注解中获取类型
            param_type = "unknown"
            if param_name in model_fields:
                field_info = model_fields[param_name]
                field_type = field_info.annotation

                # 处理 Union 类型
                if hasattr(field_type, '__origin__'):
                    origin = field_type.__origin__
                    # 检查是否是 Union 类型
                    if origin is Union or (hasattr(origin, '__name__') and origin.__name__ == 'Union'):
                        # 获取 Union 中的类型参数
                        args = getattr(field_type, '__args__', [])
                        type_names = []
                        for arg in args:
                            if hasattr(arg, '__name__'):
                                type_names.append(arg.__name__)
                            elif arg == float:
                                type_names.append("float")
                            elif arg == int:
                                type_names.append("int")
                            else:
                                type_names.append(str(arg))
                        if type_names:
                            param_type = "|".join(type_names)
                    elif hasattr(origin, '__name__'):
                        param_type = origin.__name__
                elif hasattr(field_type, '__name__'):
                    param_type = field_type.__name__
                elif field_type == float:
                    param_type = "float"
                elif field_type == int:
                    param_type = "int"
                else:
                    param_type = str(field_type)

            # 如果从字段注解中获取失败，尝试从 JSON schema 中获取
            if param_type == "unknown":
                # 检查是否有 anyOf 结构（Union 类型在 JSON schema 中的表示）
                if "anyOf" in param_info:
                    any_of = param_info["anyOf"]
                    type_names = []
                    for item in any_of:
                        item_type = item.get("type")
                        if item_type == "number":
                            type_names.append("float")
                        elif item_type == "integer":
                            type_names.append("int")
                        elif item_type:
                            type_names.append(item_type)
                    if type_names:
                        param_type = "|".join(type_names)
                # 检查是否有 type 字段
                elif "type" in param_info:
                    schema_type = param_info["type"]
                    if schema_type == "number":
                        param_type = "float|int"
                    else:
                        param_type = schema_type
                else:
                    param_type = param_info.get("type", "unknown")

            schema_info["parameters"][param_name] = {
                "type": param_type,
                "description": param_info.get("description", ""),
                "required": param_name in required
            }

        return schema_info

    def get_internal_input_schema(self) -> Dict[str, Any]:
        """
        获取内部输入参数模型的schema信息
        包括参数名称、类型、描述等

        :return: 包含参数schema信息的字典
        """
        internal_input_class = self.create_args_model()
        schema = internal_input_class.model_json_schema()

        # 提取并格式化参数信息
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        definitions = schema.get("$defs", {})  # Pydantic v2 使用 $defs

        schema_info = {
            "class_name": schema.get("title", internal_input_class.__name__),
            "description": schema.get("description", ""),
            "parameters": {}
        }

        # 从模型字段注解中获取类型信息
        model_fields = internal_input_class.model_fields

        for param_name, param_info in properties.items():
            # 尝试从字段注解中获取类型
            param_type = "unknown"
            if param_name in model_fields:
                field_info = model_fields[param_name]
                # 获取字段的实际类型
                field_type = field_info.annotation
                if hasattr(field_type, '__name__'):
                    param_type = field_type.__name__
                elif hasattr(field_type, '__origin__'):
                    # 处理泛型类型
                    origin = field_type.__origin__
                    if hasattr(origin, '__name__'):
                        param_type = origin.__name__
                else:
                    param_type = str(field_type)

            # 如果从字段注解中获取失败，尝试从 JSON schema 中获取
            if param_type == "unknown":
                # 检查是否有 $ref 引用
                if "$ref" in param_info:
                    ref_path = param_info["$ref"]
                    # 提取引用的类型名（例如 "#/$defs/ThresholdBasedIndicatorSpec" -> "ThresholdBasedIndicatorSpec"）
                    if "/" in ref_path:
                        param_type = ref_path.split("/")[-1]
                    else:
                        param_type = ref_path
                # 检查是否有 allOf 结构
                elif "allOf" in param_info:
                    all_of = param_info["allOf"]
                    for item in all_of:
                        if "$ref" in item:
                            ref_path = item["$ref"]
                            if "/" in ref_path:
                                param_type = ref_path.split("/")[-1]
                                break
                # 如果是对象类型，尝试从 definitions 中查找
                elif param_info.get("type") == "object":
                    # 查找是否有对应的定义
                    for def_name, def_info in definitions.items():
                        if def_info == param_info:
                            param_type = def_name
                            break
                    if param_type == "unknown":
                        param_type = "object"
                else:
                    param_type = param_info.get("type", "unknown")

            schema_info["parameters"][param_name] = {
                "type": param_type,
                "description": param_info.get("description", ""),
                "required": param_name in required
            }

        return schema_info

    def create_indicators_input_block(
            self,
            input_data: BaseModel
    ) -> ThresholdBasedIndicatorsBlock:
        """
        从内部输入模型创建 ThresholdBasedIndicatorsBlock
        用于进行阈值归因分析

        :param input_data: 内部输入模型实例（通过 from_llm 方法从 LLM 输入转换得到）
        :return: ThresholdBasedIndicatorsBlock 对象

        使用示例：
            # 1. 创建模型
            model_creator = ThresholdArgModel(
                model_name_root="Chapter4Threshold",
                indicators_config=[
                    {
                        "indicator": "高值品收入",
                        "baseline": "高值品收入目标",
                        "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
                    },
                    {
                        "indicator": "绩效总分",
                        "threshold_type": ThresholdType.TOTAL_PERFORMANCE_SCORE
                    }
                ]
            )

            # 2. 从 LLM 输入创建内部输入模型
            llm_input_class = model_creator.create_args_model4llm()
            internal_input_class = model_creator.create_args_model()

            # 3. LLM 输入数据
            llm_input = llm_input_class(
                gao_zhi_pin_shou_ru=85000.0,
                gao_zhi_pin_shou_ru_mu_biao=100000.0,
                ji_xiao_zong_fen=65.0
            )

            # 4. 转换为内部输入模型
            internal_input = internal_input_class.from_llm(llm_input)

            # 5. 创建 ThresholdBasedIndicatorsBlock
            indicators_block = model_creator.create_indicators_input_block(
                input_data=internal_input
            )

            # 6. 使用 ThresholdBasedAttrAnalyzer 进行归因分析
            from ThresholdBasedAttrAnalyzer import ThresholdBasedAttrAnalyzer
            analyzer = ThresholdBasedAttrAnalyzer()
            result = analyzer.evaluate_indicators(indicators_block)
        """
        # 验证输入数据是否为正确的内部输入模型类型
        internal_input_class = self.create_args_model()
        if not isinstance(input_data, internal_input_class):
            raise TypeError(
                f"期望 {internal_input_class.__name__} 类型的输入数据，"
                f"但得到 {type(input_data).__name__}"
            )

        # 提取所有指标的 ThresholdBasedIndicatorSpec 列表
        indicators = []
        for config in self.processed_config:
            indicator_key = config.get("indicator_key")
            indicator = getattr(input_data, indicator_key)
            if not isinstance(indicator, ThresholdBasedIndicatorSpec):
                raise TypeError(
                    f"指标 {indicator_key} 应该是 ThresholdBasedIndicatorSpec 类型，"
                    f"但得到 {type(indicator).__name__}"
                )
            indicators.append(indicator)

        # 创建并返回 ThresholdBasedIndicatorsBlock
        return ThresholdBasedIndicatorsBlock(indicators=indicators)

    def print_all_schemas(self) -> None:
        """
        打印所有参数模型的schema信息（包括LLM输入和内部输入）
        格式化输出，便于阅读
        """
        llm_schema = self.get_llm_input_schema()
        internal_schema = self.get_internal_input_schema()

        # 打印LLM输入参数模型
        print("\n" + "=" * 90)
        print(f"[LLM输入参数模型] {llm_schema['class_name']}")
        print("=" * 90)
        if llm_schema['description']:
            print(f"描述: {llm_schema['description']}\n")

        if llm_schema['parameters']:
            print("参数列表:")
            print("-" * 90)
            # 表头
            header = f"{'参数名称':<40} {'类型':<25} {'必填':<10} {'描述'}"
            print(header)
            print("-" * 90)

            # 参数行
            for param_name, param_info in llm_schema['parameters'].items():
                required_mark = "[必填]" if param_info['required'] else "[可选]"
                param_type = param_info['type']
                description = param_info['description']
                # 截断过长的描述
                if len(description) > 35:
                    description = description[:32] + "..."
                print(f"{param_name:<40} {param_type:<25} {required_mark:<10} {description}")
        else:
            print("无参数")

        print("=" * 90)

        # 打印内部输入参数模型
        print("\n" + "=" * 90)
        print(f"[内部输入参数模型] {internal_schema['class_name']}")
        print("=" * 90)
        if internal_schema['description']:
            print(f"描述: {internal_schema['description']}\n")

        if internal_schema['parameters']:
            print("参数列表:")
            print("-" * 90)
            # 表头
            header = f"{'参数名称':<40} {'类型':<25} {'必填':<10} {'描述'}"
            print(header)
            print("-" * 90)

            # 参数行
            for param_name, param_info in internal_schema['parameters'].items():
                required_mark = "[必填]" if param_info['required'] else "[可选]"
                param_type = param_info['type']
                description = param_info['description']
                # 截断过长的描述
                if len(description) > 35:
                    description = description[:32] + "..."
                print(f"{param_name:<40} {param_type:<25} {required_mark:<10} {description}")
        else:
            print("无参数")

        print("=" * 90 + "\n")


# 测试代码示例
if __name__ == "__main__":
    print("=" * 90)
    print("ThresholdArgModel 功能测试")
    print("=" * 90 + "\n")

    # 测试配置：包含两种类型的指标
    # 1. 有分母的指标（目标达成率类型）
    # 2. 无分母的指标（绩效总分类型）
    test_config = [
        {
            "indicator": "高值品收入",
            "baseline": "高值品收入目标",
            "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
        },
        {
            "indicator": "真时丽产品收入",
            "baseline": "真时丽产品收入目标",
            "threshold_type": ThresholdType.TARGET_ACHIEVEMENT
        },
        {
            "indicator": "绩效总分",
            "threshold_type": ThresholdType.TOTAL_PERFORMANCE_SCORE
        }
    ]

    # 创建参数模型
    model_creator = ThresholdArgModel(
        model_name_root="Chapter4Threshold",
        indicators_config=test_config
    )

    print("1. 参数模型创建成功！\n")

    # 打印所有schema信息
    print("2. 打印参数模型Schema信息：")
    print("-" * 90)
    model_creator.print_all_schemas()

    # 获取LLM输入模型和内部输入模型
    llm_input_class = model_creator.create_args_model4llm()
    internal_input_class = model_creator.create_args_model()

    print("3. 创建LLM输入实例：")
    print("-" * 90)

    # 测试数据 - 模拟LLM输入
    llm_input_data = {
        "gao_zhi_pin_shou_ru": 85000.0,           # 高值品收入实际值
        "gao_zhi_pin_shou_ru_mu_biao": 100000.0,  # 高值品收入目标值 (达成率85% - 未达标-良好)
        "zhen_shi_li_chan_pin_shou_ru": 45000.0,  # 真时丽产品收入实际值
        "zhen_shi_li_chan_pin_shou_ru_mu_biao": 50000.0,  # 真时丽产品收入目标值 (达成率90% - 未达标-良好)
        "ji_xiao_zong_fen": 65.0                   # 绩效总分 (65分 - 良好)
    }

    print(f"LLM输入数据: {llm_input_data}\n")

    # 创建LLM输入实例
    llm_input_instance = llm_input_class(**llm_input_data)
    print(f"LLM输入实例类型: {type(llm_input_instance).__name__}")
    print(f"LLM输入实例: {llm_input_instance}\n")

    print("4. 转换为内部输入模型：")
    print("-" * 90)

    # 使用 from_llm 方法转换为内部输入模型
    internal_input_instance = internal_input_class.from_llm(llm_input_instance)
    print(f"内部输入实例类型: {type(internal_input_instance).__name__}")

    # 打印内部输入实例的每个字段
    for config in model_creator.processed_config:
        indicator_key = config.get("indicator_key")
        indicator_spec = getattr(internal_input_instance, indicator_key)
        print(f"\n[{indicator_key}]")
        print(f"  - indicator_name: {indicator_spec.indicator_name}")
        print(f"  - indicator_value: {indicator_spec.indicator_value}")
        if indicator_spec.baseline_name:
            print(f"  - baseline_name: {indicator_spec.baseline_name}")
            print(f"  - baseline_value: {indicator_spec.baseline_value}")
        print(f"  - threshold_type: {indicator_spec.threshold_type}")

    print("\n5. 使用 ThresholdBasedAttrAnalyzer 进行归因分析：")
    print("-" * 90)

    # 导入分析器
    from analyzer import ThresholdBasedAttrAnalyzer

    # 提取所有指标进行分析
    indicators_list = []
    for config in model_creator.processed_config:
        indicator_key = config.get("indicator_key")
        indicator_spec = getattr(internal_input_instance, indicator_key)
        indicators_list.append(indicator_spec)

    # 创建分析器并执行分析
    analyzer = ThresholdBasedAttrAnalyzer()
    indicators_block = ThresholdBasedIndicatorsBlock(indicators=indicators_list)
    result = analyzer.evaluate_indicators(indicators_block)

    # 打印分析结果
    print(f"\n分析结果概览:")
    print(f"  - 总指标数: {len(result.indicators)}")
    if result.negative_indicators:
        print(f"  - 负向指标数: {len(result.negative_indicators)}")
    if result.positive_indicators:
        print(f"  - 正向指标数: {len(result.positive_indicators)}")

    print(f"\n详细分析结果:")
    for idx, indicator_result in enumerate(result.indicators, 1):
        print(f"\n[{idx}] {indicator_result.indicator_name}")
        print(f"    指标值: {indicator_result.indicator_value}")
        if indicator_result.baseline_name:
            print(f"    目标值: {indicator_result.baseline_value}")
            achievement_rate = (indicator_result.indicator_value / indicator_result.baseline_value) * 100
            print(f"    达成率: {achievement_rate:.2f}%")
        print(f"    状态标签: {indicator_result.status_label}")
        if indicator_result.is_negative is not None:
            status = "负向/风险" if indicator_result.is_negative else "正向/正常"
            print(f"    指标属性: {status}")

    print("\n" + "=" * 90)
    print("测试完成！")
    print("=" * 90)